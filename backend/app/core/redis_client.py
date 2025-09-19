"""
Redis client configuration and connection management for Shield AI.

Provides Redis connection handling, health checks, and connection pooling
for session management and caching.

Author: Shield AI Team - Backend Developer
Date: 2025-09-19
"""

import redis
import logging
from typing import Optional, Dict, Any
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from .config import settings, get_redis_config


logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper with connection management and health checks.
    
    Provides a robust Redis connection with automatic reconnection,
    connection pooling, and health monitoring.
    """
    
    def __init__(self):
        """Initialize Redis client with connection pool."""
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._is_connected = False
        self._connect()
    
    def _connect(self) -> None:
        """
        Create Redis connection with connection pool.
        
        Raises:
            ConnectionError: If unable to connect to Redis
        """
        try:
            # Get Redis configuration
            redis_config = get_redis_config()
            
            # Create connection pool
            self._connection_pool = ConnectionPool(
                max_connections=settings.redis_connection_pool_max_connections,
                **redis_config
            )
            
            # Create Redis client with connection pool
            self._client = redis.Redis(
                connection_pool=self._connection_pool,
                **redis_config
            )
            
            # Test connection
            self._client.ping()
            self._is_connected = True
            
            logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
            
        except Exception as e:
            self._is_connected = False
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise ConnectionError(f"Cannot connect to Redis: {str(e)}")
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client instance.
        
        Returns:
            redis.Redis: Redis client instance
            
        Raises:
            ConnectionError: If client is not connected
        """
        if not self._is_connected or self._client is None:
            logger.warning("Redis client not connected, attempting to reconnect...")
            self._connect()
        
        return self._client
    
    def is_connected(self) -> bool:
        """
        Check if Redis client is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self._client:
            return False
            
        try:
            self._client.ping()
            self._is_connected = True
            return True
        except (ConnectionError, TimeoutError, RedisError):
            self._is_connected = False
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Dict[str, Any]: Health check results with metrics
        """
        health_info = {
            "status": "unhealthy",
            "connected": False,
            "redis_info": {},
            "connection_pool_info": {},
            "error": None
        }
        
        try:
            if not self._client:
                raise ConnectionError("Redis client not initialized")
            
            # Test basic connectivity
            ping_result = self._client.ping()
            if not ping_result:
                raise ConnectionError("Redis ping failed")
            
            # Get Redis server info
            redis_info = self._client.info()
            health_info["redis_info"] = {
                "version": redis_info.get("redis_version", "unknown"),
                "uptime_seconds": redis_info.get("uptime_in_seconds", 0),
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                "total_commands_processed": redis_info.get("total_commands_processed", 0)
            }
            
            # Get connection pool info
            if self._connection_pool:
                pool_info = {
                    "max_connections": self._connection_pool.max_connections,
                    "created_connections": len(self._connection_pool._created_connections),
                    "available_connections": len(self._connection_pool._available_connections),
                    "in_use_connections": len(self._connection_pool._in_use_connections)
                }
                health_info["connection_pool_info"] = pool_info
            
            # Test basic operations
            test_key = "health_check_test"
            self._client.set(test_key, "test_value", ex=5)
            test_value = self._client.get(test_key)
            self._client.delete(test_key)
            
            if test_value != "test_value":
                raise RedisError("Redis set/get test failed")
            
            health_info["status"] = "healthy"
            health_info["connected"] = True
            self._is_connected = True
            
        except Exception as e:
            health_info["error"] = str(e)
            health_info["connected"] = False
            self._is_connected = False
            logger.error(f"Redis health check failed: {str(e)}")
        
        return health_info
    
    def disconnect(self) -> None:
        """
        Disconnect from Redis and close connection pool.
        """
        try:
            if self._connection_pool:
                self._connection_pool.disconnect()
                logger.info("Redis connection pool disconnected")
            
            self._client = None
            self._connection_pool = None
            self._is_connected = False
            
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics and metrics.
        
        Returns:
            Dict[str, Any]: Redis statistics
        """
        if not self.is_connected():
            return {"error": "Not connected to Redis"}
        
        try:
            info = self._client.info()
            stats = {
                "server": {
                    "redis_version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "arch_bits": info.get("arch_bits")
                },
                "clients": {
                    "connected_clients": info.get("connected_clients"),
                    "blocked_clients": info.get("blocked_clients")
                },
                "memory": {
                    "used_memory": info.get("used_memory"),
                    "used_memory_human": info.get("used_memory_human"),
                    "used_memory_peak_human": info.get("used_memory_peak_human")
                },
                "stats": {
                    "total_connections_received": info.get("total_connections_received"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                }
            }
            
            # Add keyspace info if available
            keyspace_info = {}
            for key, value in info.items():
                if key.startswith("db"):
                    keyspace_info[key] = value
            
            if keyspace_info:
                stats["keyspace"] = keyspace_info
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            return {"error": str(e)}
    
    def __del__(self):
        """Cleanup on object destruction."""
        try:
            self.disconnect()
        except Exception:
            pass  # Ignore errors during cleanup


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> redis.Redis:
    """
    Get global Redis client instance.
    
    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
    
    return _redis_client.get_client()


def get_redis_health() -> Dict[str, Any]:
    """
    Get Redis health check information.
    
    Returns:
        Dict[str, Any]: Health check results
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
    
    return _redis_client.health_check()


def get_redis_stats() -> Dict[str, Any]:
    """
    Get Redis statistics.
    
    Returns:
        Dict[str, Any]: Redis statistics
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
    
    return _redis_client.get_stats()


def is_redis_connected() -> bool:
    """
    Check if Redis is connected.
    
    Returns:
        bool: True if connected, False otherwise
    """
    global _redis_client
    
    if _redis_client is None:
        return False
    
    return _redis_client.is_connected()


# Export main functions
__all__ = [
    "RedisClient",
    "get_redis_client", 
    "get_redis_health",
    "get_redis_stats",
    "is_redis_connected"
]