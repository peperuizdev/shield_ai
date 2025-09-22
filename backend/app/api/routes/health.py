"""
Health check endpoints for Shield AI.

Provides health monitoring, system status, and diagnostic
information for the application and its dependencies.
"""

import time
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse

from core.app import app, get_app_health
from core.redis_client import get_redis_health, get_redis_stats, is_redis_connected
from models.requests import HealthCheckRequest
from models.responses import HealthCheckResponse, SystemStatsResponse


logger = logging.getLogger(__name__)

# Create router for health endpoints
router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/",
    response_model=HealthCheckResponse,
    summary="Basic health check",
    description="Get basic health status of the application and its services"
)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns overall system health status including:
    - Application status
    - Redis connectivity
    - Service availability
    
    Returns:
        HealthCheckResponse: Health status information
    """
    try:
        app_health = get_app_health()
        
        return HealthCheckResponse(
            success=True,
            message="Health check completed",
            status=app_health["status"],
            services=app_health["services"],
            version=app_health["version"],
            environment=app_health["environment"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/detailed",
    response_model=HealthCheckResponse,
    summary="Detailed health check",
    description="Get comprehensive health information including system metrics"
)
async def detailed_health_check(
    include_redis_info: bool = Query(
        True,
        description="Include detailed Redis information"
    ),
    include_system_stats: bool = Query(
        False,
        description="Include system performance statistics"
    )
):
    """
    Detailed health check with comprehensive system information.
    
    Args:
        include_redis_info (bool): Include Redis server information
        include_system_stats (bool): Include system performance stats
        
    Returns:
        HealthCheckResponse: Detailed health status information
    """
    try:
        app_health = get_app_health()
        detailed_info = {}
        
        # Add Redis detailed information
        if include_redis_info:
            try:
                redis_health = get_redis_health()
                detailed_info["redis"] = {
                    "status": redis_health["status"],
                    "connection_info": redis_health.get("redis_info", {}),
                    "pool_info": redis_health.get("connection_pool_info", {}),
                    "error": redis_health.get("error")
                }
            except Exception as e:
                detailed_info["redis"] = {"error": str(e), "status": "error"}
        
        # Add system statistics if requested
        if include_system_stats:
            try:
                import psutil
                detailed_info["system"] = {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent,
                    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                }
            except ImportError:
                detailed_info["system"] = {"error": "psutil not available"}
            except Exception as e:
                detailed_info["system"] = {"error": str(e)}
        
        # Add application-specific info
        detailed_info["application"] = {
            "uptime": time.time(),  # This would be calculated from app start time
            "endpoints_available": True,
            "middleware_active": True
        }
        
        return HealthCheckResponse(
            success=True,
            message="Detailed health check completed",
            status=app_health["status"],
            services=app_health["services"],
            version=app_health["version"],
            environment=app_health["environment"],
            detailed_info=detailed_info if detailed_info else None
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/redis",
    summary="Redis health check",
    description="Check Redis connectivity and get Redis-specific health information"
)
async def redis_health_check():
    """
    Redis-specific health check endpoint.
    
    Returns:
        Dict[str, Any]: Redis health status and information
    """
    try:
        redis_health = get_redis_health()
        
        return {
            "success": redis_health["status"] == "healthy",
            "timestamp": datetime.now(),
            "redis_status": redis_health["status"],
            "connected": redis_health["connected"],
            "server_info": redis_health.get("redis_info", {}),
            "connection_pool": redis_health.get("connection_pool_info", {}),
            "error": redis_health.get("error")
        }
        
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "redis_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="System statistics",
    description="Get system performance statistics and metrics"
)
async def get_system_stats():
    """
    Get comprehensive system statistics.
    
    Returns:
        SystemStatsResponse: System statistics and metrics
    """
    try:
        # Get Redis statistics
        redis_stats = get_redis_stats()
        
        # Get session statistics (would be implemented in session manager)
        from services.session_manager import list_active_sessions, cleanup_expired_sessions
        
        active_sessions = list_active_sessions()
        cleanup_info = cleanup_expired_sessions()
        
        session_stats = {
            "active_sessions": len(active_sessions),
            "total_active": cleanup_info.get("active_sessions", 0),
            "recently_expired": cleanup_info.get("expired_sessions", 0),
            "last_cleanup": cleanup_info.get("cleanup_time", datetime.now()).isoformat() if cleanup_info.get("cleanup_time") else None
        }
        
        # Basic API stats (would be enhanced with proper metrics collection)
        api_stats = {
            "endpoints_registered": len([route for route in app.routes]),
            "health_check_time": datetime.now().isoformat(),
            "redis_connected": is_redis_connected()
        }
        
        return SystemStatsResponse(
            success=True,
            message="System statistics retrieved successfully",
            redis_stats=redis_stats,
            session_stats=session_stats,
            api_stats=api_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/readiness",
    summary="Readiness probe",
    description="Check if application is ready to serve requests"
)
async def readiness_probe():
    """
    Kubernetes/Docker readiness probe endpoint.
    
    Returns:
        Dict[str, Any]: Readiness status
    """
    try:
        # Check critical dependencies
        redis_connected = is_redis_connected()
        
        if redis_connected:
            return {
                "ready": True,
                "timestamp": datetime.now(),
                "checks": {
                    "redis": "connected",
                    "application": "ready"
                }
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "timestamp": datetime.now().isoformat(),
                    "checks": {
                        "redis": "disconnected",
                        "application": "not_ready"
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness probe failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/liveness",
    summary="Liveness probe",
    description="Check if application is alive and responding"
)
async def liveness_probe():
    """
    Kubernetes/Docker liveness probe endpoint.
    
    Returns:
        Dict[str, Any]: Liveness status
    """
    try:
        return {
            "alive": True,
            "timestamp": datetime.now(),
            "uptime": time.time(),  # Would be calculated from app start
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Liveness probe failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "alive": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Export router for testing
__all__ = ["router"]