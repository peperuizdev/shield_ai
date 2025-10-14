"""
Sistema de generación de datos sintéticos mejorado
Extrae solo las partes necesarias del pipeline mejorado
"""

import random
import hashlib
import re
import pickle
import os
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from faker import Faker
from enum import Enum

class EntityType(Enum):
    DNI = "DNI"
    NIE = "NIE"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    ORG = "ORGANIZATION"
    IBAN = "IBAN"
    DOB = "DOB"
    OTHER = "OTHER"

class ImprovedMappingValidator:
    
    STOPWORDS = {
        'el', 'la', 'de', 'en', 'un', 'una', 'con', 'su', 'es', 'se', 'por', 'para',
        'del', 'al', 'le', 'les', 'me', 'te', 'nos', 'os', 'lo', 'las', 'los', 'an',
        'y', 'o', 'pero', 'si', 'no', 'que', 'como', 'cuando', 'donde', 'sra', 'sr',
        'estimado', 'estimada', 'atentamente', 'saludo', 'saludos', 'cordialmente',
        'departamento'
    }
    
    INVALID_PATTERNS = [
        r'^[a-z]{1,3}$',
        r'^\.$',
        r'^[A-Z]$',
        r'^[^a-zA-Z0-9@.]+$',
        r'^[a-z]+$',
        r'^\d{1,3}$',
        r'^[.,:;!?-]+$'
    ]
    
    @staticmethod
    def validate_and_clean_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
        if not mapping:
            return {}
            
        cleaned_mapping = {}
        
        grouped_values = {}
        for token, value in mapping.items():
            clean_value = value.strip()
            if clean_value not in grouped_values:
                grouped_values[clean_value] = []
            grouped_values[clean_value].append(token)
        
        for value, tokens in grouped_values.items():
            if not ImprovedMappingValidator._is_valid_entity_value(value):
                continue
                
            best_token = ImprovedMappingValidator._select_best_token(tokens, value)
            
            if best_token and ImprovedMappingValidator._is_valid_entity(best_token, value):
                cleaned_mapping[best_token] = value
        
        return cleaned_mapping
    
    @staticmethod
    def _is_valid_entity_value(value: str) -> bool:
        clean_value = value.strip().lower()
        
        if len(clean_value) < 2:
            return False
            
        if clean_value in ImprovedMappingValidator.STOPWORDS:
            return False
            
        for pattern in ImprovedMappingValidator.INVALID_PATTERNS:
            if re.match(pattern, value.strip()):
                return False
        
        return True
    
    @staticmethod
    def _select_best_token(tokens: List[str], value: str) -> Optional[str]:
        if not tokens:
            return None
            
        priority_order = ['EMAIL', 'PHONE', 'DNI', 'NIE', 'IBAN', 'DOB', 'PERSON', 'ORG', 'ORGANIZATION', 'LOCATION']
        
        for priority_type in priority_order:
            matching_tokens = [t for t in tokens if t.startswith(f'[{priority_type}_') or t.upper().startswith(f'{priority_type}_')]
            if matching_tokens:
                return matching_tokens[0]
        
        return tokens[0] if tokens else None
    
    @staticmethod
    def _is_valid_entity(token: str, value: str) -> bool:
        token_upper = token.upper()
        
        if 'EMAIL' in token_upper:
            return '@' in value and '.' in value and len(value) > 5
        elif 'PHONE' in token_upper or 'TEL' in token_upper:
            digits = re.sub(r'[^\d]', '', value)
            return len(digits) >= 7 and len(digits) <= 15
        elif 'PERSON' in token_upper or 'PER' in token_upper:
            words = value.split()
            if len(words) < 2:
                return False
            return all(len(word) >= 2 and word[0].isupper() for word in words if word)
        elif 'DNI' in token_upper:
            return bool(re.match(r'^\d{8}[A-Z]$', value.strip()))
        elif 'ORG' in token_upper:
            return len(value.strip()) >= 3
        elif 'LOCATION' in token_upper or 'LOC' in token_upper:
            return len(value.strip()) >= 3 and value[0].isupper()
        elif 'DOB' in token_upper:
            date_patterns = [
                r'\d{2}[-/]\d{2}[-/]\d{4}',
                r'\d{4}[-/]\d{2}[-/]\d{2}'
            ]
            return any(re.match(pattern, value.strip()) for pattern in date_patterns)
        
        return True


class EnhancedSyntheticDataGenerator:
    
    def __init__(self, locale='es_ES'):
        self.fake = Faker(locale)
        self._name_cache = {}
        self._email_cache = {}
    
    def _sanitize_email_part(self, text: str, max_length: int = 20) -> str:
        import unicodedata
        
        text = text.lower().strip()
        
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        text = re.sub(r"['\s]+", '', text)
        
        text = re.sub(r'[^a-z0-9._-]', '', text)
        
        text = text.strip('._-')
        
        if len(text) > max_length:
            text = text[:max_length]
        
        if not text or len(text) < 2:
            text = 'user' + str(random.randint(100, 999))
        
        return text
    
    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) and len(email) <= 254
        
    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        entity_type_upper = entity_type.upper()
        
        try:
            if entity_type_upper == 'DNI':
                return self._generate_dni()
            elif entity_type_upper == 'NIE':
                return self._generate_nie()
            elif entity_type_upper == 'EMAIL':
                return self._generate_email(original_value)
            elif entity_type_upper in ['PHONE', 'TEL']:
                return self._generate_phone(original_value)
            elif entity_type_upper in ['PERSON', 'PER']:
                return self._generate_person_name(original_value)
            elif entity_type_upper in ['LOCATION', 'LOC']:
                return self._generate_location()
            elif entity_type_upper in ['ORGANIZATION', 'ORG']:
                return self._generate_organization(original_value)
            elif entity_type_upper == 'IBAN':
                return self._generate_iban()
            elif entity_type_upper == 'DOB':
                return self._generate_dob(original_value)
            else:
                return self._generate_fallback(original_value)
        except Exception:
            return self._generate_fallback(original_value)
    
    def _generate_dni(self) -> str:
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        letter = letters[int(numbers) % 23]
        return f"{numbers}{letter}"
    
    def _generate_nie(self) -> str:
        prefix = random.choice(['X', 'Y', 'Z'])
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        prefix_num = {'X': 0, 'Y': 1, 'Z': 2}[prefix]
        full_number = str(prefix_num) + numbers
        control = letters[int(full_number) % 23]
        return f"{prefix}{numbers}{control}"
    
    def _generate_dob(self, original: str) -> str:
        format_patterns = [
            (r'^\d{2}[-/]\d{2}[-/]\d{4}$', 'DD/MM/YYYY', '%d/%m/%Y'),
            (r'^\d{4}[-/]\d{2}[-/]\d{2}$', 'YYYY-MM-DD', '%Y-%m-%d'),
            (r'^\d{2}-\d{2}-\d{4}$', 'DD-MM-YYYY', '%d-%m-%Y'),
            (r'^\d{4}\d{2}\d{2}$', 'YYYYMMDD', '%Y%m%d')
        ]
        
        detected_format = None
        separator = '/'
        
        for pattern, format_name, strftime_format in format_patterns:
            if re.match(pattern, original.strip()):
                detected_format = strftime_format
                if '-' in original:
                    separator = '-'
                elif '/' in original:
                    separator = '/'
                else:
                    separator = ''
                break
        
        if not detected_format:
            detected_format = '%d/%m/%Y'
            separator = '/'
        
        today = datetime.now()
        min_age = 18
        max_age = 80
        
        years_ago = random.randint(min_age, max_age)
        days_offset = random.randint(0, 365)
        
        birth_date = today - timedelta(days=years_ago * 365 + days_offset)
        
        max_attempts = 10
        for _ in range(max_attempts):
            try:
                formatted_date = birth_date.strftime(detected_format)
                
                if separator and separator in detected_format:
                    formatted_date = formatted_date.replace('/', separator).replace('-', separator)
                
                datetime.strptime(formatted_date.replace(separator, '/'), detected_format.replace('-', '/'))
                
                return formatted_date
            except ValueError:
                birth_date = birth_date - timedelta(days=1)
        
        return birth_date.strftime('%d/%m/%Y')
    
    def _generate_phone(self, original: str) -> str:
        has_country_code = '+34' in original or original.strip().startswith('00')
        
        if original and original.strip().startswith('9'):
            first_digit = '9'
            second_digit = random.choice(['1', '2', '3', '4', '5', '6', '7', '8'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(7)])
            phone_number = f"{first_digit}{second_digit}{rest}"
        else:
            first_digit = random.choice(['6', '7'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            phone_number = f"{first_digit}{rest}"
        
        if has_country_code:
            return f"+34 {phone_number[:3]} {phone_number[3:6]} {phone_number[6:]}"
        else:
            return f"{phone_number[:3]} {phone_number[3:6]} {phone_number[6:]}"
    
    def _generate_email(self, original: str) -> str:
        cache_key = original.lower().strip()
        
        if cache_key in self._email_cache:
            return self._email_cache[cache_key]
        
        if '@' not in original:
            synthetic_email = self.fake.email()
            self._email_cache[cache_key] = synthetic_email
            return synthetic_email
        
        try:
            local_part, domain = original.rsplit('@', 1)
            domain = domain.strip()
        except ValueError:
            synthetic_email = self.fake.email()
            self._email_cache[cache_key] = synthetic_email
            return synthetic_email
        
        first_name_raw = self.fake.first_name()
        last_name_raw = self.fake.last_name()
        
        first_name = self._sanitize_email_part(first_name_raw, max_length=15)
        last_name = self._sanitize_email_part(last_name_raw, max_length=15)
        
        if '.' in local_part:
            new_local = f"{first_name}.{last_name}"
        elif '_' in local_part:
            new_local = f"{first_name}_{last_name}"
        elif any(char.isdigit() for char in local_part):
            number = random.randint(10, 99)
            new_local = f"{first_name}{number}"
        else:
            new_local = f"{first_name}{last_name}"
        
        new_local = self._sanitize_email_part(new_local, max_length=30)
        
        synthetic_email = f"{new_local}@{domain}"
        
        if not self._validate_email(synthetic_email):
            fallback_local = f"user{random.randint(1000, 9999)}"
            synthetic_email = f"{fallback_local}@{domain}"
        
        if not self._validate_email(synthetic_email):
            synthetic_email = self.fake.email()
        
        self._email_cache[cache_key] = synthetic_email
        return synthetic_email
    
    def _generate_person_name(self, original: str) -> str:
        if original in self._name_cache:
            return self._name_cache[original]
        
        parts = original.split() if original else []
        
        if len(parts) == 2:
            synthetic_name = f"{self.fake.first_name()} {self.fake.last_name()}"
        elif len(parts) == 3:
            has_middle_initial = len(parts[1]) <= 2 and parts[1].endswith('.')
            if has_middle_initial:
                middle_initial = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                synthetic_name = f"{self.fake.first_name()} {middle_initial}. {self.fake.last_name()}"
            else:
                synthetic_name = f"{self.fake.first_name()} {self.fake.first_name()} {self.fake.last_name()}"
        elif len(parts) >= 4:
            first = self.fake.first_name()
            middle = self.fake.first_name()
            last1 = self.fake.last_name()
            last2 = self.fake.last_name()
            synthetic_name = f"{first} {middle} {last1} {last2}"
        else:
            synthetic_name = self.fake.name()
        
        self._name_cache[original] = synthetic_name
        return synthetic_name
    
    def _generate_location(self) -> str:
        cities = [
            'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 
            'Zaragoza', 'Murcia', 'Córdoba', 'Palma', 'Granada',
            'Alicante', 'Valladolid', 'Vigo', 'Gijón', 'Salamanca'
        ]
        return random.choice(cities)
    
    def _generate_organization(self, original: str = None) -> str:
        if original:
            if 'S.A.' in original or 'SA' in original:
                return f"{self.fake.company()} S.A."
            elif 'S.L.' in original or 'SL' in original:
                return f"{self.fake.company()} S.L."
            elif 'Ltd' in original or 'Limited' in original:
                return f"{self.fake.company()} Ltd."
            elif 'Inc' in original:
                return f"{self.fake.company()} Inc."
            elif 'Departamento' in original or 'Department' in original:
                departments = ['Ventas', 'Marketing', 'Recursos Humanos', 'Tecnología', 'Atención al Cliente']
                return f"Departamento de {random.choice(departments)}"
        
        return f"{self.fake.company()} S.A."
    
    def _generate_iban(self) -> str:
        bank = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        branch = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        account = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        iban_control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        return f"ES{iban_control} {bank} {branch} {control} {account}"
    
    def _generate_fallback(self, original: str) -> str:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Using fallback for unrecognized entity: {original[:50]}")
        
        if original.isdigit():
            return ''.join([str(random.randint(0, 9)) for _ in range(len(original))])
        elif len(original.split()) > 1:
            return ' '.join([self.fake.word() for _ in range(len(original.split()))])
        else:
            return self.fake.word()