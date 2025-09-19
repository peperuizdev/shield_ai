"""
Response models for Shield AI API endpoints.

Pydantic models for response serialization and documentation
across all API endpoints.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """
    Base response model with common fields.
    """
    success: bool = Field(
        ...,
        description="Whether the operation was successful",
        example=True
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp",
        example="2025-09-19T10:30:00"
    )
    message: Optional[str] = Field(
        None,
        description="Optional message or description",
        example="Operation completed successfully"
    )


class ErrorResponse(BaseResponse):
    """
    Error response model for API errors.
    """
    success: bool = Field(
        default=False,
        description="Always false for error responses"
    )
    error_code: Optional[str] = Field(
        None,
        description="Specific error code",
        example="SESSION_NOT_FOUND"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details",
        example={"session_id": "invalid_session"}
    )
    path: Optional[str] = Field(
        None,
        description="API path where error occurred",
        example="/api/sessions/invalid_session"
    )


class HealthCheckResponse(BaseResponse):
    """
    Response model for health check endpoints.
    """
    status: str = Field(
        ...,
        description="Overall system health status",
        example="healthy"
    )
    services: Dict[str, str] = Field(
        ...,
        description="Status of individual services",
        example={
            "redis": "healthy",
            "fastapi": "healthy",
            "pii_detection": "healthy"
        }
    )
    version: str = Field(
        ...,
        description="Application version",
        example="1.0.0"
    )
    environment: str = Field(
        ...,
        description="Environment name",
        example="development"
    )
    uptime: Optional[float] = Field(
        None,
        description="System uptime in seconds",
        example=3600.5
    )
    detailed_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed health information if requested",
        example={
            "redis_info": {"version": "7.0", "memory_usage": "2.5MB"},
            "system_info": {"cpu_usage": "15%", "memory_usage": "512MB"}
        }
    )


class SessionStatusResponse(BaseResponse):
    """
    Response model for session status endpoints.
    """
    session_id: str = Field(
        ...,
        description="Session identifier",
        example="session_123"
    )
    exists: bool = Field(
        ...,
        description="Whether the session exists",
        example=True
    )
    status: str = Field(
        ...,
        description="Session status",
        example="active"
    )
    ttl_seconds: int = Field(
        ...,
        description="Time to live in seconds",
        example=1800
    )
    expires_in: Optional[str] = Field(
        None,
        description="Human-readable expiration time",
        example="30 minutes 0 seconds"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Exact expiration timestamp",
        example="2025-09-19T11:00:00"
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Session creation timestamp",
        example="2025-09-19T10:00:00"
    )
    map_size: Optional[int] = Field(
        None,
        description="Size of anonymization map",
        example=10
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional session metadata",
        example={"created_by": "api", "last_accessed": "2025-09-19T10:30:00"}
    )


class SessionCreateResponse(BaseResponse):
    """
    Response model for session creation endpoints.
    """
    session_id: str = Field(
        ...,
        description="Created session identifier",
        example="session_123"
    )
    ttl_seconds: int = Field(
        ...,
        description="Session TTL in seconds",
        example=3600
    )
    expires_at: datetime = Field(
        ...,
        description="Session expiration timestamp",
        example="2025-09-19T11:30:00"
    )
    map_size: int = Field(
        ...,
        description="Number of entries in anonymization map",
        example=5
    )


class SessionDeleteResponse(BaseResponse):
    """
    Response model for session deletion endpoints.
    """
    session_id: str = Field(
        ...,
        description="Deleted session identifier",
        example="session_123"
    )
    session_deleted: bool = Field(
        ...,
        description="Whether session data was deleted",
        example=True
    )
    metadata_deleted: bool = Field(
        ...,
        description="Whether session metadata was deleted",
        example=True
    )


class SessionListResponse(BaseResponse):
    """
    Response model for listing active sessions.
    """
    total_sessions: int = Field(
        ...,
        description="Total number of active sessions",
        example=5
    )
    sessions: List[SessionStatusResponse] = Field(
        ...,
        description="List of active sessions with their status",
        example=[]
    )


class DeAnonymizationResponse(BaseResponse):
    """
    Response model for deanonymization endpoints.
    """
    session_id: str = Field(
        ...,
        description="Session identifier used",
        example="session_123"
    )
    original_response: str = Field(
        ...,
        description="Original anonymized text",
        example="Hola María González, tu email es maria@example.com"
    )
    deanonymized_response: str = Field(
        ...,
        description="Deanonymized text with original data restored",
        example="Hola Juan Pérez, tu email es juan@example.com"
    )
    replacements_made: int = Field(
        ...,
        description="Number of replacements performed",
        example=2
    )
    processing_time: Optional[float] = Field(
        None,
        description="Processing time in seconds",
        example=0.125
    )


class PiiDetectionResponse(BaseResponse):
    """
    Response model for PII detection endpoints.
    """
    text_length: int = Field(
        ...,
        description="Length of analyzed text",
        example=45
    )
    total_entities: int = Field(
        ...,
        description="Total number of PII entities found",
        example=3
    )
    processing_time: float = Field(
        ...,
        description="Processing time in seconds",
        example=0.087
    )
    entities: List[Dict[str, Any]] = Field(
        ...,
        description="List of detected PII entities",
        example=[
            {
                "entity_type": "DNI",
                "value": "12345678A",
                "start": 10,
                "end": 19,
                "confidence": 0.95,
                "detection_method": "REGEX"
            }
        ]
    )
    detection_summary: Dict[str, int] = Field(
        ...,
        description="Summary of entities by type",
        example={"DNI": 1, "EMAIL": 1, "PERSON": 1}
    )
    methods_used: List[str] = Field(
        ...,
        description="Detection methods used",
        example=["NER", "REGEX"]
    )


class AnonymizationResponse(BaseResponse):
    """
    Response model for anonymization endpoints.
    """
    session_id: Optional[str] = Field(
        None,
        description="Session ID if map was stored",
        example="session_123"
    )
    original_text: str = Field(
        ...,
        description="Original input text",
        example="Mi nombre es Juan Pérez"
    )
    anonymized_text: str = Field(
        ...,
        description="Text with PII replaced",
        example="Mi nombre es María González"
    )
    entities_detected: int = Field(
        ...,
        description="Number of PII entities detected",
        example=1
    )
    entities_replaced: int = Field(
        ...,
        description="Number of entities replaced",
        example=1
    )
    anonymization_map: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of original to anonymized data",
        example={"Juan Pérez": "María González"}
    )
    processing_time: float = Field(
        ...,
        description="Processing time in seconds",
        example=0.156
    )


class BulkProcessingResponse(BaseResponse):
    """
    Response model for bulk processing endpoints.
    """
    session_id: str = Field(
        ...,
        description="Batch session identifier",
        example="batch_session_001"
    )
    total_texts: int = Field(
        ...,
        description="Total number of texts processed",
        example=10
    )
    successful_processes: int = Field(
        ...,
        description="Number of successfully processed texts",
        example=9
    )
    failed_processes: int = Field(
        ...,
        description="Number of failed processes",
        example=1
    )
    results: List[Union[PiiDetectionResponse, AnonymizationResponse, DeAnonymizationResponse]] = Field(
        ...,
        description="Results for each processed text",
        example=[]
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Errors encountered during processing",
        example=[{"index": 5, "error": "Text too long", "text_preview": "Lorem ipsum..."}]
    )
    total_processing_time: float = Field(
        ...,
        description="Total processing time in seconds",
        example=2.345
    )


class SystemStatsResponse(BaseResponse):
    """
    Response model for system statistics endpoints.
    """
    redis_stats: Dict[str, Any] = Field(
        ...,
        description="Redis statistics and metrics",
        example={
            "connected_clients": 5,
            "used_memory_human": "2.5MB",
            "total_commands_processed": 1234
        }
    )
    session_stats: Dict[str, Any] = Field(
        ...,
        description="Session management statistics",
        example={
            "active_sessions": 10,
            "total_sessions_created": 50,
            "average_session_duration": 1800
        }
    )
    api_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="API usage statistics",
        example={
            "total_requests": 1000,
            "requests_per_minute": 15.5,
            "average_response_time": 0.125
        }
    )


class ApplicationInfoResponse(BaseResponse):
    """
    Response model for application information endpoints.
    """
    name: str = Field(
        ...,
        description="Application name",
        example="Shield AI"
    )
    version: str = Field(
        ...,
        description="Application version",
        example="1.0.0"
    )
    description: str = Field(
        ...,
        description="Application description",
        example="Intelligent Data Anonymization System"
    )
    environment: str = Field(
        ...,
        description="Current environment",
        example="development"
    )
    features: Dict[str, bool] = Field(
        ...,
        description="Available features",
        example={
            "pii_detection": True,
            "streaming": True,
            "bulk_processing": True
        }
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="Non-sensitive configuration details",
        example={
            "redis_host": "localhost",
            "session_ttl": 3600,
            "max_request_size": 1048576
        }
    )


# Export all response models
__all__ = [
    "BaseResponse",
    "ErrorResponse", 
    "HealthCheckResponse",
    "SessionStatusResponse",
    "SessionCreateResponse",
    "SessionDeleteResponse", 
    "SessionListResponse",
    "DeAnonymizationResponse",
    "PiiDetectionResponse",
    "AnonymizationResponse",
    "BulkProcessingResponse",
    "SystemStatsResponse",
    "ApplicationInfoResponse"
]