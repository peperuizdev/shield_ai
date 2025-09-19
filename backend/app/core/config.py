"""
Configuration module for Shield AI application.

Handles environment variables, application settings, and configuration
for Redis, FastAPI, and other core services.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses pydantic_settings for validation and type conversion.
    Settings can be overridden via environment variables with SHIELD_AI_ prefix.
    """
    
    # Application settings
    app_name: str = Field(default="Shield AI", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/production)")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="API auto-reload in development")
    
    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_decode_responses: bool = Field(default=True, description="Decode Redis responses as strings")
    redis_socket_timeout: int = Field(default=5, description="Redis socket timeout in seconds")
    redis_connection_pool_max_connections: int = Field(default=20, description="Max Redis connections")
    
    # Session settings
    session_ttl: int = Field(default=3600, description="Session TTL in seconds (1 hour)")
    session_cleanup_interval: int = Field(default=300, description="Session cleanup interval in seconds")
    session_key_prefix: str = Field(default="anon_map", description="Redis key prefix for sessions")
    
    # Security settings
    allowed_hosts: list[str] = Field(default=["*"], description="Allowed hosts for CORS")
    allowed_origins: list[str] = Field(default=["*"], description="Allowed origins for CORS")
    allowed_methods: list[str] = Field(default=["*"], description="Allowed methods for CORS")
    allowed_headers: list[str] = Field(default=["*"], description="Allowed headers for CORS")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format"
    )
    
    # External API settings (for LLM integration)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    
    # Performance settings
    max_request_size: int = Field(default=1048576, description="Max request size in bytes (1MB)")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    worker_connections: int = Field(default=1000, description="Worker connections for Uvicorn")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "SHIELD_AI_"
        case_sensitive = False
        

class DevelopmentSettings(Settings):
    """Development environment specific settings."""
    debug: bool = True
    api_reload: bool = True
    log_level: str = "DEBUG"
    environment: str = "development"


class ProductionSettings(Settings):
    """Production environment specific settings."""
    debug: bool = False
    api_reload: bool = False
    log_level: str = "WARNING"
    environment: str = "production"
    allowed_hosts: list[str] = ["shield-ai.com", "api.shield-ai.com"]
    allowed_origins: list[str] = ["https://shield-ai.com", "https://app.shield-ai.com"]


class TestSettings(Settings):
    """Test environment specific settings."""
    debug: bool = True
    environment: str = "test"
    redis_db: int = 15  # Use different DB for tests
    session_ttl: int = 60  # Shorter TTL for tests
    log_level: str = "CRITICAL"  # Reduce test noise


def get_settings() -> Settings:
    """
    Get application settings based on environment.
    
    Returns:
        Settings: Configured settings instance based on environment
    """
    env = os.getenv("SHIELD_AI_ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


# Convenience functions for common configurations
def get_redis_url() -> str:
    """
    Get Redis connection URL.
    
    Returns:
        str: Redis connection URL
    """
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


def get_redis_config() -> dict:
    """
    Get Redis configuration dictionary.
    
    Returns:
        dict: Redis configuration for redis.Redis()
    """
    config = {
        "host": settings.redis_host,
        "port": settings.redis_port,
        "db": settings.redis_db,
        "decode_responses": settings.redis_decode_responses,
        "socket_timeout": settings.redis_socket_timeout,
        "socket_connect_timeout": settings.redis_socket_timeout,
    }
    
    if settings.redis_password:
        config["password"] = settings.redis_password
    
    return config


def get_cors_config() -> dict:
    """
    Get CORS configuration dictionary.
    
    Returns:
        dict: CORS configuration for FastAPI
    """
    return {
        "allow_origins": settings.allowed_origins,
        "allow_credentials": True,
        "allow_methods": settings.allowed_methods,
        "allow_headers": settings.allowed_headers,
    }


def is_development() -> bool:
    """Check if running in development mode."""
    return settings.environment == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return settings.environment == "production"


def is_testing() -> bool:
    """Check if running in test mode."""
    return settings.environment == "test"


# Export commonly used settings
__all__ = [
    "settings",
    "get_settings", 
    "get_redis_url",
    "get_redis_config",
    "get_cors_config",
    "is_development",
    "is_production", 
    "is_testing",
    "Settings",
    "DevelopmentSettings",
    "ProductionSettings", 
    "TestSettings"
]