"""
Redis storage abstraction for session management.

Provides generic Redis operations for storing and retrieving
session-related data with TTL management.
"""

import json
import logging
from typing import Dict, Any, Optional

from core.redis_client import get_redis_client
from core.config import settings


logger = logging.getLogger(__name__)


class RedisStorage:
    """
    Generic Redis storage for session data.
    
    Provides abstracted methods for storing different types of
    session data with consistent TTL and key management.
    """
    
    def __init__(self):
        """Initialize Redis storage."""
        self.redis_client = get_redis_client()
        self.key_prefix = settings.session_key_prefix
        self.default_ttl = settings.session_ttl
    
    def _build_key(self, key_type: str, session_id: str) -> str:
        """
        Build Redis key for session data.
        
        Args:
            key_type: Type of data (e.g., 'map', 'llm', 'request', 'meta')
            session_id: Session identifier
            
        Returns:
            str: Complete Redis key
        """
        if key_type == "map":
            return f"{self.key_prefix}:{session_id}"
        return f"{self.key_prefix}:{key_type}:{session_id}"
    
    def store_json(self, key_type: str, session_id: str, data: Dict[str, Any], 
                   ttl: Optional[int] = None) -> bool:
        """
        Store JSON-serializable data in Redis.
        
        Args:
            key_type: Type of data being stored
            session_id: Session identifier
            data: Data to store (must be JSON-serializable)
            ttl: Time to live in seconds
            
        Returns:
            bool: True if stored successfully
        """
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            key = self._build_key(key_type, session_id)
            data_json = json.dumps(data)
            success = self.redis_client.setex(key, ttl, data_json)
            
            if success:
                logger.debug(f"Stored {key_type} for session {session_id}")
            
            return bool(success)
            
        except json.JSONEncodeError as e:
            logger.error(f"JSON encoding error for {key_type} in session {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error storing {key_type} for session {session_id}: {e}")
            return False
    
    def get_json(self, key_type: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and deserialize JSON data from Redis.
        
        Args:
            key_type: Type of data to retrieve
            session_id: Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Deserialized data or None if not found
        """
        try:
            key = self._build_key(key_type, session_id)
            data = self.redis_client.get(key)
            
            if not data:
                logger.debug(f"No {key_type} found for session {session_id}")
                return None
            
            return json.loads(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for {key_type} in session {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving {key_type} for session {session_id}: {e}")
            return None
    
    def store_text(self, key_type: str, session_id: str, text: str, 
                   ttl: Optional[int] = None) -> bool:
        """
        Store plain text in Redis.
        
        Args:
            key_type: Type of data being stored
            session_id: Session identifier
            text: Text to store
            ttl: Time to live in seconds
            
        Returns:
            bool: True if stored successfully
        """
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            key = self._build_key(key_type, session_id)
            success = self.redis_client.setex(key, ttl, text)
            
            if success:
                logger.debug(f"Stored {key_type} text for session {session_id}")
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Error storing {key_type} text for session {session_id}: {e}")
            return False
    
    def get_text(self, key_type: str, session_id: str) -> Optional[str]:
        """
        Retrieve plain text from Redis.
        
        Args:
            key_type: Type of data to retrieve
            session_id: Session identifier
            
        Returns:
            Optional[str]: Text data or None if not found
        """
        try:
            key = self._build_key(key_type, session_id)
            data = self.redis_client.get(key)
            
            if not data:
                logger.debug(f"No {key_type} text found for session {session_id}")
                return None
            
            if isinstance(data, bytes):
                return data.decode('utf-8')
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving {key_type} text for session {session_id}: {e}")
            return None
    
    def exists(self, key_type: str, session_id: str) -> bool:
        """
        Check if data exists in Redis.
        
        Args:
            key_type: Type of data to check
            session_id: Session identifier
            
        Returns:
            bool: True if data exists
        """
        try:
            key = self._build_key(key_type, session_id)
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence of {key_type} for session {session_id}: {e}")
            return False
    
    def get_ttl(self, key_type: str, session_id: str) -> int:
        """
        Get TTL for stored data.
        
        Args:
            key_type: Type of data
            session_id: Session identifier
            
        Returns:
            int: TTL in seconds (-1 if no expiry, -2 if doesn't exist)
        """
        try:
            key = self._build_key(key_type, session_id)
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for {key_type} in session {session_id}: {e}")
            return -2
    
    def delete(self, key_type: str, session_id: str) -> bool:
        """
        Delete data from Redis.
        
        Args:
            key_type: Type of data to delete
            session_id: Session identifier
            
        Returns:
            bool: True if deleted
        """
        try:
            key = self._build_key(key_type, session_id)
            deleted = self.redis_client.delete(key)
            
            if deleted:
                logger.debug(f"Deleted {key_type} for session {session_id}")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Error deleting {key_type} for session {session_id}: {e}")
            return False
    
    def extend_ttl(self, key_type: str, session_id: str, additional_seconds: int) -> bool:
        """
        Extend TTL for stored data.
        
        Args:
            key_type: Type of data
            session_id: Session identifier
            additional_seconds: Additional seconds to add to TTL
            
        Returns:
            bool: True if TTL was extended
        """
        try:
            key = self._build_key(key_type, session_id)
            
            if not self.redis_client.exists(key):
                return False
            
            current_ttl = self.redis_client.ttl(key)
            new_ttl = max(current_ttl + additional_seconds, additional_seconds)
            
            return bool(self.redis_client.expire(key, new_ttl))
            
        except Exception as e:
            logger.error(f"Error extending TTL for {key_type} in session {session_id}: {e}")
            return False


_storage_instance: Optional[RedisStorage] = None


def get_storage() -> RedisStorage:
    """
    Get global Redis storage instance.
    
    Returns:
        RedisStorage: Storage instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = RedisStorage()
    
    return _storage_instance