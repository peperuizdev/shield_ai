"""
Session Manager for Image Anonymization

Manages storage and retrieval of anonymization maps in Redis.
Used to store original image regions for deanonymization.
"""

import json
import logging
from typing import Dict, Any, Optional
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)

# ==========================================
# REDIS CONNECTION
# ==========================================

# Configuración de Redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # Cambiar si tu Redis tiene password

# TTL por defecto: 1 hora
DEFAULT_TTL = 3600


def get_redis_client() -> redis.Redis:
    """
    Get Redis client connection.
    
    Returns:
        redis.Redis: Redis client instance
        
    Raises:
        redis.ConnectionError: If cannot connect to Redis
    """
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,  # Importante: devuelve strings en vez de bytes
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        client.ping()
        
        return client
        
    except redis.ConnectionError as e:
        logger.error(f"❌ Cannot connect to Redis: {e}")
        logger.error(f"Redis config: {REDIS_HOST}:{REDIS_PORT} DB:{REDIS_DB}")
        raise


def get_session_manager() -> redis.Redis:
    """
    Alias for get_redis_client() for backwards compatibility.
    
    Returns:
        redis.Redis: Redis client instance
    """
    return get_redis_client()


# ==========================================
# ANONYMIZATION MAP STORAGE
# ==========================================

def store_anonymization_map(
    session_id: str, 
    anonymization_map: Dict[str, Any],
    ttl: int = DEFAULT_TTL
) -> bool:
    """
    Store anonymization map in Redis.
    
    The map contains:
    - Original image regions (base64 encoded)
    - Bounding boxes of detected faces/plates
    - Detection metadata
    
    Args:
        session_id (str): Unique session identifier
        anonymization_map (Dict[str, Any]): Map with anonymization data
        ttl (int): Time-to-live in seconds (default: 1 hour)
        
    Returns:
        bool: True if stored successfully, False otherwise
        
    Example:
        >>> map_data = {
        ...     'faces': [{'id': 'face_1', 'bbox': [...], 'original_base64': '...'}],
        ...     'plates': [{'id': 'plate_1', 'bbox': [...], 'original_base64': '...'}]
        ... }
        >>> store_anonymization_map('session_123', map_data)
        True
    """
    try:
        client = get_redis_client()
        
        # Convertir el mapa a JSON
        map_json = json.dumps(anonymization_map)
        
        # Clave en Redis
        redis_key = f"image_anon_map:{session_id}"
        
        # Guardar con TTL
        client.setex(
            name=redis_key,
            time=ttl,
            value=map_json
        )
        
        logger.info(f"✅ Stored anonymization map for session: {session_id} (TTL: {ttl}s)")
        
        return True
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error storing map for {session_id}: {e}")
        return False
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON serialization error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error storing map: {e}")
        return False


def get_anonymization_map(session_id: str) -> Dict[str, Any]:
    """
    Retrieve anonymization map from Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        Dict[str, Any]: Anonymization map with original regions
        
    Raises:
        ValueError: If session not found or expired
        
    Example:
        >>> map_data = get_anonymization_map('session_123')
        >>> print(map_data['faces'])
        [{'id': 'face_1', 'bbox': [100, 150, 250, 300], ...}]
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        # Obtener datos de Redis
        map_json = client.get(redis_key)
        
        if map_json is None:
            logger.warning(f"⚠️  Session not found or expired: {session_id}")
            raise ValueError(f"Session '{session_id}' not found or expired")
        
        # Parsear JSON
        anonymization_map = json.loads(map_json)
        
        logger.info(f"✅ Retrieved anonymization map for session: {session_id}")
        
        return anonymization_map
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error retrieving map for {session_id}: {e}")
        raise ValueError(f"Cannot retrieve session data: {e}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        raise ValueError(f"Corrupted session data: {e}")
        
    except ValueError:
        raise
        
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving map: {e}")
        raise ValueError(f"Error retrieving session: {e}")


def delete_anonymization_map(session_id: str) -> bool:
    """
    Delete anonymization map from Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        bool: True if deleted, False if not found
        
    Example:
        >>> delete_anonymization_map('session_123')
        True
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        result = client.delete(redis_key)
        
        if result > 0:
            logger.info(f"✅ Deleted anonymization map for session: {session_id}")
            return True
        else:
            logger.warning(f"⚠️  Session not found: {session_id}")
            return False
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error deleting map for {session_id}: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error deleting map: {e}")
        return False


def session_exists(session_id: str) -> bool:
    """
    Check if session exists in Redis.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        bool: True if exists, False otherwise
        
    Example:
        >>> if session_exists('session_123'):
        ...     print("Session is active")
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        return client.exists(redis_key) > 0
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error checking session {session_id}: {e}")
        return False


def get_session_ttl(session_id: str) -> Optional[int]:
    """
    Get remaining TTL for a session.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        Optional[int]: Remaining seconds, or None if session doesn't exist
        
    Example:
        >>> ttl = get_session_ttl('session_123')
        >>> print(f"Session expires in {ttl} seconds")
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        ttl = client.ttl(redis_key)
        
        if ttl == -2:  # Key doesn't exist
            return None
        elif ttl == -1:  # Key exists but has no expiration
            return -1
        else:
            return ttl
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error getting TTL for {session_id}: {e}")
        return None


def extend_session_ttl(session_id: str, additional_seconds: int = 3600) -> bool:
    """
    Extend session TTL.
    
    Args:
        session_id (str): Session identifier
        additional_seconds (int): Seconds to add (default: 1 hour)
        
    Returns:
        bool: True if extended successfully
        
    Example:
        >>> extend_session_ttl('session_123', 1800)  # Add 30 minutes
        True
    """
    try:
        client = get_redis_client()
        
        redis_key = f"image_anon_map:{session_id}"
        
        result = client.expire(redis_key, additional_seconds)
        
        if result:
            logger.info(f"✅ Extended TTL for session: {session_id} (+{additional_seconds}s)")
            return True
        else:
            logger.warning(f"⚠️  Cannot extend TTL, session not found: {session_id}")
            return False
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error extending TTL for {session_id}: {e}")
        return False


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_all_sessions() -> list:
    """
    Get all active image anonymization sessions.
    
    Returns:
        list: List of session IDs
        
    Note: Use with caution in production (can be slow with many keys)
    """
    try:
        client = get_redis_client()
        
        pattern = "image_anon_map:*"
        keys = client.keys(pattern)
        
        # Extract session IDs from keys
        sessions = [key.replace("image_anon_map:", "") for key in keys]
        
        logger.info(f"📊 Found {len(sessions)} active sessions")
        
        return sessions
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error listing sessions: {e}")
        return []


def clear_all_sessions() -> int:
    """
    Clear all image anonymization sessions (DANGEROUS!).
    
    Returns:
        int: Number of sessions deleted
        
    Warning: This deletes ALL anonymization maps. Use only for testing/cleanup.
    """
    try:
        client = get_redis_client()
        
        pattern = "image_anon_map:*"
        keys = client.keys(pattern)
        
        if not keys:
            logger.info("ℹ️  No sessions to clear")
            return 0
        
        deleted = client.delete(*keys)
        
        logger.warning(f"⚠️  Cleared {deleted} anonymization sessions")
        
        return deleted
        
    except redis.RedisError as e:
        logger.error(f"❌ Redis error clearing sessions: {e}")
        return 0


def test_redis_connection() -> bool:
    """
    Test Redis connection.
    
    Returns:
        bool: True if Redis is reachable
        
    Example:
        >>> if test_redis_connection():
        ...     print("Redis is working!")
    """
    try:
        client = get_redis_client()
        response = client.ping()
        
        if response:
            logger.info("✅ Redis connection successful")
            return True
        else:
            logger.error("❌ Redis ping failed")
            return False
        
    except redis.ConnectionError as e:
        logger.error(f"❌ Cannot connect to Redis: {e}")
        return False
    
    except Exception as e:
        logger.error(f"❌ Unexpected error testing Redis: {e}")
        return False


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Main functions
    "store_anonymization_map",
    "get_anonymization_map",
    "delete_anonymization_map",
    
    # Session utilities
    "session_exists",
    "get_session_ttl",
    "extend_session_ttl",
    
    # Management
    "get_all_sessions",
    "clear_all_sessions",
    
    # Connection
    "get_redis_client",
    "get_session_manager",
    "test_redis_connection",
]