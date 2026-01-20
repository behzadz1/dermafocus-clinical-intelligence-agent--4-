"""
Authentication Middleware
API key-based authentication for securing endpoints
"""

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery
from typing import Optional
import structlog

from app.config import settings

logger = structlog.get_logger()

# API key can be passed via header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def get_valid_api_keys() -> list:
    """
    Get list of valid API keys from settings.
    In production, this could come from a database or secrets manager.
    """
    api_keys_str = getattr(settings, 'valid_api_keys', '')
    if not api_keys_str:
        return []
    return [key.strip() for key in api_keys_str.split(',') if key.strip()]


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> str:
    """
    Verify API key from header or query parameter.

    Args:
        api_key_header: API key from X-API-Key header
        api_key_query: API key from api_key query parameter

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if no key provided, 403 if invalid key
    """
    # Get the API key from header or query
    api_key = api_key_header or api_key_query

    # Check if auth is enabled
    valid_keys = get_valid_api_keys()

    # If no valid keys configured, auth is disabled (development mode)
    if not valid_keys:
        logger.debug("api_auth_disabled", reason="no_valid_keys_configured")
        return "auth_disabled"

    # If keys are configured but none provided
    if not api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Validate the key
    if api_key not in valid_keys:
        logger.warning("api_key_invalid", key_prefix=api_key[:8] + "..." if len(api_key) > 8 else "***")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    logger.debug("api_key_validated", key_prefix=api_key[:8] + "...")
    return api_key


async def optional_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> Optional[str]:
    """
    Optional API key verification - doesn't require auth but logs if present.
    Useful for endpoints that work with or without authentication.
    """
    api_key = api_key_header or api_key_query
    valid_keys = get_valid_api_keys()

    if api_key and valid_keys and api_key in valid_keys:
        return api_key

    return None


# Dependency for protected routes
RequireAPIKey = Depends(verify_api_key)
OptionalAPIKey = Depends(optional_api_key)
