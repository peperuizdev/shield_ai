"""
Session manager for Shield AI.

Handles session lifecycle management including status checking,
TTL extension, deletion, and listing of active sessions.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .storage import get_storage
from .anonymization import get_anonymization_map


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager for handling session lifecycle in Redis.
    
    Provides functionality for managing session status, TTL,
    and cleanup operations.
    """
    
    def __init__(self):
        """Initialize session manager."""
        self.storage = get_storage()
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get session status and metadata.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict[str, Any]: Session status information
        """
        try:
            exists = self.storage.exists("map", session_id)
            ttl = self.storage.get_ttl("map", session_id) if exists else -1
            
            status_info = {
                "session_id": session_id,
                "exists": bool(exists),
                "ttl_seconds": ttl,
                "status": "active" if ttl > 0 else "expired" if exists else "not_found"
            }
            
            if ttl > 0:
                status_info["expires_in"] = f"{ttl // 60} minutes {ttl % 60} seconds"
                status_info["expires_at"] = datetime.now() + timedelta(seconds=ttl)
            
            metadata = self.storage.get_json("meta", session_id)
            if metadata:
                status_info["metadata"] = metadata
                status_info["created_at"] = datetime.fromtimestamp(metadata.get("created_at", 0)) if "created_at" in metadata else None
                status_info["map_size"] = metadata.get("map_size", 0)
            
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
        Delete session and all its associated data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict[str, Any]: Deletion result
        """
        try:
            deleted_map = self.storage.delete("map", session_id)
            deleted_meta = self.storage.delete("meta", session_id)
            deleted_llm = self.storage.delete("llm", session_id)
            deleted_request = self.storage.delete("request", session_id)
            
            total_deleted = deleted_map or deleted_meta or deleted_llm or deleted_request
            
            result = {
                "session_id": session_id,
                "session_deleted": bool(deleted_map),
                "metadata_deleted": bool(deleted_meta),
                "llm_deleted": bool(deleted_llm),
                "request_deleted": bool(deleted_request),
                "success": bool(total_deleted)
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
    
    def extend_session_ttl(self, session_id: str, additional_seconds: Optional[int] = None) -> bool:
        """
        Extend session TTL for all session data.
        
        Args:
            session_id: Session identifier
            additional_seconds: Additional seconds to add to TTL
            
        Returns:
            bool: True if TTL was extended
        """
        try:
            if additional_seconds is None:
                additional_seconds = self.storage.default_ttl
            
            if not self.storage.exists("map", session_id):
                return False
            
            map_extended = self.storage.extend_ttl("map", session_id, additional_seconds)
            self.storage.extend_ttl("meta", session_id, additional_seconds)
            self.storage.extend_ttl("llm", session_id, additional_seconds)
            self.storage.extend_ttl("request", session_id, additional_seconds)
            
            if map_extended:
                logger.info(f"Extended TTL for session {session_id} by {additional_seconds}s")
            
            return bool(map_extended)
            
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
            pattern = f"{self.storage.key_prefix}:*"
            keys = self.storage.redis_client.keys(pattern)
            
            session_ids = set()
            for key in keys:
                if ":meta:" in key or ":llm:" in key or ":request:" in key:
                    continue
                
                session_id = key.split(":", 1)[1] if ":" in key else key
                session_ids.add(session_id)
            
            active_sessions = []
            for session_id in session_ids:
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
        Clean up expired sessions.
        
        Returns:
            Dict[str, Any]: Cleanup statistics
        """
        try:
            pattern = f"{self.storage.key_prefix}:*"
            keys = self.storage.redis_client.keys(pattern)
            
            expired_count = 0
            total_count = 0
            
            for key in keys:
                if ":meta:" in key or ":llm:" in key or ":request:" in key:
                    continue
                
                total_count += 1
                ttl = self.storage.redis_client.ttl(key)
                
                if ttl == -2:
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


def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get session status using global session manager."""
    return get_session_manager().get_session_status(session_id)


def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete session using global session manager."""
    return get_session_manager().delete_session(session_id)


def extend_session_ttl(session_id: str, additional_seconds: Optional[int] = None) -> bool:
    """Extend session TTL using global session manager."""
    return get_session_manager().extend_session_ttl(session_id, additional_seconds)


def list_active_sessions() -> List[Dict[str, Any]]:
    """List active sessions using global session manager."""
    return get_session_manager().list_active_sessions()


def cleanup_expired_sessions() -> Dict[str, Any]:
    """Cleanup expired sessions using global session manager."""
    return get_session_manager().cleanup_expired_sessions()