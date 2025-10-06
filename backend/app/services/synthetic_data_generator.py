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
    OTHER = "OTHER"

class ImprovedMappingValidator:
    """Validador mejorado que filtra falsos positivos"""
    
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
        """Valida y limpia el mapping eliminando falsos positivos"""
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
        """Validación básica del valor"""
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
        """Selecciona el mejor token basado en prioridades"""
        if not tokens:
            return None
            
        priority_order = ['EMAIL', 'PHONE', 'DNI', 'NIE', 'IBAN', 'PERSON', 'ORG', 'ORGANIZATION', 'LOCATION']
        
        for priority_type in priority_order:
            matching_tokens = [t for t in tokens if t.startswith(f'[{priority_type}_') or t.upper().startswith(f'{priority_type}_')]
            if matching_tokens:
                return matching_tokens[0]
        
        return tokens[0] if tokens else None
    
    @staticmethod
    def _is_valid_entity(token: str, value: str) -> bool:
        """Validación específica por tipo de entidad"""
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
        
        return True


class EnhancedSyntheticDataGenerator:
    """Generador mejorado de datos sintéticos con mayor realismo"""
    
    def __init__(self, locale='es_ES'):
        self.fake = Faker(locale)
        self._name_cache = {}
        self._email_cache = {}
        
    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        """Genera reemplazo sintético basado en el tipo de entidad"""
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
            else:
                return self._generate_fallback(original_value)
        except Exception:
            return self._generate_fallback(original_value)
    
    def _generate_dni(self) -> str:
        """Genera DNI sintético válido"""
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        letter = letters[int(numbers) % 23]
        return f"{numbers}{letter}"
    
    def _generate_nie(self) -> str:
        """Genera NIE sintético válido"""
        prefix = random.choice(['X', 'Y', 'Z'])
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        prefix_num = {'X': 0, 'Y': 1, 'Z': 2}[prefix]
        full_number = str(prefix_num) + numbers
        control = letters[int(full_number) % 23]
        return f"{prefix}{numbers}{control}"
    
    def _generate_phone(self, original: str) -> str:
        """Genera teléfono sintético español con formato natural"""
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
        """Genera email sintético realista manteniendo el dominio"""
        if '@' in original:
            domain = original.split('@')[-1]
            local_part = original.split('@')[0]
            
            if original in self._email_cache:
                return self._email_cache[original]
            
            if '.' in local_part:
                first_name = self.fake.first_name().lower()
                last_name = self.fake.last_name().lower()
                synthetic_email = f"{first_name}.{last_name}@{domain}"
            elif '_' in local_part:
                first_name = self.fake.first_name().lower()
                last_name = self.fake.last_name().lower()
                synthetic_email = f"{first_name}_{last_name}@{domain}"
            elif any(char.isdigit() for char in local_part):
                username = self.fake.user_name()
                number = random.randint(10, 99)
                synthetic_email = f"{username}{number}@{domain}"
            else:
                first_name = self.fake.first_name().lower()
                last_name = self.fake.last_name().lower()
                synthetic_email = f"{first_name}{last_name}@{domain}"
            
            self._email_cache[original] = synthetic_email
            return synthetic_email
        
        return self.fake.email()
    
    def _generate_person_name(self, original: str) -> str:
        """Genera nombre sintético manteniendo estructura y estilo"""
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
        """Genera ubicación sintética española"""
        cities = [
            'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 
            'Zaragoza', 'Murcia', 'Córdoba', 'Palma', 'Granada',
            'Alicante', 'Valladolid', 'Vigo', 'Gijón', 'Salamanca'
        ]
        return random.choice(cities)
    
    def _generate_organization(self, original: str = None) -> str:
        """Genera organización sintética manteniendo sufijos legales"""
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
        """Genera IBAN sintético español con formato correcto"""
        bank = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        branch = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        account = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        iban_control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        return f"ES{iban_control} {bank} {branch} {control} {account}"
    
    def _generate_fallback(self, original: str) -> str:
        """Fallback para tipos desconocidos con mayor inteligencia"""
        if original.isdigit():
            return ''.join([str(random.randint(0, 9)) for _ in range(len(original))])
        elif len(original.split()) > 1:
            return ' '.join([self.fake.word() for _ in range(len(original.split()))])
        else:
            return self.fake.word()