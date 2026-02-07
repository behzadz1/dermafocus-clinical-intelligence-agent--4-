"""
Simple in-memory rate limiting middleware keyed by API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

from app.config import settings

logger = structlog.get_logger()


@dataclass
class _WindowCounter:
    window_id: int
    count: int


_rate_limits: Dict[str, Dict[str, _WindowCounter]] = {}


def _get_window_id(now: datetime, seconds: int) -> int:
    return int(now.timestamp() // seconds)


def _get_api_key(request: Request) -> Optional[str]:
    header_name = settings.api_key_header
    return request.headers.get(header_name) or request.query_params.get("api_key")


def _increment_counter(key: str, bucket: str, window_seconds: int) -> int:
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
    Apply per-API-key rate limiting. Skips if auth is disabled.
    """
    valid_keys = [key.strip() for key in settings.valid_api_keys.split(",") if key.strip()]
    if not valid_keys:
        return await call_next(request)

    api_key = _get_api_key(request)
    if not api_key:
        return await call_next(request)

    minute_count = _increment_counter(api_key, "minute", 60)
    hour_count = _increment_counter(api_key, "hour", 3600)

    if minute_count > settings.rate_limit_per_minute or hour_count > settings.rate_limit_per_hour:
        logger.warning(
            "rate_limit_exceeded",
            api_key_prefix=api_key[:8] + "..." if len(api_key) > 8 else "***",
            minute_count=minute_count,
            hour_count=hour_count
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
