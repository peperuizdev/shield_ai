"""
Session management endpoints for Shield AI.

Provides CRUD operations for anonymization sessions including
creation, status checking, updating TTL, and deletion.

Author: Shield AI Team - Backend Developer
Date: 2025-09-19
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, Query, Depends
from fastapi.responses import JSONResponse

from core.app import app
from services.session_manager import (
    store_anonymization_map,
    get_session_status,
    delete_session,
    extend_session_ttl,
    list_active_sessions,
    cleanup_expired_sessions,
    get_session_manager
)
from models.requests import SessionCreateRequest, SessionUpdateRequest
from models.responses import (
    SessionStatusResponse,
    SessionCreateResponse,
    SessionDeleteResponse,
    SessionListResponse,
    BaseResponse
)


logger = logging.getLogger(__name__)

# Create router for session endpoints
router = APIRouter(prefix="/sessions", tags=["Session Management"])


@router.post(
    "/",
    response_model=SessionCreateResponse,
    status_code=201,
    summary="Create new session",
    description="Create a new anonymization session with provided mapping data"
)
async def create_session(request: SessionCreateRequest):
    """
    Create a new anonymization session.
    
    Stores the anonymization map in Redis with specified TTL.
    
    Args:
        request (SessionCreateRequest): Session creation parameters
        
    Returns:
        SessionCreateResponse: Created session information
        
    Raises:
        HTTPException: If session creation fails
    """
    try:
        logger.info(f"Creating session: {request.session_id}")
        
        # Store the anonymization map
        success = store_anonymization_map(
            session_id=request.session_id,
            anonymization_map=request.anonymization_map,
            ttl=request.ttl
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create session"
            )
        
        # Get session info to return
        session_info = get_session_status(request.session_id)
        
        logger.info(f"Session {request.session_id} created successfully")
        
        return SessionCreateResponse(
            success=True,
            message=f"Session {request.session_id} created successfully",
            session_id=request.session_id,
            ttl_seconds=session_info.get("ttl_seconds", request.ttl or 3600),
            expires_at=session_info.get("expires_at", datetime.now()),
            map_size=len(request.anonymization_map)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session {request.session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error creating session: {str(e)}"
        )


@router.get(
    "/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Get session status",
    description="Get detailed status information for a specific session"
)
async def get_session_status_endpoint(
    session_id: str = Path(
        ...,
        description="Session identifier",
        regex=r'^[a-zA-Z0-9_\-]+$',
        example="session_123"
    )
):
    """
    Get session status and metadata.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        SessionStatusResponse: Session status information
    """
    try:
        logger.debug(f"Getting status for session: {session_id}")
        
        session_info = get_session_status(session_id)
        
        # Handle case where session doesn't exist
        if not session_info.get("exists", False):
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        return SessionStatusResponse(
            success=True,
            message="Session status retrieved successfully",
            session_id=session_info["session_id"],
            exists=session_info["exists"],
            status=session_info.get("status", "unknown"),
            ttl_seconds=session_info.get("ttl_seconds", -1),
            expires_in=session_info.get("expires_in"),
            expires_at=session_info.get("expires_at"),
            created_at=session_info.get("created_at"),
            map_size=session_info.get("map_size"),
            metadata=session_info.get("metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error retrieving session status: {str(e)}"
        )


@router.put(
    "/{session_id}",
    response_model=SessionStatusResponse,
    summary="Update session",
    description="Update session TTL or extend existing session lifetime"
)
async def update_session(
    session_id: str = Path(
        ...,
        description="Session identifier",
        regex=r'^[a-zA-Z0-9_\-]+$',
        example="session_123"
    ),
    request: SessionUpdateRequest = None
):
    """
    Update session TTL or extend session lifetime.
    
    Args:
        session_id (str): Session identifier
        request (SessionUpdateRequest): Update parameters
        
    Returns:
        SessionStatusResponse: Updated session information
    """
    try:
        logger.info(f"Updating session: {session_id}")
        
        # Check if session exists first
        session_info = get_session_status(session_id)
        if not session_info.get("exists", False):
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Extend TTL if requested
        if request and request.extend_by:
            success = extend_session_ttl(session_id, request.extend_by)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to extend session TTL"
                )
            logger.info(f"Extended session {session_id} TTL by {request.extend_by} seconds")
        
        # Get updated session info
        updated_info = get_session_status(session_id)
        
        return SessionStatusResponse(
            success=True,
            message=f"Session {session_id} updated successfully",
            session_id=updated_info["session_id"],
            exists=updated_info["exists"],
            status=updated_info.get("status", "unknown"),
            ttl_seconds=updated_info.get("ttl_seconds", -1),
            expires_in=updated_info.get("expires_in"),
            expires_at=updated_info.get("expires_at"),
            created_at=updated_info.get("created_at"),
            map_size=updated_info.get("map_size"),
            metadata=updated_info.get("metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error updating session: {str(e)}"
        )


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    summary="Delete session",
    description="Delete a session and all its associated data"
)
async def delete_session_endpoint(
    session_id: str = Path(
        ...,
        description="Session identifier",
        regex=r'^[a-zA-Z0-9_\-]+$',
        example="session_123"
    )
):
    """
    Delete session and its metadata.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        SessionDeleteResponse: Deletion result
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        deletion_result = delete_session(session_id)
        
        if not deletion_result.get("success", False):
            # Session might not exist, but that's ok for DELETE operation
            logger.warning(f"Session {session_id} was not found for deletion")
        
        return SessionDeleteResponse(
            success=True,
            message=f"Session {session_id} deletion completed",
            session_id=session_id,
            session_deleted=deletion_result.get("session_deleted", False),
            metadata_deleted=deletion_result.get("metadata_deleted", False)
        )
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error deleting session: {str(e)}"
        )


@router.get(
    "/",
    response_model=SessionListResponse,
    summary="List active sessions",
    description="Get a list of all active sessions with their status information"
)
async def list_sessions(
    limit: int = Query(
        50,
        description="Maximum number of sessions to return",
        ge=1,
        le=1000
    ),
    offset: int = Query(
        0,
        description="Number of sessions to skip",
        ge=0
    )
):
    """
    List all active sessions.
    
    Args:
        limit (int): Maximum number of sessions to return
        offset (int): Number of sessions to skip for pagination
        
    Returns:
        SessionListResponse: List of active sessions
    """
    try:
        logger.debug("Listing active sessions")
        
        active_sessions = list_active_sessions()
        
        # Apply pagination
        total_sessions = len(active_sessions)
        paginated_sessions = active_sessions[offset:offset + limit]
        
        # Convert to response format
        session_responses = []
        for session_info in paginated_sessions:
            session_response = SessionStatusResponse(
                success=True,
                session_id=session_info["session_id"],
                exists=session_info["exists"],
                status=session_info.get("status", "unknown"),
                ttl_seconds=session_info.get("ttl_seconds", -1),
                expires_in=session_info.get("expires_in"),
                expires_at=session_info.get("expires_at"),
                created_at=session_info.get("created_at"),
                map_size=session_info.get("map_size"),
                metadata=session_info.get("metadata")
            )
            session_responses.append(session_response)
        
        return SessionListResponse(
            success=True,
            message=f"Retrieved {len(session_responses)} active sessions",
            total_sessions=total_sessions,
            sessions=session_responses
        )
        
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error listing sessions: {str(e)}"
        )


@router.post(
    "/cleanup",
    response_model=BaseResponse,
    summary="Cleanup expired sessions",
    description="Manually trigger cleanup of expired sessions (mainly for statistics)"
)
async def cleanup_sessions():
    """
    Manually trigger session cleanup.
    
    Note: Redis automatically handles TTL expiration, but this endpoint
    provides cleanup statistics and manual maintenance capabilities.
    
    Returns:
        BaseResponse: Cleanup operation results
    """
    try:
        logger.info("Manual session cleanup initiated")
        
        cleanup_stats = cleanup_expired_sessions()
        
        if "error" in cleanup_stats:
            raise HTTPException(
                status_code=500,
                detail=f"Cleanup failed: {cleanup_stats['error']}"
            )
        
        return BaseResponse(
            success=True,
            message=f"Session cleanup completed. Active: {cleanup_stats.get('active_sessions', 0)}, "
                   f"Expired: {cleanup_stats.get('expired_sessions', 0)}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during session cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during cleanup: {str(e)}"
        )


@router.post(
    "/{session_id}/setup-dummy", 
    response_model=SessionCreateResponse,
    summary="Setup dummy session",
    description="Create a session with dummy/test data for development and testing"
)
async def setup_dummy_session(
    session_id: str = Path(
        ...,
        description="Session identifier for dummy data",
        regex=r'^[a-zA-Z0-9_\-]+$',
        example="test_session_001"
    )
):
    """
    Setup a session with dummy anonymization data for testing.
    
    This endpoint creates a session with predefined test data
    useful for development, testing, and demonstrations.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        SessionCreateResponse: Created session information
    """
    try:
        logger.info(f"Setting up dummy session: {session_id}")
        
        # Define dummy anonymization map
        dummy_map = {
            # Full names
            "Juan Pérez": "María González",
            # Emails  
            "juan.perez@email.com": "maria.gonzalez@email.com",
            # Phones
            "612345678": "687654321",
            # DNIs
            "12345678A": "87654321B", 
            # Addresses
            "Calle Mayor 123": "Avenida Libertad 456",
            # Cities
            "Madrid": "Barcelona",
            # Postal codes
            "28001": "08001",
            # Banks
            "Banco Santander": "Banco BBVA",
            # IBANs
            "ES91 2100 0418 4502 0005 1332": "ES76 0182 6473 8901 2345 6789"
        }
        
        # Store dummy session
        success = store_anonymization_map(
            session_id=session_id,
            anonymization_map=dummy_map,
            ttl=3600  # 1 hour TTL for dummy sessions
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create dummy session"
            )
        
        # Get session info
        session_info = get_session_status(session_id)
        
        logger.info(f"Dummy session {session_id} created successfully")
        
        return SessionCreateResponse(
            success=True,
            message=f"Dummy session {session_id} created with test data",
            session_id=session_id,
            ttl_seconds=session_info.get("ttl_seconds", 3600),
            expires_at=session_info.get("expires_at", datetime.now()),
            map_size=len(dummy_map)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dummy session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error creating dummy session: {str(e)}"
        )


# Add the router to the main app
app.include_router(router)


# Export router for testing
__all__ = ["router"]