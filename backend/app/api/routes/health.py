"""
Health Check Routes
Endpoints for monitoring application health and dependencies
"""

from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import structlog
import os

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    environment: str
    python_version: str


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with dependency status"""
    dependencies: dict


async def check_pinecone_health() -> Dict[str, Any]:
    """Actually verify Pinecone connectivity."""
    try:
        from app.services.pinecone_service import get_pinecone_service
        pinecone_service = get_pinecone_service()
        result = pinecone_service.health_check()
        return result
    except Exception as e:
        logger.error("pinecone_health_check_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_claude_health() -> Dict[str, Any]:
    """Verify Claude API key is present (actual health check is expensive)."""
    try:
        if not settings.anthropic_api_key:
            return {"status": "unhealthy", "error": "API key not configured"}
        return {
            "status": "healthy",
            "model": settings.claude_model,
            "key_configured": True
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_embeddings_health() -> Dict[str, Any]:
    """Verify OpenAI embeddings configuration."""
    try:
        if not settings.openai_api_key:
            return {"status": "unhealthy", "error": "API key not configured"}
        return {
            "status": "healthy",
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
            "key_configured": True
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint
    Returns: Application status and basic info
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check endpoint with actual dependency verification.

    Returns 200 if all healthy, 503 if any critical service is unhealthy.
    """
    dependencies = {}
    critical_unhealthy = False

    # Check Pinecone (critical)
    pinecone_status = await check_pinecone_health()
    dependencies["pinecone"] = pinecone_status
    if pinecone_status.get("status") == "unhealthy":
        critical_unhealthy = True

    # Check Claude API (critical)
    claude_status = await check_claude_health()
    dependencies["claude"] = claude_status
    if claude_status.get("status") == "unhealthy":
        critical_unhealthy = True

    # Check Embeddings (critical)
    embeddings_status = await check_embeddings_health()
    dependencies["embeddings"] = embeddings_status
    if embeddings_status.get("status") == "unhealthy":
        critical_unhealthy = True

    # Non-critical services
    dependencies["redis"] = {
        "status": "not_configured",
        "message": "Optional - not required for operation"
    }
    dependencies["database"] = {
        "status": "not_configured",
        "message": "Optional - not required for operation"
    }

    # Determine overall status
    if critical_unhealthy:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall_status = "healthy"
        http_status = status.HTTP_200_OK

    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "dependencies": dependencies
    }

    return JSONResponse(content=response_data, status_code=http_status)


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/Docker.
    Returns 200 if app is ready to serve traffic, 503 otherwise.

    Checks critical services before accepting traffic.
    """
    checks = {
        "pinecone": await check_pinecone_health(),
        "claude": await check_claude_health(),
        "embeddings": await check_embeddings_health()
    }

    all_ready = all(
        check.get("status") == "healthy"
        for check in checks.values()
    )

    if not all_ready:
        logger.warning("readiness_check_failed", checks=checks)
        return JSONResponse(
            content={"status": "not_ready", "checks": checks},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return {"status": "ready", "checks": checks}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness probe for Kubernetes/Docker.
    Returns 200 if app process is alive (even if degraded).

    This should always return 200 unless the process is completely dead.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}



@router.get("/debug-config")
def debug_config():
    # IMPORTANT: do NOT return API keys
    return {
        "ENVIRONMENT": os.getenv("ENVIRONMENT"),
        "APP_VERSION": os.getenv("APP_VERSION"),
        "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME"),
        "PINECONE_ENVIRONMENT": os.getenv("PINECONE_ENVIRONMENT"),
        "PINECONE_NAMESPACE": os.getenv("PINECONE_NAMESPACE", "default"),
        "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL"),
        "VECTOR_SEARCH_TOP_K": os.getenv("VECTOR_SEARCH_TOP_K"),
        "RERANK_TOP_K": os.getenv("RERANK_TOP_K"),
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL"),
        "CLAUDE_TEMPERATURE": os.getenv("CLAUDE_TEMPERATURE"),
    }
