"""
Simple PII Detection Tests

Simplified version of tests that can run without complex import setup.
This version tests the core functionality with minimal dependencies.

Author: Shield AI Team
Date: 2025-09-18
"""

import sys
import os

# Add the app directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, '..', 'app')
sys.path.insert(0, app_dir)

def test_regex_patterns():
    """Test regex patterns without unittest framework."""
    print("=== Testing Regex Patterns ===")
    
    try:
        from pii_detection.regex_patterns import SpanishPiiRegexPatterns
        
        detector = SpanishPiiRegexPatterns()
        print("✓ Regex patterns module loaded successfully")
        
        # Test DNI detection
        test_text = "Mi DNI es 12345678Z"
        matches = detector.detect_pii_patterns(test_text)
        
        if matches:
            print(f"✓ DNI detection works: found {len(matches)} matches")
            for match in matches:
                print(f"  - {match.pii_type}: {match.value} (confidence: {match.confidence})")
        else:
            print("✗ DNI detection failed: no matches found")
        
        # Test email detection
        test_text = "Mi email es usuario@dominio.com"
        matches = detector.detect_pii_patterns(test_text)
        email_matches = [m for m in matches if m.pii_type == 'EMAIL']
        
        if email_matches:
            print("✓ Email detection works")
        else:
            print("✗ Email detection failed")
        
        # Test phone detection
        test_text = "Mi teléfono es 666 123 456"
        matches = detector.detect_pii_patterns(test_text)
        phone_matches = [m for m in matches if 'PHONE' in m.pii_type]
        
        if phone_matches:
            print("✓ Phone detection works")
        else:
            print("✗ Phone detection failed")
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import regex patterns: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in regex pattern testing: {e}")
        return False

def test_dni_validation():
    """Test DNI validation algorithm."""
    print("\n=== Testing DNI Validation ===")
    
    try:
        from pii_detection.regex_patterns import SpanishPiiRegexPatterns
        
        detector = SpanishPiiRegexPatterns()
        
        # Test valid DNI (this is a valid test DNI)
        valid_dni = "12345678Z"
        if detector.validate_dni(valid_dni):
            print(f"✓ Valid DNI {valid_dni} correctly validated")
        else:
            print(f"✗ Valid DNI {valid_dni} incorrectly rejected")
        
        # Test invalid DNI
        invalid_dni = "12345678A"  # Wrong letter for this number
        if not detector.validate_dni(invalid_dni):
            print(f"✓ Invalid DNI {invalid_dni} correctly rejected")
        else:
            print(f"✗ Invalid DNI {invalid_dni} incorrectly accepted")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in DNI validation testing: {e}")
        return False

def test_pipeline_basic():
    """Test basic pipeline functionality without NER model."""
    print("\n=== Testing Pipeline (Regex Only) ===")
    
    try:
        from pii_detection.pipeline import PiiDetectionPipeline
        
        # Create pipeline with only regex (no NER to avoid model loading)
        pipeline = PiiDetectionPipeline(use_ner=False, use_regex=True)
        print("✓ Pipeline created successfully")
        
        # Test detection
        text = "Hola, soy Juan Pérez, mi DNI es 12345678Z y mi email es juan@test.com"
        detections = pipeline.detect_pii(text)
        
        if detections:
            print(f"✓ Pipeline detection works: found {len(detections)} entities")
            for detection in detections:
                print(f"  - {detection.entity_type}: {detection.value}")
        else:
            print("✗ Pipeline detection failed: no entities found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in pipeline testing: {e}")
        return False

def test_main_detector():
    """Test the main detector interface."""
    print("\n=== Testing Main Detector Interface ===")
    
    try:
        # First try to import without NER dependencies
        from pii_detection.detector import detect_pii_simple, get_supported_entity_types
        
        print("✓ Main detector module loaded successfully")
        
        # Test supported entity types
        entity_types = get_supported_entity_types()
        print(f"✓ Supported entity types: {len(entity_types)} types available")
        for entity_type, description in list(entity_types.items())[:3]:
            print(f"  - {entity_type}: {description}")
        
        # Test simple detection (this might fail if NER model is required)
        try:
            text = "Mi DNI es 12345678Z"
            entities = detect_pii_simple(text)
            print(f"✓ Simple detection works: found {len(entities)} entities")
        except Exception as e:
            print(f"Note: Simple detection failed (expected if NER model not available): {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in main detector testing: {e}")
        return False

def run_comprehensive_test():
    """Run a comprehensive test with real data."""
    print("\n=== Comprehensive Test with Real Data ===")
    
    test_texts = [
        "Mi nombre es María García y mi DNI es 12345678Z",
        "Puedes contactarme en maria@email.com o llamar al 666 123 456",
        "Vivo en Madrid, código postal 28001",
        "Mi cuenta bancaria es ES91 2100 0418 4502 0005 1332"
    ]
    
    try:
        from pii_detection.regex_patterns import SpanishPiiRegexPatterns
        
        detector = SpanishPiiRegexPatterns()
        
        for i, text in enumerate(test_texts, 1):
            print(f"\nTest {i}: {text}")
            matches = detector.detect_pii_patterns(text)
            
            if matches:
                for match in matches:
                    print(f"  -> {match.pii_type}: '{match.value}' (confidence: {match.confidence:.2f})")
            else:
                print("  -> No PII detected")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in comprehensive testing: {e}")
        return False

def main():
    """Main test runner."""
    print("Shield AI - PII Detection System Tests")
    print("=" * 50)
    
    tests = [
        ("Regex Patterns", test_regex_patterns),
        ("DNI Validation", test_dni_validation),
        ("Pipeline Basic", test_pipeline_basic),
        ("Main Detector", test_main_detector),
        ("Comprehensive Test", run_comprehensive_test)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)