"""
Session management service for Shield AI.

Handles session-based storage and retrieval of anonymization maps
in Redis with TTL, cleanup, and session lifecycle management.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import HTTPException

from core.config import settings
from core.redis_client import get_redis_client


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager for handling anonymization maps in Redis.
    
    Provides functionality for storing, retrieving, and managing
    session-based anonymization data with automatic cleanup.
    """
    
    def __init__(self):
        """Initialize session manager with Redis client."""
        self.redis_client = get_redis_client()
        self.key_prefix = settings.session_key_prefix
        self.default_ttl = settings.session_ttl
    
    def _get_session_key(self, session_id: str) -> str:
        """
        Generate Redis key for session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            str: Redis key for the session
        """
        return f"{self.key_prefix}:{session_id}"
    
    def _get_metadata_key(self, session_id: str) -> str:
        """
        Generate Redis key for session metadata.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            str: Redis key for session metadata
        """
        return f"{self.key_prefix}:meta:{session_id}"
    
    def store_anonymization_map(self, session_id: str, anonymization_map: Dict[str, str], 
                               ttl: Optional[int] = None) -> bool:
        """
        Store anonymization map in Redis with TTL.
        
        Args:
            session_id (str): Unique session identifier
            anonymization_map (Dict[str, str]): Map of original -> anonymized data
            ttl (Optional[int]): Time to live in seconds (default: from settings)
            
        Returns:
            bool: True if stored successfully, False otherwise
            
        Raises:
            HTTPException: If storage fails
        """
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            # Validate input
            if not session_id or not session_id.strip():
                raise ValueError("Session ID cannot be empty")
            
            if not isinstance(anonymization_map, dict):
                raise ValueError("Anonymization map must be a dictionary")
            
            session_key = self._get_session_key(session_id)
            metadata_key = self._get_metadata_key(session_id)
            
            # Store anonymization map
            map_json = json.dumps(anonymization_map)
            success = self.redis_client.setex(session_key, ttl, map_json)
            
            if not success:
                raise Exception("Failed to store anonymization map in Redis")
            
            # Store session metadata
            metadata = {
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
                "session_id": session_id,
                "map_size": len(anonymization_map),
                "ttl": ttl
            }
            
            metadata_json = json.dumps(metadata)
            self.redis_client.setex(metadata_key, ttl, metadata_json)
            
            logger.info(f"Stored anonymization map for session {session_id} with TTL {ttl}s")
            return True
            
        except json.JSONEncodeError as e:
            logger.error(f"JSON encoding error for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid anonymization map format: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error storing session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store session: {str(e)}"
            )
    
    def get_anonymization_map(self, session_id: str) -> Dict[str, str]:
        """
        Retrieve anonymization map from Redis.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, str]: Anonymization map
            
        Raises:
            HTTPException: If session not found or retrieval fails
        """
        try:
            if not session_id or not session_id.strip():
                raise ValueError("Session ID cannot be empty")
            
            session_key = self._get_session_key(session_id)
            map_data = self.redis_client.get(session_key)
            
            if not map_data:
                logger.warning(f"Session {session_id} not found or expired")
                raise HTTPException(
                    status_code=404,
                    detail=f"Anonymization map not found for session: {session_id}"
                )
            
            anonymization_map = json.loads(map_data)
            logger.debug(f"Retrieved anonymization map for session {session_id}")
            
            return anonymization_map
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error decoding anonymization map"
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve session: {str(e)}"
            )
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get session status and metadata.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Session status information
        """
        try:
            session_key = self._get_session_key(session_id)
            metadata_key = self._get_metadata_key(session_id)
            
            # Check if session exists
            exists = self.redis_client.exists(session_key)
            ttl = self.redis_client.ttl(session_key) if exists else -1
            
            status_info = {
                "session_id": session_id,
                "exists": bool(exists),
                "ttl_seconds": ttl,
                "status": "active" if ttl > 0 else "expired" if exists else "not_found"
            }
            
            if ttl > 0:
                status_info["expires_in"] = f"{ttl // 60} minutes {ttl % 60} seconds"
                status_info["expires_at"] = datetime.now() + timedelta(seconds=ttl)
            
            # Get metadata if available
            metadata_data = self.redis_client.get(metadata_key)
            if metadata_data:
                try:
                    metadata = json.loads(metadata_data)
                    status_info["metadata"] = metadata
                    status_info["created_at"] = datetime.fromtimestamp(metadata.get("created_at", 0))
                    status_info["map_size"] = metadata.get("map_size", 0)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode metadata for session {session_id}")
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting status for session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "exists": False,
                "error": str(e),
                "status": "error"
            }
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete session and its metadata.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Deletion result
        """
        try:
            session_key = self._get_session_key(session_id)
            metadata_key = self._get_metadata_key(session_id)
            
            # Delete both session data and metadata
            deleted_session = self.redis_client.delete(session_key)
            deleted_metadata = self.redis_client.delete(metadata_key)
            
            result = {
                "session_id": session_id,
                "session_deleted": bool(deleted_session),
                "metadata_deleted": bool(deleted_metadata),
                "success": bool(deleted_session or deleted_metadata)
            }
            
            if result["success"]:
                logger.info(f"Deleted session {session_id}")
            else:
                logger.warning(f"Session {session_id} was not found for deletion")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    
    def extend_session_ttl(self, session_id: str, additional_seconds: int = None) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id (str): Session identifier
            additional_seconds (int): Additional seconds to add to TTL
            
        Returns:
            bool: True if TTL was extended, False otherwise
        """
        try:
            if additional_seconds is None:
                additional_seconds = self.default_ttl
            
            session_key = self._get_session_key(session_id)
            metadata_key = self._get_metadata_key(session_id)
            
            # Check if session exists
            if not self.redis_client.exists(session_key):
                return False
            
            # Extend TTL for both session and metadata
            current_ttl = self.redis_client.ttl(session_key)
            new_ttl = max(current_ttl + additional_seconds, additional_seconds)
            
            session_extended = self.redis_client.expire(session_key, new_ttl)
            metadata_extended = self.redis_client.expire(metadata_key, new_ttl)
            
            if session_extended:
                logger.info(f"Extended TTL for session {session_id} by {additional_seconds}s")
            
            return bool(session_extended)
            
        except Exception as e:
            logger.error(f"Error extending TTL for session {session_id}: {str(e)}")
            return False
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.
        
        Returns:
            List[Dict[str, Any]]: List of active session information
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            active_sessions = []
            for key in keys:
                # Skip metadata keys
                if ":meta:" in key:
                    continue
                
                # Extract session ID from key
                session_id = key.split(":", 1)[1] if ":" in key else key
                
                # Get session status
                status = self.get_session_status(session_id)
                if status.get("exists", False):
                    active_sessions.append(status)
            
            logger.debug(f"Found {len(active_sessions)} active sessions")
            return active_sessions
            
        except Exception as e:
            logger.error(f"Error listing active sessions: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """
        Clean up expired sessions (Redis handles this automatically, but useful for stats).
        
        Returns:
            Dict[str, Any]: Cleanup statistics
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            expired_count = 0
            total_count = 0
            
            for key in keys:
                if ":meta:" in key:
                    continue
                
                total_count += 1
                ttl = self.redis_client.ttl(key)
                
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1
            
            cleanup_stats = {
                "total_sessions_checked": total_count,
                "expired_sessions": expired_count,
                "active_sessions": total_count - expired_count,
                "cleanup_time": datetime.now()
            }
            
            logger.info(f"Session cleanup: {expired_count} expired, {total_count - expired_count} active")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            return {"error": str(e)}


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get global session manager instance.
    
    Returns:
        SessionManager: Session manager instance
    """
    global _session_manager
    
    if _session_manager is None:
        _session_manager = SessionManager()
    
    return _session_manager


# Convenience functions that use the global session manager
def store_anonymization_map(session_id: str, anonymization_map: Dict[str, str], 
                          ttl: Optional[int] = None) -> bool:
    """Store anonymization map using global session manager."""
    return get_session_manager().store_anonymization_map(session_id, anonymization_map, ttl)


def get_anonymization_map(session_id: str) -> Dict[str, str]:
    """Get anonymization map using global session manager."""
    return get_session_manager().get_anonymization_map(session_id)


def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get session status using global session manager."""
    return get_session_manager().get_session_status(session_id)


def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete session using global session manager."""
    return get_session_manager().delete_session(session_id)


def extend_session_ttl(session_id: str, additional_seconds: int = None) -> bool:
    """Extend session TTL using global session manager."""
    return get_session_manager().extend_session_ttl(session_id, additional_seconds)


def list_active_sessions() -> List[Dict[str, Any]]:
    """List active sessions using global session manager."""
    return get_session_manager().list_active_sessions()


def cleanup_expired_sessions() -> Dict[str, Any]:
    """Cleanup expired sessions using global session manager."""
    return get_session_manager().cleanup_expired_sessions()


# Export main functions
def store_llm_response(session_id: str, llm_response: str, ttl_seconds: int = None) -> bool:
    """
    Store LLM response for a session (for streaming purposes).
    
    Args:
        session_id (str): Session identifier
        llm_response (str): LLM response text
        ttl_seconds (int, optional): TTL in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = get_session_manager()
    try:
        # Store LLM response in a separate key
        llm_key = f"{manager.key_prefix}:llm:{session_id}"
        
        # Use provided TTL or default
        ttl = ttl_seconds or manager.default_ttl
        
        # Store the LLM response
        manager.redis_client.setex(llm_key, ttl, llm_response)
        
        logger.info(f"LLM response stored for session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing LLM response for session {session_id}: {e}")
        return False

def get_llm_response(session_id: str) -> Optional[str]:
    """
    Retrieve LLM response for a session.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        Optional[str]: LLM response text or None if not found
    """
    manager = get_session_manager()
    try:
        llm_key = f"{manager.key_prefix}:llm:{session_id}"
        llm_response = manager.redis_client.get(llm_key)
        
        if llm_response:
            return llm_response.decode('utf-8')
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving LLM response for session {session_id}: {e}")
        return None

__all__ = [
    "SessionManager",
    "get_session_manager",
    "store_anonymization_map",
    "get_anonymization_map", 
    "get_session_status",
    "delete_session",
    "extend_session_ttl",
    "list_active_sessions",
    "cleanup_expired_sessions",
    "store_llm_response",
    "get_llm_response"
]