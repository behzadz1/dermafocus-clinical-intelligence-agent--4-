"""
DermaAI CKPA Backend API
FastAPI application with RAG capabilities for clinical knowledge retrieval
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
import structlog

from app.config import settings
from app.utils.logging_utils import redact_phi
from app.middleware.rate_limit import rate_limit_middleware


from app.api.routes import health, chat, documents, search, products, protocols

# Configure structured logging with context support
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Merge request_id from context
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown
    """
    # Startup
    logger.info(
        "application_startup",
        environment=settings.environment,
        debug=settings.debug
    )
    
    # TODO: Initialize services
    # - Connect to Pinecone
    # - Initialize embedding service
    # - Warm up models if needed
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    
    # TODO: Cleanup resources
    # - Close database connections
    # - Disconnect from Pinecone
    # - Cleanup temporary files


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Clinical Knowledge & Protocol Agent API for Dermafocus products",
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    redirect_slashes=False  # Don't redirect /api/chat to /api/chat/ (avoids 307 issues)
)


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

# CORS Middleware - Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Middleware - Compress responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request Logging Middleware with Request ID
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """
    Enforce per-API-key rate limits (skips when auth disabled).
    """
    return await rate_limit_middleware(request, call_next)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing information and request ID tracing
    """
    start_time = time.time()

    # Generate or extract request ID for tracing
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Bind request ID to structlog context for all logs in this request
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    # Log request (PHI-safe)
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        request_id=request_id
    )

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2),
        request_id=request_id
    )

    # Add headers for tracing
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id

    return response


# ==============================================================================
# EXCEPTION HANDLERS
# ==============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.error(
        "validation_error",
        error=str(exc),
        path=request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True
    )
    
    # Don't expose internal errors in production
    if settings.is_production:
        detail = "An internal error occurred. Please try again later."
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": detail
        }
    )


# ==============================================================================
# ROUTE REGISTRATION
# ==============================================================================

# Health check routes
app.include_router(health.router, prefix="/api", tags=["Health"])

# Chat and RAG routes
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

# Document management routes
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])

# Search routes
app.include_router(search.router, prefix="/api/search", tags=["Search"])

# Products routes (dynamic product extraction from RAG)
app.include_router(products.router, prefix="/api/products", tags=["Products"])

# Protocols routes (dynamic protocol extraction from RAG)
app.include_router(protocols.router, prefix="/api/protocols", tags=["Protocols"])


# ==============================================================================
# ROOT ENDPOINT
# ==============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "docs": "/docs" if settings.debug else "disabled",
        "endpoints": {
            "health": "/api/health",
            "chat": "/api/chat",
            "documents": "/api/documents",
            "search": "/api/search"
        }
    }


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers
    )
