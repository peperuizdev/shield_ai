"""
Image Anonymization Session Management for Shield AI

Manages storage and retrieval of image anonymization maps in Redis.
Used to store original image regions for deanonymization.
"""

import json
import logging
from typing import Dict, Any, Optional

from core.redis_client import get_redis_client
from core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL = settings.session_ttl


def store_anonymization_map(
    session_id: str, 
    anonymization_map: Dict[str, Any],
    ttl: int = DEFAULT_TTL
) -> bool:
    """
    Store image anonymization map in Redis.
    
    The map contains:
    - Original image regions (base64 encoded)
    - Bounding boxes of detected faces/plates
    - Detection metadata
    
    Args:
        session_id (str): Unique session identifier
        anonymization_map (Dict[str, Any]): Map with anonymization data
        ttl (int): Time-to-live in seconds
        
    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        client = get_redis_client()
        
        map_json = json.dumps(anonymization_map)
        
        redis_key = f"image_anon_map:{session_id}"
        
        client.setex(
            name=redis_key,
            time=ttl,
            value=map_json
        )
        
        logger.info(f"✅ Stored image anonymization map for session: {session_id} (TTL: {ttl}s)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error storing image map for {session_id}: {e}")
        return False


def get_anonymization_map(session_id: str) -> Dict[str, Any]:
    """
    Retrieve image anonymization map from Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        Dict[str, Any]: Anonymization map with original regions
        
    Raises:
        ValueError: If session not found or expired
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        map_json = client.get(redis_key)
        
        if map_json is None:
            logger.warning(f"⚠️  Image session not found or expired: {session_id}")
            raise ValueError(f"Session '{session_id}' not found or expired")
        
        anonymization_map = json.loads(map_json)
        
        logger.info(f"✅ Retrieved image anonymization map for session: {session_id}")
        
        return anonymization_map
        
    except ValueError:
        raise
        
    except Exception as e:
        logger.error(f"❌ Error retrieving image map for {session_id}: {e}")
        raise ValueError(f"Error retrieving session: {e}")


def delete_anonymization_map(session_id: str) -> bool:
    """
    Delete image anonymization map from Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        bool: True if deleted, False if not found
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        result = client.delete(redis_key)
        
        if result > 0:
            logger.info(f"✅ Deleted image anonymization map for session: {session_id}")
            return True
        else:
            logger.warning(f"⚠️  Image session not found: {session_id}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error deleting image map for {session_id}: {e}")
        return False


def session_exists(session_id: str) -> bool:
    """
    Check if image session exists in Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        bool: True if exists, False otherwise
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        return client.exists(redis_key) > 0
        
    except Exception as e:
        logger.error(f"❌ Error checking image session {session_id}: {e}")
        return False


def get_session_ttl(session_id: str) -> Optional[int]:
    """
    Get remaining TTL for an image session.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        Optional[int]: Remaining seconds, or None if session doesn't exist
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        ttl = client.ttl(redis_key)
        
        if ttl == -2:
            return None
        elif ttl == -1:
            return -1
        else:
            return ttl
        
    except Exception as e:
        logger.error(f"❌ Error getting TTL for image session {session_id}: {e}")
        return None


def extend_session_ttl(session_id: str, additional_seconds: int = 3600) -> bool:
    """
    Extend image session TTL.
    
    Args:
        session_id (str): Session identifier
        additional_seconds (int): Seconds to add
        
    Returns:
        bool: True if extended successfully
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        result = client.expire(redis_key, additional_seconds)
        
        if result:
            logger.info(f"✅ Extended TTL for image session: {session_id} (+{additional_seconds}s)")
            return True
        else:
            logger.warning(f"⚠️  Cannot extend TTL, image session not found: {session_id}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error extending TTL for image session {session_id}: {e}")
        return False


__all__ = [
    "store_anonymization_map",
    "get_anonymization_map",
    "delete_anonymization_map",
    "session_exists",
    "get_session_ttl",
    "extend_session_ttl"
]