"""
Spanish PII Detection Regex Patterns

This module contains comprehensive regex patterns for detecting Spanish-specific
Personally Identifiable Information (PII) including DNI, NIE, phone numbers,
postal codes, credit cards, and IBAN numbers.

Author: Shield AI Team
Date: 2025-09-18
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PiiMatch:
    """
    Represents a detected PII match with its type, value, and position.
    
    Attributes:
        pii_type (str): Type of PII detected (e.g., 'DNI', 'EMAIL', 'PHONE')
        value (str): The actual detected value
        start (int): Start position in the original text
        end (int): End position in the original text
        confidence (float): Confidence score (0.0 to 1.0)
    """
    pii_type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0


class SpanishPiiRegexPatterns:
    """
    Spanish-specific PII regex patterns with validation logic.
    
    This class provides comprehensive pattern matching for Spanish PII types
    including document numbers, contact information, and financial data.
    """
    
    def __init__(self):
        """Initialize regex patterns for Spanish PII detection."""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile all regex patterns for better performance."""
        
        # DNI Pattern: 8 digits + 1 letter (with optional formatting)
        # Valid format: 12345678A, 12.345.678-A, 12 345 678 A
        self.dni_pattern = re.compile(
            r'\b(?:DNI[\s:]*)?(\d{1,2}[\.\s]?\d{3}[\.\s]?\d{3}[\s\-]?[A-Z])\b',
            re.IGNORECASE
        )
        
        # NIE Pattern: X/Y/Z + 7 digits + 1 letter
        # Valid format: X1234567A, Y-1234567-B, Z 1234567 C
        self.nie_pattern = re.compile(
            r'\b(?:NIE[\s:]*)?([XYZ][\s\-]?\d{7}[\s\-]?[A-Z])\b',
            re.IGNORECASE
        )
        
        # Spanish mobile phones: +34 6XX XXX XXX or +34 7XX XXX XXX
        # Also matches without country code: 6XX XXX XXX
        self.mobile_phone_pattern = re.compile(
            r'\b(?:\+34[\s\-]?)?([67]\d{2}[\s\-]?\d{3}[\s\-]?\d{3})\b'
        )
        
        # Spanish landline phones: +34 9XX XXX XXX
        # Regional codes: 91 (Madrid), 93 (Barcelona), 95 (Sevilla), etc.
        self.landline_phone_pattern = re.compile(
            r'\b(?:\+34[\s\-]?)?([89]\d{2}[\s\-]?\d{3}[\s\-]?\d{3})\b'
        )
        
        # Spanish postal codes: 5 digits (first 2 indicate province)
        # Range: 01000-52999 (valid Spanish postal codes)
        self.postal_code_pattern = re.compile(
            r'\b(?:CP[\s:]*)?([0-4]\d{4}|5[0-2]\d{3})\b'
        )
        
        # Email addresses with comprehensive validation
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Credit card numbers (Visa, Mastercard, American Express)
        # Supports various formatting: spaces, dashes, or no separation
        self.credit_card_pattern = re.compile(
            r'\b(?:4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}|'  # Visa
            r'5[1-5]\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}|'  # Mastercard
            r'3[47]\d{2}[\s\-]?\d{6}[\s\-]?\d{5})\b'  # American Express
        )
        
        # Spanish IBAN: ES + 2 check digits + 20 digits
        # Format: ES12 1234 1234 1234 1234 1234
        self.iban_pattern = re.compile(
            r'\bES\d{2}[\s]?(?:\d{4}[\s]?){5}\b',
            re.IGNORECASE
        )
        
        # Old Spanish bank account (CCC): 4+4+2+10 digits
        # Format: 1234-1234-12-1234567890
        self.ccc_pattern = re.compile(
            r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{2}[\s\-]?\d{10}\b'
        )
        
        # Spanish addresses with street types
        self.address_pattern = re.compile(
            r'\b(?:C/|Calle|Avenida|Avda?|Plaza|Pl|Paseo|P°|Carrer|'
            r'Ronda|Travesía|Camino)[\s]+[A-ZÀ-ÿ\s\d,]+(?:\d{1,4}[A-Z]?)\b',
            re.IGNORECASE
        )
    
    def validate_dni(self, dni: str) -> bool:
        """
        Validate Spanish DNI using check digit algorithm.
        
        Args:
            dni (str): DNI string to validate
            
        Returns:
            bool: True if DNI is valid, False otherwise
        """
        # Remove formatting and extract numbers and letter
        clean_dni = re.sub(r'[\s\.\-]', '', dni.upper())
        if len(clean_dni) != 9:
            return False
            
        numbers = clean_dni[:8]
        letter = clean_dni[8]
        
        # DNI letter calculation table
        dni_letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        
        try:
            calculated_letter = dni_letters[int(numbers) % 23]
            return letter == calculated_letter
        except (ValueError, IndexError):
            return False
    
    def validate_nie(self, nie: str) -> bool:
        """
        Validate Spanish NIE using check digit algorithm.
        
        Args:
            nie (str): NIE string to validate
            
        Returns:
            bool: True if NIE is valid, False otherwise
        """
        # Remove formatting
        clean_nie = re.sub(r'[\s\-]', '', nie.upper())
        if len(clean_nie) != 9:
            return False
            
        # Replace first letter with corresponding number
        first_char = clean_nie[0]
        if first_char == 'X':
            number_part = '0' + clean_nie[1:8]
        elif first_char == 'Y':
            number_part = '1' + clean_nie[1:8]
        elif first_char == 'Z':
            number_part = '2' + clean_nie[1:8]
        else:
            return False
            
        letter = clean_nie[8]
        dni_letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        
        try:
            calculated_letter = dni_letters[int(number_part) % 23]
            return letter == calculated_letter
        except (ValueError, IndexError):
            return False
    
    def validate_iban(self, iban: str) -> bool:
        """
        Validate Spanish IBAN using mod-97 algorithm.
        
        Args:
            iban (str): IBAN string to validate
            
        Returns:
            bool: True if IBAN is valid, False otherwise
        """
        # Remove spaces and convert to uppercase
        clean_iban = re.sub(r'\s', '', iban.upper())
        
        if not clean_iban.startswith('ES') or len(clean_iban) != 24:
            return False
            
        # Move first 4 characters to end and replace letters with numbers
        rearranged = clean_iban[4:] + clean_iban[:4]
        
        # Replace letters with numbers (A=10, B=11, ..., Z=35)
        numeric_string = ''
        for char in rearranged:
            if char.isdigit():
                numeric_string += char
            else:
                numeric_string += str(ord(char) - ord('A') + 10)
        
        try:
            return int(numeric_string) % 97 == 1
        except ValueError:
            return False
    
    def detect_pii_patterns(self, text: str) -> List[PiiMatch]:
        """
        Detect all PII patterns in the given text.
        
        Args:
            text (str): Input text to analyze
            
        Returns:
            List[PiiMatch]: List of detected PII matches with metadata
        """
        matches = []
        
        # DNI detection with validation
        for match in self.dni_pattern.finditer(text):
            dni_value = match.group(1)
            if self.validate_dni(dni_value):
                matches.append(PiiMatch(
                    pii_type='DNI',
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                ))
        
        # NIE detection with validation
        for match in self.nie_pattern.finditer(text):
            nie_value = match.group(1)
            if self.validate_nie(nie_value):
                matches.append(PiiMatch(
                    pii_type='NIE',
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                ))
        
        # Mobile phone detection
        for match in self.mobile_phone_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='MOBILE_PHONE',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))
        
        # Landline phone detection
        for match in self.landline_phone_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='LANDLINE_PHONE',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))
        
        # Email detection
        for match in self.email_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='EMAIL',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.90
            ))
        
        # Postal code detection
        for match in self.postal_code_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='POSTAL_CODE',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.80
            ))
        
        # Credit card detection
        for match in self.credit_card_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='CREDIT_CARD',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.90
            ))
        
        # IBAN detection with validation
        for match in self.iban_pattern.finditer(text):
            if self.validate_iban(match.group(0)):
                matches.append(PiiMatch(
                    pii_type='IBAN',
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                ))
        
        # CCC detection
        for match in self.ccc_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='CCC',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))
        
        # Address detection
        for match in self.address_pattern.finditer(text):
            matches.append(PiiMatch(
                pii_type='ADDRESS',
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.75
            ))
        
        # Sort matches by start position
        matches.sort(key=lambda x: x.start)
        
        return matches


# Global instance for easy import
spanish_pii_regex = SpanishPiiRegexPatterns()