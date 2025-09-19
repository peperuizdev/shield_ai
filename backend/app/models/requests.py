"""
Request models for Shield AI API endpoints.

Pydantic models for request validation and serialization
across all API endpoints.

Author: Shield AI Team - Backend Developer
Date: 2025-09-19
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import re


class DeAnonymizationRequest(BaseModel):
    """
    Request model for deanonymization endpoints.
    
    Used by deanonymization functionality to process
    anonymized text and restore original data.
    """
    session_id: str = Field(
        ...,
        description="Session identifier for anonymization map",
        min_length=1,
        max_length=128,
        example="session_123"
    )
    model_response: str = Field(
        ...,
        description="Anonymized response from LLM to be deanonymized",
        min_length=1,
        max_length=50000,
        example="Hola María González, tu email es maria@example.com"
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Session ID must contain only alphanumeric characters, underscores, and hyphens')
        return v


class SessionCreateRequest(BaseModel):
    """
    Request model for creating a new session.
    """
    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=1,
        max_length=128,
        example="user_session_001"
    )
    anonymization_map: Dict[str, str] = Field(
        ...,
        description="Mapping of original data to anonymized data",
        example={
            "Juan Pérez": "María González",
            "juan@email.com": "maria@example.com"
        }
    )
    ttl: Optional[int] = Field(
        None,
        description="Time to live in seconds (default: 3600)",
        ge=60,
        le=86400,
        example=3600
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Session ID must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @validator('anonymization_map')
    def validate_anonymization_map(cls, v):
        """Validate anonymization map."""
        if not v:
            raise ValueError('Anonymization map cannot be empty')
        
        if len(v) > 1000:
            raise ValueError('Anonymization map cannot exceed 1000 entries')
        
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError('All keys and values in anonymization map must be strings')
            
            if len(key) > 500 or len(value) > 500:
                raise ValueError('Keys and values in anonymization map cannot exceed 500 characters')
        
        return v


class SessionUpdateRequest(BaseModel):
    """
    Request model for updating session TTL or metadata.
    """
    ttl: Optional[int] = Field(
        None,
        description="New TTL in seconds",
        ge=60,
        le=86400,
        example=7200
    )
    extend_by: Optional[int] = Field(
        None,
        description="Extend current TTL by seconds",
        ge=60,
        le=86400,
        example=3600
    )
    
    @validator('ttl', 'extend_by')
    def validate_ttl_values(cls, v):
        """Validate TTL values."""
        if v is not None and (v < 60 or v > 86400):
            raise ValueError('TTL must be between 60 seconds and 24 hours')
        return v


class PiiDetectionRequest(BaseModel):
    """
    Request model for PII detection endpoints.
    """
    text: str = Field(
        ...,
        description="Text to analyze for PII",
        min_length=1,
        max_length=50000,
        example="Mi DNI es 12345678A y mi email es juan@example.com"
    )
    confidence_threshold: Optional[float] = Field(
        0.5,
        description="Minimum confidence threshold for detections",
        ge=0.0,
        le=1.0,
        example=0.8
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description="Specific entity types to detect (None = all)",
        example=["DNI", "EMAIL", "PHONE"]
    )
    enable_ner: Optional[bool] = Field(
        True,
        description="Enable Named Entity Recognition",
        example=True
    )
    enable_regex: Optional[bool] = Field(
        True,
        description="Enable regex pattern matching",
        example=True
    )
    
    @validator('entity_types')
    def validate_entity_types(cls, v):
        """Validate entity types."""
        if v is not None:
            valid_types = {
                'DNI', 'NIE', 'EMAIL', 'MOBILE_PHONE', 'LANDLINE_PHONE',
                'POSTAL_CODE', 'ADDRESS', 'CREDIT_CARD', 'IBAN', 'CCC',
                'PERSON', 'ORGANIZATION', 'LOCATION', 'MISCELLANEOUS'
            }
            
            invalid_types = set(v) - valid_types
            if invalid_types:
                raise ValueError(f'Invalid entity types: {invalid_types}')
        
        return v


class AnonymizationRequest(BaseModel):
    """
    Request model for anonymization endpoints.
    """
    text: str = Field(
        ...,
        description="Text to anonymize",
        min_length=1,
        max_length=50000,
        example="Mi nombre es Juan Pérez y mi email es juan@example.com"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID to store anonymization map",
        min_length=1,
        max_length=128,
        example="session_001"
    )
    detection_config: Optional[PiiDetectionRequest] = Field(
        None,
        description="PII detection configuration"
    )
    replacement_strategy: Optional[str] = Field(
        "synthetic",
        description="Strategy for replacing PII",
        regex=r'^(synthetic|placeholder|custom)$',
        example="synthetic"
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if v is not None and not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Session ID must contain only alphanumeric characters, underscores, and hyphens')
        return v


class BulkProcessingRequest(BaseModel):
    """
    Request model for bulk processing operations.
    """
    texts: List[str] = Field(
        ...,
        description="List of texts to process",
        min_items=1,
        max_items=100,
        example=["Text 1", "Text 2", "Text 3"]
    )
    session_id: str = Field(
        ...,
        description="Session identifier for batch processing",
        min_length=1,
        max_length=128,
        example="batch_session_001"
    )
    processing_type: str = Field(
        ...,
        description="Type of processing to perform",
        regex=r'^(detect|anonymize|deanonymize)$',
        example="detect"
    )
    
    @validator('texts')
    def validate_texts(cls, v):
        """Validate text list."""
        for i, text in enumerate(v):
            if not isinstance(text, str):
                raise ValueError(f'Text at index {i} must be a string')
            if len(text) > 10000:
                raise ValueError(f'Text at index {i} exceeds maximum length of 10000 characters')
            if not text.strip():
                raise ValueError(f'Text at index {i} cannot be empty or whitespace only')
        return v


class HealthCheckRequest(BaseModel):
    """
    Request model for health check with optional detailed checks.
    """
    include_detailed: Optional[bool] = Field(
        False,
        description="Include detailed health information",
        example=True
    )
    check_services: Optional[List[str]] = Field(
        None,
        description="Specific services to check",
        example=["redis", "pii_detection"]
    )


# Export all request models
__all__ = [
    "DeAnonymizationRequest",
    "SessionCreateRequest", 
    "SessionUpdateRequest",
    "PiiDetectionRequest",
    "AnonymizationRequest",
    "BulkProcessingRequest",
    "HealthCheckRequest"
]