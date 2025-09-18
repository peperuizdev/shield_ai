"""
Main PII Detection Interface

This module provides the main interface for PII detection in Spanish text.
It serves as the entry point for the Shield AI anonymization system.

Author: Shield AI Team
Date: 2025-09-18
"""

import logging
import time
from typing import List, Dict, Optional, Set, Any
from dataclasses import asdict

from .pipeline import get_pii_pipeline, DetectedEntity
from .regex_patterns import spanish_pii_regex


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PiiDetectionResult:
    """
    Container for PII detection results with metadata and statistics.
    
    Attributes:
        entities (List[DetectedEntity]): Detected PII entities
        text_length (int): Length of analyzed text
        processing_time (float): Time taken for detection in seconds
        detection_summary (Dict[str, int]): Count of entities by type
        total_entities (int): Total number of entities found
        methods_used (Set[str]): Detection methods that were used
    """
    
    def __init__(self, entities: List[DetectedEntity], text_length: int, 
                 processing_time: float):
        self.entities = entities
        self.text_length = text_length
        self.processing_time = processing_time
        self.detection_summary = self._calculate_summary()
        self.total_entities = len(entities)
        self.methods_used = self._get_methods_used()
    
    def _calculate_summary(self) -> Dict[str, int]:
        """Calculate summary of detected entities by type."""
        summary = {}
        for entity in self.entities:
            entity_type = entity.entity_type
            summary[entity_type] = summary.get(entity_type, 0) + 1
        return summary
    
    def _get_methods_used(self) -> Set[str]:
        """Get set of detection methods that were used."""
        methods = set()
        for entity in self.entities:
            methods.add(entity.detection_method)
        return methods
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format for JSON serialization."""
        return {
            'entities': [asdict(entity) for entity in self.entities],
            'text_length': self.text_length,
            'processing_time': self.processing_time,
            'detection_summary': self.detection_summary,
            'total_entities': self.total_entities,
            'methods_used': list(self.methods_used)
        }
    
    def get_sensitive_spans(self) -> List[tuple]:
        """
        Get list of (start, end) tuples for all sensitive spans.
        Useful for text masking operations.
        
        Returns:
            List[tuple]: List of (start, end) position tuples
        """
        return [(entity.start, entity.end) for entity in self.entities]
    
    def filter_by_confidence(self, min_confidence: float) -> 'PiiDetectionResult':
        """
        Create new result with entities filtered by confidence threshold.
        
        Args:
            min_confidence (float): Minimum confidence threshold
            
        Returns:
            PiiDetectionResult: Filtered result
        """
        filtered_entities = [
            entity for entity in self.entities 
            if entity.confidence >= min_confidence
        ]
        
        return PiiDetectionResult(
            entities=filtered_entities,
            text_length=self.text_length,
            processing_time=self.processing_time
        )


def detect_pii(text: str, 
               confidence_threshold: float = 0.5,
               entity_types: Optional[Set[str]] = None,
               enable_ner: bool = True,
               enable_regex: bool = True) -> PiiDetectionResult:
    """
    Main function to detect PII entities in Spanish text.
    
    This is the primary interface for PII detection in the Shield AI system.
    It combines NER and regex-based detection methods to provide comprehensive
    PII identification.
    
    Args:
        text (str): Input text to analyze for PII
        confidence_threshold (float): Minimum confidence score for detections (0.0-1.0)
        entity_types (Optional[Set[str]]): Specific entity types to detect (None = all)
        enable_ner (bool): Enable Named Entity Recognition detection
        enable_regex (bool): Enable regex pattern detection
        
    Returns:
        PiiDetectionResult: Comprehensive detection results with metadata
        
    Raises:
        ValueError: If invalid parameters are provided
        RuntimeError: If detection pipeline fails
        
    Example:
        >>> result = detect_pii("Mi DNI es 12345678A y mi email es juan@email.com")
        >>> print(f"Found {result.total_entities} PII entities")
        >>> for entity in result.entities:
        ...     print(f"{entity.entity_type}: {entity.value}")
    """
    # Input validation
    if not isinstance(text, str):
        raise ValueError("Input text must be a string")
    
    if not text.strip():
        logger.warning("Empty or whitespace-only text provided")
        return PiiDetectionResult(entities=[], text_length=0, processing_time=0.0)
    
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")
    
    if not enable_ner and not enable_regex:
        raise ValueError("At least one detection method must be enabled")
    
    # Log detection request
    logger.info(f"Starting PII detection on text of length {len(text)}")
    logger.debug(f"Configuration: NER={enable_ner}, Regex={enable_regex}, "
                f"Confidence={confidence_threshold}")
    
    start_time = time.time()
    
    try:
        # Get the detection pipeline
        pipeline = get_pii_pipeline()
        
        # Configure pipeline based on parameters
        pipeline.use_ner = enable_ner
        pipeline.use_regex = enable_regex
        
        # Perform detection
        entities = pipeline.detect_pii(text, merge_overlapping=True)
        
        # Apply confidence filtering
        if confidence_threshold > 0.0:
            entities = pipeline.filter_by_confidence(entities, confidence_threshold)
        
        # Apply entity type filtering
        if entity_types is not None:
            entities = pipeline.filter_by_types(entities, entity_types)
        
        processing_time = time.time() - start_time
        
        # Create result object
        result = PiiDetectionResult(
            entities=entities,
            text_length=len(text),
            processing_time=processing_time
        )
        
        # Log results
        logger.info(f"Detection completed in {processing_time:.3f}s. "
                   f"Found {result.total_entities} entities")
        logger.debug(f"Entity summary: {result.detection_summary}")
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"PII detection failed after {processing_time:.3f}s: {str(e)}")
        raise RuntimeError(f"PII detection failed: {str(e)}") from e


def detect_pii_simple(text: str) -> List[Dict[str, Any]]:
    """
    Simplified PII detection function that returns basic results.
    
    This is a convenience function for quick PII detection without
    advanced configuration options.
    
    Args:
        text (str): Input text to analyze
        
    Returns:
        List[Dict[str, Any]]: List of detected entities as dictionaries
    """
    result = detect_pii(text)
    return [asdict(entity) for entity in result.entities]


def get_supported_entity_types() -> Dict[str, str]:
    """
    Get dictionary of all supported PII entity types with descriptions.
    
    Returns:
        Dict[str, str]: Mapping of entity type to description
    """
    return {
        'DNI': 'Spanish National Identity Document',
        'NIE': 'Spanish Foreigner Identity Number',
        'PERSON': 'Person names detected by NER',
        'EMAIL': 'Email addresses',
        'MOBILE_PHONE': 'Spanish mobile phone numbers',
        'LANDLINE_PHONE': 'Spanish landline phone numbers',
        'POSTAL_CODE': 'Spanish postal codes',
        'ADDRESS': 'Physical addresses',
        'CREDIT_CARD': 'Credit card numbers',
        'IBAN': 'Spanish IBAN bank account numbers',
        'CCC': 'Spanish old format bank account numbers',
        'ORGANIZATION': 'Organization names detected by NER',
        'LOCATION': 'Location names detected by NER',
        'MISCELLANEOUS': 'Other entities detected by NER'
    }


def validate_detection_config(enable_ner: bool = True, 
                            enable_regex: bool = True,
                            confidence_threshold: float = 0.5) -> bool:
    """
    Validate detection configuration parameters.
    
    Args:
        enable_ner (bool): NER detection enabled flag
        enable_regex (bool): Regex detection enabled flag
        confidence_threshold (float): Confidence threshold value
        
    Returns:
        bool: True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    if not enable_ner and not enable_regex:
        raise ValueError("At least one detection method must be enabled")
    
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")
    
    return True


def get_detection_stats() -> Dict[str, Any]:
    """
    Get statistics about the detection system capabilities.
    
    Returns:
        Dict[str, Any]: System statistics and capabilities
    """
    try:
        pipeline = get_pii_pipeline()
        
        stats = {
            'supported_entity_types': len(get_supported_entity_types()),
            'ner_available': pipeline.use_ner and pipeline.ner_model is not None,
            'regex_patterns_count': len([
                attr for attr in dir(spanish_pii_regex) 
                if attr.endswith('_pattern')
            ]),
            'system_ready': True
        }
        
        if stats['ner_available']:
            stats['ner_model_info'] = pipeline.ner_model.get_model_info()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get detection stats: {str(e)}")
        return {
            'system_ready': False,
            'error': str(e)
        }