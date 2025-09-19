"""
FastAPI application configuration and setup for Shield AI.

Creates the main FastAPI application instance with middleware,
CORS configuration, and global exception handlers.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings, get_cors_config, is_development
from .redis_client import get_redis_health


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Shield AI application...")
    
    # Test Redis connection on startup
    try:
        health = get_redis_health()
        if health["status"] == "healthy":
            logger.info("Redis connection established successfully")
        else:
            logger.warning(f"Redis health check issues: {health.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis on startup: {str(e)}")
    
    logger.info("Shield AI application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Shield AI application...")
    logger.info("Shield AI application shut down complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Shield AI - Intelligent Data Anonymization System",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if is_development() else None,
        redoc_url="/redoc" if is_development() else None,
        openapi_url="/openapi.json" if is_development() else None,
    )
    
    # Add CORS middleware
    cors_config = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        **cors_config
    )
    
    # Add trusted host middleware for production
    if not is_development():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add processing time header to responses."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log HTTP requests."""
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response
    
    # Global exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.method} {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc.errors()} - {request.method} {request.url.path}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "details": exc.errors(),
                "status_code": 422,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc: Exception):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {str(exc)} - {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "path": request.url.path
            }
        )
    
    # Add basic root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with application information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Shield AI - Intelligent Data Anonymization System",
            "status": "running",
            "environment": settings.environment,
            "docs_url": "/docs" if is_development() else "disabled"
        }
    
    # Add application info endpoint
    @app.get("/info", tags=["System"])
    async def app_info():
        """Get application information and configuration."""
        return {
            "application": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug
            },
            "server": {
                "host": settings.api_host,
                "port": settings.api_port,
                "reload": settings.api_reload
            },
            "features": {
                "docs_enabled": is_development(),
                "cors_enabled": True,
                "redis_enabled": True,
                "pii_detection": True,
                "streaming": True
            }
        }
    
    logger.info("FastAPI application configured successfully")
    return app


# Create global app instance
app = create_app()


# Health check function for the app
def get_app_health() -> Dict[str, Any]:
    """
    Get application health status.
    
    Returns:
        Dict[str, Any]: Application health information
    """
    try:
        redis_health = get_redis_health()
        
        app_health = {
            "status": "healthy" if redis_health["status"] == "healthy" else "degraded",
            "timestamp": time.time(),
            "services": {
                "redis": redis_health["status"],
                "fastapi": "healthy"
            },
            "version": settings.app_version,
            "environment": settings.environment
        }
        
        if redis_health["status"] != "healthy":
            app_health["issues"] = {
                "redis": redis_health.get("error", "Unknown Redis error")
            }
        
        return app_health
        
    except Exception as e:
        logger.error(f"Error checking app health: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "version": settings.app_version,
            "environment": settings.environment
        }


# Export main components
__all__ = [
    "app",
    "create_app",
    "get_app_health"
]