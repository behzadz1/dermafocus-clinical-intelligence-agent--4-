"""
Health Check Routes
Endpoints for monitoring application health and dependencies
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
import sys
import structlog

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


@router.get("/health/detailed", response_model=DetailedHealthResponse, status_code=status.HTTP_200_OK)
async def detailed_health_check():
    """
    Detailed health check endpoint
    Returns: Application status + dependency status
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Pinecone connectivity
    - API key validity
    """
    dependencies = {}
    
    # Check Anthropic API (placeholder - will implement in Phase 4)
    try:
        dependencies["anthropic"] = {
            "status": "configured",
            "key_present": bool(settings.anthropic_api_key)
        }
    except Exception as e:
        dependencies["anthropic"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Pinecone (placeholder - will implement in Phase 3)
    try:
        dependencies["pinecone"] = {
            "status": "configured",
            "key_present": bool(settings.pinecone_api_key),
            "index_name": settings.pinecone_index_name
        }
    except Exception as e:
        dependencies["pinecone"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check OpenAI (placeholder)
    try:
        dependencies["openai"] = {
            "status": "configured",
            "key_present": bool(settings.openai_api_key),
            "embedding_model": settings.embedding_model
        }
    except Exception as e:
        dependencies["openai"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Redis (placeholder - will implement when needed)
    dependencies["redis"] = {
        "status": "not_implemented",
        "message": "Redis integration pending"
    }
    
    # Check Database (placeholder - will implement when needed)
    dependencies["database"] = {
        "status": "not_implemented",
        "message": "Database integration pending"
    }
    
    # Determine overall health status
    all_healthy = all(
        dep.get("status") in ["configured", "healthy", "not_implemented"]
        for dep in dependencies.values()
    )
    
    return DetailedHealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        dependencies=dependencies
    )


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness probe for Kubernetes/Docker
    Returns 200 if app is ready to serve traffic
    """
    # TODO: Add actual readiness checks
    # - Database connection pool ready
    # - Pinecone connection established
    # - Required models loaded
    
    return {"status": "ready"}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness probe for Kubernetes/Docker
    Returns 200 if app is alive (even if degraded)
    """
    return {"status": "alive"}
