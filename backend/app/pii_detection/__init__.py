"""
PII Detection Module for Shield AI

This module provides comprehensive Personally Identifiable Information (PII)
detection capabilities for Spanish text, combining Named Entity Recognition (NER)
and regex-based pattern matching.

Main Functions:
    detect_pii: Primary PII detection function
    detect_pii_simple: Simplified detection interface
    get_supported_entity_types: Get available entity types
    
Author: Shield AI Team
Date: 2025-09-18
"""

from .detector import (
    detect_pii,
    detect_pii_simple,
    get_supported_entity_types,
    validate_detection_config,
    get_detection_stats,
    PiiDetectionResult
)

from .pipeline import (
    DetectedEntity,
    PiiDetectionPipeline,
    get_pii_pipeline
)

from .regex_patterns import (
    PiiMatch,
    SpanishPiiRegexPatterns,
    spanish_pii_regex
)

__all__ = [
    # Main detection functions
    'detect_pii',
    'detect_pii_simple',
    'get_supported_entity_types',
    'validate_detection_config',
    'get_detection_stats',
    
    # Result classes
    'PiiDetectionResult',
    'DetectedEntity',
    'PiiMatch',
    
    # Pipeline components
    'PiiDetectionPipeline',
    'get_pii_pipeline',
    'SpanishPiiRegexPatterns',
    'spanish_pii_regex'
]

# Module metadata
__version__ = "1.0.0"
__author__ = "Shield AI Team"
__description__ = "Spanish PII Detection System"