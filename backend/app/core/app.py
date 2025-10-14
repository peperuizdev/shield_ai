"""
FastAPI application configuration and setup for Shield AI.

Creates the main FastAPI application instance with middleware,
CORS configuration, global exception handlers, and automatic Redis startup in development.
"""

import logging
import time
import subprocess
import sys
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


def ensure_redis_docker_running():
    """
    Ensure Redis Docker container is running (SOLO para desarrollo).
    
    Returns:
        bool: True if Redis is running or was started successfully
    """
    # Solo en desarrollo
    if not is_development():
        logger.info("Production mode: skipping automatic Redis Docker startup")
        return True
    
    container_name = "shieldai-redis-dev"
    
    try:
        logger.info("🔍 Checking if Redis Docker container is running...")
        
        # 1. Verificar si Docker está disponible
        try:
            subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠️  Docker no está disponible. Asegúrate de tener Docker Desktop abierto.")
            logger.warning("⚠️  O inicia Redis manualmente: docker run -d -p 6379:6379 --name shieldai-redis-dev redis:alpine")
            return False
        
        # 2. Verificar si el contenedor está corriendo
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if container_name in result.stdout:
            logger.info(f"✅ Redis container '{container_name}' is already running")
            return True
        
        # 3. Verificar si el contenedor existe pero está parado
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if container_name in result.stdout:
            # Contenedor existe pero está parado, iniciarlo
            logger.info(f"🔧 Starting existing Redis container '{container_name}'...")
            subprocess.run(
                ["docker", "start", container_name],
                check=True,
                timeout=10
            )
            logger.info(f"✅ Redis container '{container_name}' started successfully")
        else:
            # Contenedor no existe, crearlo
            logger.info(f"🔧 Creating new Redis container '{container_name}'...")
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "6379:6379",
                "--restart", "unless-stopped",
                "redis:alpine"
            ], check=True, timeout=30)
            logger.info(f"✅ Redis container '{container_name}' created and started successfully")
        
        # 4. Esperar a que Redis esté listo
        logger.info("⏳ Waiting for Redis to be ready...")
        max_retries = 10
        for i in range(max_retries):
            try:
                result = subprocess.run(
                    ["docker", "exec", container_name, "redis-cli", "ping"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "PONG" in result.stdout:
                    logger.info("✅ Redis is ready and responding to PING")
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass
            
            if i < max_retries - 1:
                time.sleep(0.5)
        
        logger.warning("⚠️  Redis container started but not responding to PING")
        return True  # Continuar de todas formas
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start Redis container: {e}")
        logger.error(f"   Command output: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        logger.error(f"   Command error: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        logger.error("💡 Solution: Start Docker Desktop or run Redis manually:")
        logger.error(f"   docker run -d -p 6379:6379 --name {container_name} redis:alpine")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Docker command timed out")
        logger.error("💡 Make sure Docker Desktop is running")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error starting Redis: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # ==================== STARTUP ====================
    logger.info("Starting Shield AI application...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # En desarrollo, intentar levantar Redis automáticamente
    if is_development():
        logger.info("🐳 Development mode: Ensuring Redis Docker container is running...")
        redis_docker_ok = ensure_redis_docker_running()
        
        if not redis_docker_ok:
            logger.error("=" * 60)
            logger.error("❌ REDIS DOCKER STARTUP FAILED")
            logger.error("=" * 60)
            logger.error("")
            logger.error("The application cannot start without Redis.")
            logger.error("")
            logger.error("Please do ONE of the following:")
            logger.error("  1. Start Docker Desktop")
            logger.error("  2. Run Redis manually:")
            logger.error("     docker run -d -p 6379:6379 --name shieldai-redis-dev redis:alpine")
            logger.error("  3. Install Redis locally (not recommended)")
            logger.error("")
            logger.error("=" * 60)
            sys.exit(1)  # Detener la aplicación
    
    # Test Redis connection
    try:
        logger.info("🔗 Testing Redis connection...")
        health = get_redis_health()
        
        if health["status"] == "healthy":
            logger.info("✅ Redis connection established successfully")
            logger.info(f"   Redis version: {health.get('redis_info', {}).get('version', 'unknown')}")
            logger.info(f"   Connected clients: {health.get('redis_info', {}).get('connected_clients', 0)}")
        else:
            logger.error("❌ Redis health check failed")
            logger.error(f"   Error: {health.get('error', 'Unknown error')}")
            
            if is_development():
                logger.error("")
                logger.error("Redis container is running but not responding.")
                logger.error("Try restarting it:")
                logger.error("  docker restart shieldai-redis-dev")
                logger.error("")
                sys.exit(1)
            else:
                logger.warning("⚠️  Continuing despite Redis issues (production mode)")
                
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {str(e)}")
        
        if is_development():
            logger.error("")
            logger.error("Could not connect to Redis at localhost:6379")
            logger.error("Make sure Redis container is running:")
            logger.error("  docker ps | grep redis")
            logger.error("")
            sys.exit(1)
        else:
            logger.warning("⚠️  Continuing despite Redis connection error (production mode)")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Shield AI application started successfully")
    logger.info("=" * 60)
    logger.info(f"📍 API: http://localhost:{settings.api_port}")
    logger.info(f"📚 Docs: http://localhost:{settings.api_port}/docs")
    logger.info("=" * 60)
    logger.info("")
    
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("")
    logger.info("=" * 60)
    logger.info("Shutting down Shield AI application...")
    logger.info("=" * 60)
    
    # En desarrollo, informar que Redis sigue corriendo
    if is_development():
        logger.info("💡 Redis container is still running for faster next startup")
        logger.info("   To stop it manually: docker stop shieldai-redis-dev")
    
    logger.info("✅ Shield AI application shut down complete")
    logger.info("=" * 60)


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
    @app.head("/", tags=["Root"])
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