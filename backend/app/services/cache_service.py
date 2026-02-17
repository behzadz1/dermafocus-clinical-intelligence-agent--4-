"""
Cache Management Service
Handles cache invalidation and refresh strategies using Redis backend
"""

from typing import Optional, Any, List
import structlog
import json
import redis
from datetime import datetime

from app.config import settings
from app.utils import metrics

logger = structlog.get_logger()

# Redis client (lazy initialized)
_redis_client = None

# Fallback in-memory cache for when Redis is unavailable
_fallback_cache = {}


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            # Parse Redis URL
            redis_url = settings.redis_url

            # Create Redis client with connection pooling
            _redis_client = redis.from_url(
                redis_url,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            _redis_client.ping()

            logger.info("redis_connected", url=redis_url)

        except Exception as e:
            logger.error(
                "redis_connection_failed",
                error=str(e),
                url=settings.redis_url
            )
            _redis_client = None
            raise

    return _redis_client


def _serialize_value(value: Any) -> str:
    """
    Serialize value to JSON string for Redis storage

    Args:
        value: Value to serialize

    Returns:
        JSON string
    """
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.error("cache_serialization_error", error=str(e))
        # For non-JSON-serializable objects, convert to string
        return json.dumps(str(value))


def _deserialize_value(value: str) -> Any:
    """
    Deserialize JSON string from Redis

    Args:
        value: JSON string

    Returns:
        Deserialized value
    """
    try:
        return json.loads(value)
    except (TypeError, ValueError) as e:
        logger.error("cache_deserialization_error", error=str(e))
        return value


def set_cache(key: str, data: Any, ttl_seconds: int = 3600):
    """
    Store data in Redis cache with TTL

    Args:
        key: Cache key
        data: Data to cache (must be JSON serializable)
        ttl_seconds: Time to live in seconds (default: 1 hour)
    """
    try:
        client = get_redis_client()
        serialized_data = _serialize_value(data)

        # Set with expiration
        client.setex(key, ttl_seconds, serialized_data)

        logger.debug("cache_set", key=key, ttl_seconds=ttl_seconds)

        # Record cache operation
        metrics.cache_operations.labels(operation="set", result="success").inc()

    except Exception as e:
        logger.error("cache_set_failed", key=key, error=str(e))
        metrics.cache_operations.labels(operation="set", result="failure").inc()

        # Fallback to in-memory cache
        _fallback_cache[key] = {
            "data": data,
            "expires_at": datetime.utcnow().timestamp() + ttl_seconds
        }


def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve data from Redis cache if valid

    Args:
        key: Cache key

    Returns:
        Cached data if valid, None otherwise
    """
    try:
        client = get_redis_client()
        value = client.get(key)

        if value is None:
            logger.debug("cache_miss", key=key)
            metrics.cache_operations.labels(operation="get", result="miss").inc()
            return None

        logger.debug("cache_hit", key=key)
        metrics.cache_operations.labels(operation="get", result="hit").inc()

        return _deserialize_value(value)

    except Exception as e:
        logger.error("cache_get_failed", key=key, error=str(e))
        metrics.cache_operations.labels(operation="get", result="failure").inc()

        # Fallback to in-memory cache
        if key in _fallback_cache:
            entry = _fallback_cache[key]
            if datetime.utcnow().timestamp() < entry["expires_at"]:
                logger.debug("fallback_cache_hit", key=key)
                return entry["data"]
            else:
                del _fallback_cache[key]

        return None


def clear_cache(key: str):
    """
    Clear specific cache entry from Redis

    Args:
        key: Cache key to clear
    """
    try:
        client = get_redis_client()
        deleted = client.delete(key)

        if deleted:
            logger.info("cache_cleared", key=key)
            metrics.cache_operations.labels(operation="delete", result="success").inc()

    except Exception as e:
        logger.error("cache_clear_failed", key=key, error=str(e))
        metrics.cache_operations.labels(operation="delete", result="failure").inc()

        # Fallback
        if key in _fallback_cache:
            del _fallback_cache[key]


def clear_all_cache():
    """
    Clear all cached entries in current database

    WARNING: This clears all keys in the Redis database
    """
    try:
        client = get_redis_client()
        client.flushdb()

        logger.info("cache_cleared_all")
        metrics.cache_operations.labels(operation="flush", result="success").inc()

    except Exception as e:
        logger.error("cache_clear_all_failed", error=str(e))
        metrics.cache_operations.labels(operation="flush", result="failure").inc()

        # Fallback
        _fallback_cache.clear()


def invalidate_related_caches(tags: List[str]):
    """
    Invalidate all caches with specific tags using pattern matching

    Args:
        tags: List of tag identifiers to invalidate (e.g., ['protocols', 'products'])

    Example:
        invalidate_related_caches(['protocols', 'products'])
    """
    try:
        client = get_redis_client()
        deleted_count = 0

        for tag in tags:
            # Find all keys matching pattern
            pattern = f"*{tag}*"
            keys = client.keys(pattern)

            if keys:
                deleted = client.delete(*keys)
                deleted_count += deleted

        logger.info("cache_invalidated", tags=tags, deleted_count=deleted_count)
        metrics.cache_operations.labels(operation="invalidate", result="success").inc()

    except Exception as e:
        logger.error("cache_invalidate_failed", tags=tags, error=str(e))
        metrics.cache_operations.labels(operation="invalidate", result="failure").inc()

        # Fallback
        keys_to_delete = []
        for key in list(_fallback_cache.keys()):
            for tag in tags:
                if tag in key:
                    keys_to_delete.append(key)
                    break

        for key in keys_to_delete:
            if key in _fallback_cache:
                del _fallback_cache[key]


def get_cache_stats() -> dict:
    """
    Get cache statistics from Redis

    Returns:
        Dictionary with cache stats
    """
    try:
        client = get_redis_client()
        info = client.info("stats")

        return {
            "connected": True,
            "total_keys": client.dbsize(),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) /
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
            )
        }

    except Exception as e:
        logger.error("cache_stats_failed", error=str(e))
        return {
            "connected": False,
            "total_keys": len(_fallback_cache),
            "fallback_mode": True
        }


def health_check() -> dict:
    """
    Check Redis connection health

    Returns:
        Health status dictionary
    """
    try:
        client = get_redis_client()
        client.ping()

        stats = get_cache_stats()

        return {
            "status": "healthy",
            "connected": True,
            "total_keys": stats.get("total_keys", 0),
            "hit_rate": stats.get("hit_rate", 0.0)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
            "fallback_mode": True
        }
