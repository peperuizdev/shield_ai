"""
Unified PII Detection Pipeline

This module combines NER (Named Entity Recognition) and regex-based detection
to provide comprehensive PII detection for Spanish text. The pipeline merges
results from both approaches to maximize detection accuracy.

Author: Shield AI Team
Date: 2025-09-18
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from .regex_patterns import spanish_pii_regex, PiiMatch
from .ner_model import get_ner_model, NerEntity


@dataclass
class DetectedEntity:
    """
    Unified representation of a detected PII entity.
    
    Attributes:
        entity_type (str): Type of PII (PERSON, DNI, EMAIL, etc.)
        value (str): The actual detected value
        start (int): Start position in original text
        end (int): End position in original text
        confidence (float): Detection confidence (0.0 to 1.0)
        detection_method (str): Method used for detection ('NER', 'REGEX', 'COMBINED')
        metadata (Dict): Additional information about the detection
    """
    entity_type: str
    value: str
    start: int
    end: int
    confidence: float
    detection_method: str
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PiiDetectionPipeline:
    """
    Unified pipeline that combines NER and regex-based PII detection.
    
    This class orchestrates both detection methods and provides intelligent
    merging of results to minimize false positives and maximize coverage.
    """
    
    def __init__(self, use_ner: bool = True, use_regex: bool = True):
        """
        Initialize the PII detection pipeline.
        
        Args:
            use_ner (bool): Enable NER-based detection
            use_regex (bool): Enable regex-based detection
        """
        self.use_ner = use_ner
        self.use_regex = use_regex
        self.ner_model = None
        
        # Priority mapping for entity types (higher = more specific/reliable)
        self.entity_priority = {
            'DNI': 10,
            'NIE': 10,
            'IBAN': 9,
            'CREDIT_CARD': 9,
            'EMAIL': 8,
            'MOBILE_PHONE': 7,
            'LANDLINE_PHONE': 7,
            'POSTAL_CODE': 6,
            'CCC': 6,
            'ADDRESS': 5,
            'PERSON': 4,
            'ORGANIZATION': 3,
            'LOCATION': 3,
            'MISCELLANEOUS': 1
        }
        
        if self.use_ner:
            try:
                self.ner_model = get_ner_model()
                logging.info("NER model loaded successfully")
            except Exception as e:
                logging.warning(f"Failed to load NER model: {e}. Continuing with regex only.")
                self.use_ner = False
    
    def detect_pii(self, text: str, merge_overlapping: bool = True) -> List[DetectedEntity]:
        """
        Detect PII in text using both NER and regex methods.
        
        Args:
            text (str): Input text to analyze
            merge_overlapping (bool): Whether to merge overlapping detections
            
        Returns:
            List[DetectedEntity]: List of detected PII entities
        """
        if not text or not text.strip():
            return []
        
        all_detections = []
        
        # Run regex-based detection
        if self.use_regex:
            regex_detections = self._run_regex_detection(text)
            all_detections.extend(regex_detections)
            logging.debug(f"Regex detected {len(regex_detections)} entities")
        
        # Run NER-based detection
        if self.use_ner and self.ner_model:
            ner_detections = self._run_ner_detection(text)
            all_detections.extend(ner_detections)
            logging.debug(f"NER detected {len(ner_detections)} entities")
        
        # Merge overlapping detections if requested
        if merge_overlapping:
            all_detections = self._merge_overlapping_detections(all_detections)
        
        # Sort by start position
        all_detections.sort(key=lambda x: x.start)
        
        logging.info(f"Total PII entities detected: {len(all_detections)}")
        return all_detections
    
    def _run_regex_detection(self, text: str) -> List[DetectedEntity]:
        """
        Run regex-based PII detection.
        
        Args:
            text (str): Input text to analyze
            
        Returns:
            List[DetectedEntity]: Regex-detected entities
        """
        regex_matches = spanish_pii_regex.detect_pii_patterns(text)
        
        detections = []
        for match in regex_matches:
            detection = DetectedEntity(
                entity_type=match.pii_type,
                value=match.value,
                start=match.start,
                end=match.end,
                confidence=match.confidence,
                detection_method='REGEX',
                metadata={'pattern_type': 'regex'}
            )
            detections.append(detection)
        
        return detections
    
    def _run_ner_detection(self, text: str) -> List[DetectedEntity]:
        """
        Run NER-based entity detection.
        
        Args:
            text (str): Input text to analyze
            
        Returns:
            List[DetectedEntity]: NER-detected entities
        """
        ner_entities = self.ner_model.predict_entities(text)
        
        detections = []
        for entity in ner_entities:
            detection = DetectedEntity(
                entity_type=entity.entity_type,
                value=entity.value,
                start=entity.start,
                end=entity.end,
                confidence=entity.confidence,
                detection_method='NER',
                metadata={
                    'ner_label': entity.label,
                    'model_name': self.ner_model.model_name
                }
            )
            detections.append(detection)
        
        return detections
    
    def _merge_overlapping_detections(self, detections: List[DetectedEntity]) -> List[DetectedEntity]:
        """
        Merge overlapping detections intelligently based on priority and confidence.
        
        Args:
            detections (List[DetectedEntity]): List of all detections
            
        Returns:
            List[DetectedEntity]: Merged detections without overlaps
        """
        if not detections:
            return []
        
        # Sort by start position
        sorted_detections = sorted(detections, key=lambda x: x.start)
        merged = []
        
        i = 0
        while i < len(sorted_detections):
            current = sorted_detections[i]
            overlapping = [current]
            
            # Find all overlapping detections
            j = i + 1
            while j < len(sorted_detections):
                next_detection = sorted_detections[j]
                if self._detections_overlap(current, next_detection):
                    overlapping.append(next_detection)
                    j += 1
                else:
                    break
            
            # Choose the best detection from overlapping ones
            best_detection = self._choose_best_detection(overlapping)
            merged.append(best_detection)
            
            # Move to next non-overlapping detection
            i = j if j > i + 1 else i + 1
        
        return merged
    
    def _detections_overlap(self, det1: DetectedEntity, det2: DetectedEntity) -> bool:
        """
        Check if two detections overlap in text positions.
        
        Args:
            det1 (DetectedEntity): First detection
            det2 (DetectedEntity): Second detection
            
        Returns:
            bool: True if detections overlap
        """
        return not (det1.end <= det2.start or det2.end <= det1.start)
    
    def _choose_best_detection(self, overlapping: List[DetectedEntity]) -> DetectedEntity:
        """
        Choose the best detection from a list of overlapping detections.
        
        Selection criteria (in order of priority):
        1. Higher entity priority (more specific types)
        2. Higher confidence score
        3. Longer text span (more complete detection)
        
        Args:
            overlapping (List[DetectedEntity]): List of overlapping detections
            
        Returns:
            DetectedEntity: The best detection
        """
        if len(overlapping) == 1:
            return overlapping[0]
        
        def scoring_function(detection: DetectedEntity) -> Tuple[int, float, int]:
            priority = self.entity_priority.get(detection.entity_type, 0)
            confidence = detection.confidence
            length = detection.end - detection.start
            return (priority, confidence, length)
        
        # Choose detection with highest score
        best = max(overlapping, key=scoring_function)
        
        # Combine metadata from all overlapping detections
        all_methods = {det.detection_method for det in overlapping}
        if len(all_methods) > 1:
            best.detection_method = 'COMBINED'
            best.metadata['combined_from'] = list(all_methods)
            best.metadata['alternative_detections'] = len(overlapping) - 1
        
        return best
    
    def get_detection_summary(self, detections: List[DetectedEntity]) -> Dict[str, int]:
        """
        Get a summary of detection results by entity type.
        
        Args:
            detections (List[DetectedEntity]): List of detections
            
        Returns:
            Dict[str, int]: Count of entities by type
        """
        summary = defaultdict(int)
        for detection in detections:
            summary[detection.entity_type] += 1
        return dict(summary)
    
    def filter_by_confidence(self, detections: List[DetectedEntity], 
                           min_confidence: float) -> List[DetectedEntity]:
        """
        Filter detections by minimum confidence threshold.
        
        Args:
            detections (List[DetectedEntity]): List of detections
            min_confidence (float): Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            List[DetectedEntity]: Filtered detections
        """
        return [det for det in detections if det.confidence >= min_confidence]
    
    def filter_by_types(self, detections: List[DetectedEntity], 
                       allowed_types: Set[str]) -> List[DetectedEntity]:
        """
        Filter detections by allowed entity types.
        
        Args:
            detections (List[DetectedEntity]): List of detections
            allowed_types (Set[str]): Set of allowed entity types
            
        Returns:
            List[DetectedEntity]: Filtered detections
        """
        return [det for det in detections if det.entity_type in allowed_types]


# Global pipeline instance
pii_detection_pipeline = None

def get_pii_pipeline() -> PiiDetectionPipeline:
    """
    Get or create the global PII detection pipeline instance.
    
    Returns:
        PiiDetectionPipeline: The global pipeline instance
    """
    global pii_detection_pipeline
    if pii_detection_pipeline is None:
        pii_detection_pipeline = PiiDetectionPipeline()
    return pii_detection_pipeline