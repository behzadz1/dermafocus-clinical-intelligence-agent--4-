"""
Rate limiting middleware with Redis-backed token bucket algorithm (Phase 4.0)
Supports distributed rate limiting across multiple instances
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import time

from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

from app.config import settings

logger = structlog.get_logger()


@dataclass
class _WindowCounter:
    window_id: int
    count: int


# Fallback in-memory rate limits (used if Redis unavailable)
_rate_limits: Dict[str, Dict[str, _WindowCounter]] = {}

# Redis client (lazy loaded)
_redis_client = None


def _get_window_id(now: datetime, seconds: int) -> int:
    return int(now.timestamp() // seconds)


def _get_redis_client():
    """Get or initialize Redis client (lazy loading)"""
    global _redis_client
    if _redis_client is None:
        try:
            from app.services.cache_service import get_redis_client
            _redis_client = get_redis_client()
            logger.info("rate_limit_redis_initialized")
        except Exception as e:
            logger.warning(
                "rate_limit_redis_unavailable",
                error=str(e),
                fallback="in_memory"
            )
            _redis_client = False  # Mark as failed to avoid retry on every request
    return _redis_client if _redis_client is not False else None


def _get_api_key(request: Request) -> Optional[str]:
    header_name = settings.api_key_header
    return request.headers.get(header_name) or request.query_params.get("api_key")


def _token_bucket_check_redis(redis_client, key: str, bucket: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Token bucket rate limiting using Redis (atomic)

    Args:
        redis_client: Redis client
        key: API key or identifier
        bucket: Bucket name (e.g., "minute", "hour")
        limit: Maximum requests allowed
        window_seconds: Time window in seconds

    Returns:
        (allowed: bool, current_count: int)
    """
    try:
        redis_key = f"rate_limit:{key}:{bucket}"
        current_time = time.time()

        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Get current count
        pipe.get(redis_key)
        pipe.ttl(redis_key)
        results = pipe.execute()

        current_count = int(results[0]) if results[0] else 0
        ttl = results[1] if results[1] > 0 else window_seconds

        # Check if limit exceeded
        if current_count >= limit:
            logger.debug(
                "rate_limit_check",
                key_prefix=key[:8],
                bucket=bucket,
                count=current_count,
                limit=limit,
                allowed=False
            )
            return False, current_count

        # Increment counter (atomic)
        pipe = redis_client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        results = pipe.execute()

        new_count = results[0]

        logger.debug(
            "rate_limit_check",
            key_prefix=key[:8],
            bucket=bucket,
            count=new_count,
            limit=limit,
            allowed=True
        )

        return True, new_count

    except Exception as e:
        logger.error(
            "rate_limit_redis_error",
            error=str(e),
            key_prefix=key[:8],
            bucket=bucket
        )
        # Fail open - allow request if Redis fails
        return True, 0


def _increment_counter(key: str, bucket: str, window_seconds: int) -> int:
    """Fallback in-memory counter (used if Redis unavailable)"""
    now = datetime.utcnow()
    window_id = _get_window_id(now, window_seconds)
    key_bucket = _rate_limits.setdefault(key, {})
    counter = key_bucket.get(bucket)
    if counter is None or counter.window_id != window_id:
        counter = _WindowCounter(window_id=window_id, count=0)
        key_bucket[bucket] = counter
    counter.count += 1
    return counter.count


async def rate_limit_middleware(request: Request, call_next):
    """
    Apply per-API-key rate limiting with Redis-backed token bucket (Phase 4.0)
    Also enforces daily cost threshold
    Falls back to in-memory if Redis unavailable
    """
    valid_keys = [key.strip() for key in settings.valid_api_keys.split(",") if key.strip()]
    if not valid_keys:
        return await call_next(request)

    api_key = _get_api_key(request)
    if not api_key:
        return await call_next(request)

    # PHASE 4.0: Check daily cost threshold (only for chat/query endpoints)
    if request.url.path.startswith("/api/chat") or request.url.path.startswith("/api/query"):
        try:
            from app.services.cost_tracker import get_cost_tracker

            cost_tracker = get_cost_tracker()
            daily_cost_threshold = getattr(settings, "daily_cost_threshold_usd", 50.0)  # Default $50/day

            if cost_tracker.check_daily_threshold(daily_cost_threshold):
                logger.error(
                    "daily_cost_threshold_exceeded",
                    threshold_usd=daily_cost_threshold,
                    daily_costs=cost_tracker.get_daily_costs()
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Daily cost threshold of ${daily_cost_threshold} exceeded. Please contact support.",
                        "error_code": "DAILY_COST_LIMIT_EXCEEDED",
                        "threshold_usd": daily_cost_threshold
                    }
                )
        except Exception as cost_error:
            # Don't block requests if cost tracking fails
            logger.warning(
                "cost_threshold_check_failed",
                error=str(cost_error),
                path=request.url.path
            )

    # Try Redis-backed rate limiting first
    redis_client = _get_redis_client()

    if redis_client:
        # Use Redis token bucket (distributed rate limiting)
        minute_allowed, minute_count = _token_bucket_check_redis(
            redis_client, api_key, "minute", settings.rate_limit_per_minute, 60
        )
        hour_allowed, hour_count = _token_bucket_check_redis(
            redis_client, api_key, "hour", settings.rate_limit_per_hour, 3600
        )

        if not minute_allowed or not hour_allowed:
            logger.warning(
                "rate_limit_exceeded_redis",
                api_key_prefix=api_key[:8] + "..." if len(api_key) > 8 else "***",
                minute_count=minute_count,
                hour_count=hour_count,
                backend="redis"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "limits": {
                        "per_minute": settings.rate_limit_per_minute,
                        "per_hour": settings.rate_limit_per_hour
                    },
                    "retry_after": 60 if not minute_allowed else 3600
                },
                headers={
                    "Retry-After": str(60 if not minute_allowed else 3600),
                    "X-RateLimit-Limit-Minute": str(settings.rate_limit_per_minute),
                    "X-RateLimit-Limit-Hour": str(settings.rate_limit_per_hour),
                    "X-RateLimit-Remaining-Minute": str(max(0, settings.rate_limit_per_minute - minute_count)),
                    "X-RateLimit-Remaining-Hour": str(max(0, settings.rate_limit_per_hour - hour_count))
                }
            )
    else:
        # Fallback to in-memory rate limiting (single instance only)
        minute_count = _increment_counter(api_key, "minute", 60)
        hour_count = _increment_counter(api_key, "hour", 3600)

        if minute_count > settings.rate_limit_per_minute or hour_count > settings.rate_limit_per_hour:
            logger.warning(
                "rate_limit_exceeded_memory",
                api_key_prefix=api_key[:8] + "..." if len(api_key) > 8 else "***",
                minute_count=minute_count,
                hour_count=hour_count,
                backend="in_memory"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "limits": {
                        "per_minute": settings.rate_limit_per_minute,
                        "per_hour": settings.rate_limit_per_hour
                    }
                }
            )

    return await call_next(request)
