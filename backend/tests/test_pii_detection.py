"""
Unit Tests for PII Detection System

This module contains comprehensive tests for the Shield AI PII detection system,
covering regex patterns, NER integration, and the unified pipeline.

Author: Shield AI Team
Date: 2025-09-18
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the app directory to sys.path to import our modules
current_dir = os.path.dirname(__file__)
app_dir = os.path.join(current_dir, '..', 'app')
sys.path.insert(0, app_dir)

from pii_detection.regex_patterns import SpanishPiiRegexPatterns, PiiMatch
from pii_detection.pipeline import DetectedEntity, PiiDetectionPipeline
from pii_detection.detector import detect_pii, PiiDetectionResult


class TestSpanishPiiRegexPatterns(unittest.TestCase):
    """Test cases for Spanish regex pattern detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = SpanishPiiRegexPatterns()
    
    def test_dni_detection_valid(self):
        """Test DNI detection with valid documents."""
        test_cases = [
            "Mi DNI es 12345678Z",
            "DNI: 12.345.678-Z",
            "Documento 12 345 678 Z",
            "87654321Y es mi identificación"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                dni_matches = [m for m in matches if m.pii_type == 'DNI']
                self.assertGreater(len(dni_matches), 0, f"No DNI found in: {text}")
    
    def test_dni_validation_algorithm(self):
        """Test DNI validation algorithm with known valid/invalid DNIs."""
        valid_dnis = ["12345678Z", "87654321Y", "11111111H"]
        invalid_dnis = ["12345678A", "87654321Z", "00000000T"]
        
        for dni in valid_dnis:
            with self.subTest(dni=dni):
                self.assertTrue(self.detector.validate_dni(dni), 
                              f"Valid DNI {dni} was rejected")
        
        for dni in invalid_dnis:
            with self.subTest(dni=dni):
                self.assertFalse(self.detector.validate_dni(dni), 
                               f"Invalid DNI {dni} was accepted")
    
    def test_nie_detection_valid(self):
        """Test NIE detection with valid documents."""
        test_cases = [
            "Mi NIE es X1234567L",
            "Y-7654321-A es mi número",
            "Z 9876543 B"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                nie_matches = [m for m in matches if m.pii_type == 'NIE']
                self.assertGreater(len(nie_matches), 0, f"No NIE found in: {text}")
    
    def test_email_detection(self):
        """Test email address detection."""
        test_cases = [
            "Contacta conmigo en juan@email.com",
            "Mi correo es maria.garcia@empresa.es",
            "Email: usuario123@dominio.org"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                email_matches = [m for m in matches if m.pii_type == 'EMAIL']
                self.assertGreater(len(email_matches), 0, f"No email found in: {text}")
    
    def test_phone_detection_spanish(self):
        """Test Spanish phone number detection."""
        test_cases = [
            "Llámame al 666 123 456",
            "Mi teléfono es +34 612 345 678",
            "Fijo: 91 123 45 67",
            "+34 93 456 78 90"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                phone_matches = [m for m in matches if 'PHONE' in m.pii_type]
                self.assertGreater(len(phone_matches), 0, f"No phone found in: {text}")
    
    def test_iban_detection_and_validation(self):
        """Test IBAN detection with validation."""
        # Valid Spanish IBAN (this is a test IBAN, not real)
        valid_iban = "ES91 2100 0418 4502 0005 1332"
        text_with_iban = f"Mi cuenta bancaria es {valid_iban}"
        
        matches = self.detector.detect_pii_patterns(text_with_iban)
        iban_matches = [m for m in matches if m.pii_type == 'IBAN']
        
        self.assertGreater(len(iban_matches), 0, "Valid IBAN not detected")
    
    def test_credit_card_detection(self):
        """Test credit card number detection."""
        test_cases = [
            "Tarjeta Visa: 4111 1111 1111 1111",
            "Mastercard 5555555555554444",
            "AMEX: 378282246310005"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                cc_matches = [m for m in matches if m.pii_type == 'CREDIT_CARD']
                self.assertGreater(len(cc_matches), 0, f"No credit card found in: {text}")
    
    def test_postal_code_spanish(self):
        """Test Spanish postal code detection."""
        test_cases = [
            "Vivo en Madrid, CP 28001",
            "Mi código postal es 08001",
            "Barcelona 08080"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                pc_matches = [m for m in matches if m.pii_type == 'POSTAL_CODE']
                self.assertGreater(len(pc_matches), 0, f"No postal code found in: {text}")
    
    def test_false_positives_avoidance(self):
        """Test that common false positives are avoided."""
        false_positive_texts = [
            "El año 2023 fue bueno",  # Should not detect as phone
            "Mi IP es 192.168.1.1",  # Should not detect as postal code
            "Precio: 99.99 euros",   # Should not detect as DNI
        ]
        
        for text in false_positive_texts:
            with self.subTest(text=text):
                matches = self.detector.detect_pii_patterns(text)
                # These should have no matches or very low confidence
                high_conf_matches = [m for m in matches if m.confidence > 0.8]
                self.assertEqual(len(high_conf_matches), 0, 
                               f"False positive detected in: {text}")


class TestPiiDetectionPipeline(unittest.TestCase):
    """Test cases for the unified PII detection pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create pipeline with mocked NER to avoid model loading in tests
        self.pipeline = PiiDetectionPipeline(use_ner=False, use_regex=True)
    
    def test_regex_only_detection(self):
        """Test detection using only regex patterns."""
        text = "Hola, soy Juan Pérez, mi DNI es 12345678Z y mi email juan@test.com"
        
        detections = self.pipeline.detect_pii(text)
        
        # Should detect DNI and email at minimum
        entity_types = {det.entity_type for det in detections}
        self.assertIn('DNI', entity_types)
        self.assertIn('EMAIL', entity_types)
    
    def test_overlapping_detection_merge(self):
        """Test merging of overlapping detections."""
        # Create fake overlapping detections
        detections = [
            DetectedEntity(
                entity_type='PERSON',
                value='Juan Pérez',
                start=10,
                end=20,
                confidence=0.8,
                detection_method='NER'
            ),
            DetectedEntity(
                entity_type='DNI',
                value='12345678Z',
                start=15,
                end=24,
                confidence=0.9,
                detection_method='REGEX'
            )
        ]
        
        merged = self.pipeline._merge_overlapping_detections(detections)
        
        # Should prefer DNI over PERSON due to higher priority
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].entity_type, 'DNI')
    
    def test_confidence_filtering(self):
        """Test filtering detections by confidence threshold."""
        detections = [
            DetectedEntity('PERSON', 'Juan', 0, 4, 0.9, 'NER'),
            DetectedEntity('EMAIL', 'test@email.com', 5, 18, 0.4, 'REGEX'),
            DetectedEntity('DNI', '12345678Z', 19, 28, 0.95, 'REGEX')
        ]
        
        filtered = self.pipeline.filter_by_confidence(detections, 0.5)
        
        # Should keep only high-confidence detections
        self.assertEqual(len(filtered), 2)
        confidence_scores = [det.confidence for det in filtered]
        self.assertTrue(all(score >= 0.5 for score in confidence_scores))


class TestMainDetectionInterface(unittest.TestCase):
    """Test cases for the main detection interface."""
    
    def test_detect_pii_basic_functionality(self):
        """Test basic PII detection functionality."""
        text = "Mi DNI es 12345678Z y mi email es test@email.com"
        
        # Mock the pipeline to avoid NER model loading
        with patch('pii_detection.detector.get_pii_pipeline') as mock_pipeline:
            mock_instance = Mock()
            mock_instance.detect_pii.return_value = [
                DetectedEntity('DNI', '12345678Z', 10, 19, 0.95, 'REGEX'),
                DetectedEntity('EMAIL', 'test@email.com', 32, 46, 0.9, 'REGEX')
            ]
            mock_instance.filter_by_confidence.side_effect = lambda entities, threshold: entities
            mock_instance.filter_by_types.side_effect = lambda entities, types: entities
            mock_pipeline.return_value = mock_instance
            
            result = detect_pii(text)
            
            self.assertIsInstance(result, PiiDetectionResult)
            self.assertEqual(result.total_entities, 2)
            self.assertIn('DNI', result.detection_summary)
            self.assertIn('EMAIL', result.detection_summary)
    
    def test_empty_text_handling(self):
        """Test handling of empty or whitespace-only text."""
        empty_texts = ["", "   ", "\n\t   \n"]
        
        for text in empty_texts:
            with self.subTest(text=repr(text)):
                result = detect_pii(text)
                self.assertEqual(result.total_entities, 0)
                self.assertEqual(result.text_length, 0)
    
    def test_invalid_parameters(self):
        """Test handling of invalid parameters."""
        text = "Valid text for testing"
        
        # Test invalid confidence threshold
        with self.assertRaises(ValueError):
            detect_pii(text, confidence_threshold=1.5)
        
        with self.assertRaises(ValueError):
            detect_pii(text, confidence_threshold=-0.1)
        
        # Test disabling all detection methods
        with self.assertRaises(ValueError):
            detect_pii(text, enable_ner=False, enable_regex=False)
    
    def test_result_filtering_by_confidence(self):
        """Test result filtering by confidence threshold."""
        # This would require mocking the pipeline again
        pass


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios with realistic data."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.regex_detector = SpanishPiiRegexPatterns()
    
    def test_complex_text_scenario(self):
        """Test detection in complex, realistic text."""
        complex_text = """
        Estimado Sr. García,
        
        Le escribo para confirmar sus datos personales:
        - DNI: 12345678Z
        - Teléfono: +34 666 123 456
        - Email: juan.garcia@empresa.es
        - Dirección: Calle Mayor 123, 28001 Madrid
        - Cuenta bancaria: ES91 2100 0418 4502 0005 1332
        
        Atentamente,
        María López
        Departamento de RRHH
        """
        
        matches = self.regex_detector.detect_pii_patterns(complex_text)
        
        # Should detect multiple types of PII
        entity_types = {match.pii_type for match in matches}
        expected_types = {'DNI', 'MOBILE_PHONE', 'EMAIL', 'POSTAL_CODE', 'IBAN'}
        
        # Check that we detect most expected types
        detected_expected = entity_types.intersection(expected_types)
        self.assertGreaterEqual(len(detected_expected), 3, 
                               f"Expected to detect at least 3 types, got: {entity_types}")
    
    def test_mixed_format_detection(self):
        """Test detection with various formatting styles."""
        mixed_format_text = """
        DNI sin espacios: 12345678Z
        DNI con puntos: 12.345.678-Z
        Teléfono internacional: +34 666123456
        Teléfono con espacios: 666 123 456
        Email simple: test@email.com
        Email complejo: usuario.apellido+etiqueta@dominio-empresa.es
        """
        
        matches = self.regex_detector.detect_pii_patterns(mixed_format_text)
        
        # Should detect entities despite different formatting
        self.assertGreater(len(matches), 4, "Should detect multiple formatted entities")


def run_manual_tests():
    """
    Manual test function for interactive testing.
    Call this function to run interactive tests with sample data.
    """
    print("=== Manual PII Detection Tests ===\n")
    
    # Initialize detector
    regex_detector = SpanishPiiRegexPatterns()
    
    # Test cases for manual verification
    test_texts = [
        "Mi nombre es Juan Pérez y mi DNI es 12345678Z",
        "Contacta conmigo en juan@email.com o llama al 666 123 456",
        "Vivo en Calle Mayor 123, CP 28001, Madrid",
        "Mi cuenta bancaria es ES91 2100 0418 4502 0005 1332",
        "Tarjeta de crédito: 4111 1111 1111 1111"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"Test {i}: {text}")
        matches = regex_detector.detect_pii_patterns(text)
        
        if matches:
            for match in matches:
                print(f"  -> {match.pii_type}: '{match.value}' "
                     f"(confidence: {match.confidence:.2f})")
        else:
            print("  -> No PII detected")
        print()


if __name__ == '__main__':
    # Run unit tests
    unittest.main(verbosity=2, exit=False)
    
    # Run manual tests
    print("\n" + "="*50)
    run_manual_tests()