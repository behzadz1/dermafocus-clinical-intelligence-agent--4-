"""
Cache Management Service
Handles cache invalidation and refresh strategies across the application
"""

from typing import Optional, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()

# Cache storage
_cache_store: Dict[str, Dict[str, Any]] = {}


class CacheEntry:
    """Represents a cached entry with TTL"""
    
    def __init__(self, data: Any, ttl_seconds: int = 3600):
        self.data = data
        self.ttl_seconds = ttl_seconds
        self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age >= self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get cache entry age in seconds"""
        return (datetime.utcnow() - self.created_at).total_seconds()


def set_cache(key: str, data: Any, ttl_seconds: int = 3600):
    """
    Store data in cache with TTL
    
    Args:
        key: Cache key
        data: Data to cache
        ttl_seconds: Time to live in seconds
    """
    _cache_store[key] = CacheEntry(data, ttl_seconds)
    logger.info("cache_set", key=key, ttl_seconds=ttl_seconds)


def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve data from cache if valid
    
    Args:
        key: Cache key
    
    Returns:
        Cached data if valid, None otherwise
    """
    if key not in _cache_store:
        return None
    
    entry = _cache_store[key]
    if entry.is_expired():
        logger.info("cache_expired", key=key, age_seconds=entry.age_seconds())
        del _cache_store[key]
        return None
    
    logger.info("cache_hit", key=key, age_seconds=entry.age_seconds())
    return entry.data


def clear_cache(key: str):
    """
    Clear specific cache entry
    
    Args:
        key: Cache key to clear
    """
    if key in _cache_store:
        del _cache_store[key]
        logger.info("cache_cleared", key=key)


def clear_all_cache():
    """Clear all cached entries"""
    count = len(_cache_store)
    _cache_store.clear()
    logger.info("cache_cleared_all", count=count)


def invalidate_related_caches(tags: list):
    """
    Invalidate all caches with specific tags
    
    Args:
        tags: List of tag identifiers to invalidate (e.g., ['protocols', 'products'])
    
    Example:
        invalidate_related_caches(['protocols', 'products'])
    """
    keys_to_delete = []
    
    for key in _cache_store.keys():
        for tag in tags:
            if tag in key:
                keys_to_delete.append(key)
                break
    
    for key in keys_to_delete:
        del _cache_store[key]
    
    logger.info("cache_invalidated", tags=tags, cleared_keys=keys_to_delete)
