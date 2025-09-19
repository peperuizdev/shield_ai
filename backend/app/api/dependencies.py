"""
FastAPI dependencies for Shield AI.

Common dependencies used across API endpoints for
authentication, validation, and request processing.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings
from core.redis_client import get_redis_client, is_redis_connected
from services.session_manager import get_session_manager, SessionManager


logger = logging.getLogger(__name__)

# Security scheme (optional, for future authentication)
security = HTTPBearer(auto_error=False)


async def get_current_redis_client():
    """
    Get Redis client dependency.
    
    Returns:
        redis.Redis: Redis client instance
        
    Raises:
        HTTPException: If Redis is not available
    """
    if not is_redis_connected():
        logger.error("Redis connection not available")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    
    return get_redis_client()


async def get_current_session_manager() -> SessionManager:
    """
    Get session manager dependency.
    
    Returns:
        SessionManager: Session manager instance
    """
    return get_session_manager()


async def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format and existence.
    
    Args:
        session_id (str): Session identifier to validate
        
    Returns:
        str: Validated session ID
        
    Raises:
        HTTPException: If session ID is invalid
    """
    import re
    
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Session ID cannot be empty"
        )
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', session_id):
        raise HTTPException(
            status_code=400,
            detail="Session ID must contain only alphanumeric characters, underscores, and hyphens"
        )
    
    if len(session_id) > 128:
        raise HTTPException(
            status_code=400,
            detail="Session ID cannot exceed 128 characters"
        )
    
    return session_id


async def get_request_info(request: Request) -> Dict[str, Any]:
    """
    Extract request information for logging and monitoring.
    
    Args:
        request (Request): FastAPI request object
        
    Returns:
        Dict[str, Any]: Request information
    """
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "content_type": request.headers.get("content-type"),
        "content_length": request.headers.get("content-length")
    }


async def check_rate_limit(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 60
) -> bool:
    """
    Basic rate limiting dependency (placeholder for future implementation).
    
    Args:
        request (Request): FastAPI request object
        max_requests (int): Maximum requests per window
        window_seconds (int): Time window in seconds
        
    Returns:
        bool: True if request is allowed
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Placeholder - would implement proper rate limiting with Redis
    # For now, always allow requests
    return True


async def validate_content_type(
    content_type: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Validate content type for requests that require specific types.
    
    Args:
        content_type (Optional[str]): Content-Type header
        
    Returns:
        Optional[str]: Validated content type
    """
    if content_type and not content_type.startswith(('application/json', 'multipart/form-data')):
        logger.warning(f"Unsupported content type: {content_type}")
    
    return content_type


# Export dependencies
__all__ = [
    "get_current_redis_client",
    "get_current_session_manager", 
    "validate_session_id",
    "get_request_info",
    "check_rate_limit",
    "validate_content_type",
    "security"
]