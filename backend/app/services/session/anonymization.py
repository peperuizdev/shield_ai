"""
Anonymization map management for Shield AI sessions.

Handles storage and retrieval of anonymization mappings
that translate between original and anonymized data.
"""

import logging
from typing import Dict, Optional

from fastapi import HTTPException

from .storage import get_storage


logger = logging.getLogger(__name__)


def store_anonymization_map(session_id: str, anonymization_map: Dict[str, str], 
                           ttl: Optional[int] = None) -> bool:
    """
    Store anonymization map in Redis with TTL.
    
    Args:
        session_id: Unique session identifier
        anonymization_map: Map of original -> anonymized data
        ttl: Time to live in seconds
        
    Returns:
        bool: True if stored successfully
        
    Raises:
        HTTPException: If storage fails
    """
    try:
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")
        
        if not isinstance(anonymization_map, dict):
            raise ValueError("Anonymization map must be a dictionary")
        
        storage = get_storage()
        
        success = storage.store_json("map", session_id, anonymization_map, ttl)
        
        if not success:
            raise Exception("Failed to store anonymization map in Redis")
        
        metadata = {
            "map_size": len(anonymization_map),
            "session_id": session_id
        }
        storage.store_json("meta", session_id, metadata, ttl)
        
        logger.info(f"Stored anonymization map for session {session_id} with TTL {ttl or storage.default_ttl}s")
        return True
        
    except ValueError as e:
        logger.error(f"Validation error for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error storing anonymization map for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store session: {str(e)}"
        )


def get_anonymization_map(session_id: str) -> Dict[str, str]:
    """
    Retrieve anonymization map from Redis.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dict[str, str]: Anonymization map
        
    Raises:
        HTTPException: If session not found or retrieval fails
    """
    try:
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")
        
        storage = get_storage()
        anonymization_map = storage.get_json("map", session_id)
        
        if anonymization_map is None:
            logger.warning(f"Session {session_id} not found or expired")
            raise HTTPException(
                status_code=404,
                detail=f"Anonymization map not found for session: {session_id}"
            )
        
        logger.debug(f"Retrieved anonymization map for session {session_id}")
        return anonymization_map
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving anonymization map for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session: {str(e)}"
        )