"""
NER Model Handler for Spanish PII Detection

This module provides integration with Hugging Face transformers for Named Entity
Recognition (NER) specifically tailored for Spanish text and PII detection.

Author: Shield AI Team
Date: 2025-09-18
"""

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass


@dataclass
class NerEntity:
    """
    Represents a Named Entity Recognition result.
    
    Attributes:
        entity_type (str): Type of entity (PERSON, LOCATION, ORGANIZATION, etc.)
        value (str): The actual entity text
        start (int): Start position in original text
        end (int): End position in original text
        confidence (float): Model confidence score (0.0 to 1.0)
        label (str): Original model label (B-PER, I-PER, etc.)
    """
    entity_type: str
    value: str
    start: int
    end: int
    confidence: float
    label: str


class SpanishNerModel:
    """
    Handles Spanish NER model operations using Hugging Face transformers.
    
    Uses the PlanTL-GOB-ES/roberta-base-bne-capitel-ner model which is
    specifically trained on Spanish text and optimized for Spanish entities.
    """
    
    def __init__(self, model_name: str = "mrm8488/bert-spanish-cased-finetuned-ner"):
        """
        Initialize the Spanish NER model.
        
        Args:
            model_name (str): Name of the Hugging Face model to use
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.ner_pipeline = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
        
    def _load_model(self) -> None:
        """
        Load the tokenizer and model from Hugging Face.
        
        Raises:
            Exception: If model loading fails
        """
        try:
            logging.info(f"Loading NER model: {self.model_name}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            
            # Move model to appropriate device
            self.model.to(self.device)
            
            # Create pipeline for easier inference
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                aggregation_strategy="simple"  # Combines B- and I- tags automatically
            )
            
            logging.info(f"Model loaded successfully on device: {self.device}")
            
        except Exception as e:
            logging.error(f"Failed to load NER model: {str(e)}")
            raise
    
    def predict_entities(self, text: str, confidence_threshold: float = 0.5) -> List[NerEntity]:
        """
        Predict named entities in the given text.
        
        Args:
            text (str): Input text to analyze
            confidence_threshold (float): Minimum confidence score to accept predictions
            
        Returns:
            List[NerEntity]: List of detected entities with metadata
        """
        if not text.strip():
            return []
            
        try:
            # Get predictions from the pipeline
            predictions = self.ner_pipeline(text)
            
            entities = []
            for pred in predictions:
                # Filter by confidence threshold
                if pred['score'] >= confidence_threshold:
                    # Map model labels to our entity types
                    entity_type = self._map_label_to_type(pred['entity_group'])
                    
                    entity = NerEntity(
                        entity_type=entity_type,
                        value=pred['word'],
                        start=pred['start'],
                        end=pred['end'],
                        confidence=pred['score'],
                        label=pred['entity_group']
                    )
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            logging.error(f"Error during NER prediction: {str(e)}")
            return []
    
    def _map_label_to_type(self, label: str) -> str:
        """
        Map model-specific labels to our standardized entity types.
        
        Args:
            label (str): Original model label
            
        Returns:
            str: Standardized entity type
        """
        # Common mappings for Spanish NER models
        label_mapping = {
            'PER': 'PERSON',
            'PERSON': 'PERSON',
            'LOC': 'LOCATION', 
            'LOCATION': 'LOCATION',
            'ORG': 'ORGANIZATION',
            'ORGANIZATION': 'ORGANIZATION',
            'MISC': 'MISCELLANEOUS',
            'MISCELLANEOUS': 'MISCELLANEOUS'
        }
        
        return label_mapping.get(label.upper(), label.upper())
    
    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the loaded model.
        
        Returns:
            Dict[str, str]: Model information including name, device, and config
        """
        return {
            'model_name': self.model_name,
            'device': str(self.device),
            'vocab_size': len(self.tokenizer.vocab) if self.tokenizer else 0,
            'max_length': self.tokenizer.model_max_length if self.tokenizer else 0
        }


# Global instance for easy import
spanish_ner_model = None

def get_ner_model() -> SpanishNerModel:
    """
    Get or create the global NER model instance.
    
    Returns:
        SpanishNerModel: The global NER model instance
    """
    global spanish_ner_model
    if spanish_ner_model is None:
        spanish_ner_model = SpanishNerModel()
    return spanish_ner_model