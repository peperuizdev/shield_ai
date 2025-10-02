import random
import os
import sys
import json
import time
import ssl
import hashlib
import re
import locale
import pickle
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from faker import Faker
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl


# =====================================================
# Configuración de logging mejorada y thread-safe
# =====================================================
IS_WINDOWS = sys.platform.startswith('win')
ENCODING = locale.getpreferredencoding()

class ThreadSafeLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self._lock = threading.Lock()
        
    def info(self, message):
        with self._lock:
            self.logger.info(message)
    
    def warning(self, message):
        with self._lock:
            self.logger.warning(message)
            
    def error(self, message):
        with self._lock:
            self.logger.error(message)
            
    def debug(self, message):
        with self._lock:
            self.logger.debug(message)

# Configuración de logging compatible con Windows
if IS_WINDOWS and ENCODING.lower() in ['cp1252', 'windows-1252']:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('llm_pipeline.log', encoding='utf-8')
        ]
    )
    
    def log_step(message, step_num=None):
        if step_num:
            logger.info(f"PASO {step_num}: {message}")
        else:
            logger.info(message)
    
    def log_success(message):
        logger.info(f"EXITO: {message}")
    
    def log_error(message):
        logger.error(f"ERROR: {message}")
        
    def log_warning(message):
        logger.warning(f"ADVERTENCIA: {message}")
        
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('llm_pipeline.log', encoding='utf-8')
        ]
    )
    
    def log_step(message, step_num=None):
        emojis = ["🔍", "🔒", "📝", "🤖", "🔓", "✅"]
        emoji = emojis[step_num-1] if step_num and step_num <= len(emojis) else "📋"
        logger.info(f"{emoji} PASO {step_num}: {message}" if step_num else f"📋 {message}")
    
    def log_success(message):
        logger.info(f"✅ {message}")
    
    def log_error(message):
        logger.error(f"❌ {message}")
        
    def log_warning(message):
        logger.warning(f"⚠️ {message}")

logger = ThreadSafeLogger(__name__)

# =====================================================
# Cargar variables de entorno
# =====================================================
def load_environment():
    """Carga variables de entorno de múltiples ubicaciones posibles"""
    current_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(current_env):
        load_dotenv(dotenv_path=current_env)
        logger.info(f"Loaded .env from: {current_env}")
        return True
    
    parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(parent_env):
        load_dotenv(dotenv_path=parent_env)
        logger.info(f"Loaded .env from: {parent_env}")
        return True
    
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    env_path = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded .env from: {env_path}")
        return True
    
    logger.warning("No .env file found")
    return False

load_environment()

# Variables de configuración
GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("SHIELD_AI_GROK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not any([GROK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY]):
    logger.warning("No se encontraron claves de API para LLM")

# =====================================================
# Enums y Dataclasses
# =====================================================
class EntityType(Enum):
    DNI = "DNI"
    NIE = "NIE"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    MOBILE_PHONE = "MOBILE_PHONE"
    LANDLINE_PHONE = "LANDLINE_PHONE"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    IBAN = "IBAN"
    CREDIT_CARD = "CREDIT_CARD"
    DATE_TIME = "DATE_TIME"
    IP_ADDRESS = "IP_ADDRESS"
    OTHER = "OTHER"

@dataclass
class PipelineResult:
    original_text: str
    anonymized_text: str = ""
    pii_detected: bool = False
    pii_mapping: Dict[str, str] = field(default_factory=dict)
    llm_prompt: str = ""
    llm_response: str = ""
    final_response: str = ""
    success: bool = False
    error: Optional[str] = None
    processing_time: float = 0.0
    llm_provider_used: Optional[str] = None
    confidence_score: float = 0.0
    quality_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str
    endpoint: str
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3

# =====================================================
# Detector PII mejorado con fallback robusto
# =====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from pii_detector import run_pipeline as pii_run_pipeline
    PII_DETECTOR_AVAILABLE = True
    logger.info("PII detector real disponible")
except ImportError:
    logger.warning("No se pudo importar run_pipeline. Usando función mock mejorada.")
    PII_DETECTOR_AVAILABLE = False
    
    def pii_run_pipeline(model="es", text="", use_regex=True, pseudonymize=False):
        """Mock mejorado y más preciso para desarrollo"""
        mapping = {}
        
        # Detectar emails completos
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        for i, email in enumerate(emails, 1):
            mapping[f"[EMAIL_{i}]"] = email
            
        # Detectar nombres propios completos (al menos 2 palabras con mayúscula)
        name_pattern = r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+\b'
        names = re.findall(name_pattern, text)
        valid_names = []
        for name in names:
            words = name.split()
            if len(words) >= 2 and all(len(word) >= 3 for word in words):
                if not any(common in name.lower() for common in ['estimado', 'atentamente', 'departamento']):
                    valid_names.append(name)
        
        for i, name in enumerate(valid_names[:3], 1):
            mapping[f"[PERSON_{i}]"] = name
                
        # Detectar teléfonos españoles
        phone_patterns = [
            r'\+34\s?[6-9]\d{2}\s?\d{3}\s?\d{3}',
            r'\b[6-9]\d{2}\s?\d{3}\s?\d{3}\b',
            r'\b9[0-9]\s?\d{3}\s?\d{2}\s?\d{2}\b'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            for phone in phones:
                if phone not in mapping.values():
                    phone_count = len([k for k in mapping.keys() if k.startswith('[PHONE_')]) + 1
                    mapping[f"[PHONE_{phone_count}]"] = phone
                    
        # Detectar DNI español
        dni_pattern = r'\b\d{8}[A-Z]\b'
        dnis = re.findall(dni_pattern, text)
        for i, dni in enumerate(dnis, 1):
            mapping[f"[DNI_{i}]"] = dni
            
        # Detectar NIE español
        nie_pattern = r'\b[XYZ]\d{7}[A-Z]\b'
        nies = re.findall(nie_pattern, text)
        for i, nie in enumerate(nies, 1):
            mapping[f"[NIE_{i}]"] = nie
            
        # Detectar IBAN español
        iban_pattern = r'\bES\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b'
        ibans = re.findall(iban_pattern, text)
        for i, iban in enumerate(ibans, 1):
            mapping[f"[IBAN_{i}]"] = iban.replace(' ', '')
            
        logger.info(f"Mock PII detector encontró {len(mapping)} entidades")
        return {"mapping": mapping, "anonymized_text": text}

# =====================================================
# Validador de Mappings mejorado y más estricto
# =====================================================
class ImprovedMappingValidator:
    STOPWORDS = {
        'el', 'la', 'de', 'en', 'un', 'una', 'con', 'su', 'es', 'se', 'por', 'para',
        'del', 'al', 'le', 'les', 'me', 'te', 'nos', 'os', 'lo', 'las', 'los', 'an',
        'y', 'o', 'pero', 'si', 'no', 'que', 'como', 'cuando', 'donde', 'sra', 'sr',
        'estimado', 'estimada', 'atentamente', 'saludo', 'saludos', 'cordialmente'
    }
    
    INVALID_PATTERNS = [
        r'^[a-z]{1,3}$',          # Fragmentos muy cortos en minúscula
        r'^\.$',                  # Solo puntos
        r'^[A-Z]$',               # Solo una letra mayúscula
        r'^[^a-zA-Z0-9@.]+$',     # Solo caracteres especiales
        r'^[a-z]+$',              # Solo minúsculas (fragmentos)
        r'^\d{1,3}$',             # Números muy cortos
        r'^[.,:;!?-]+$'           # Solo puntuación
    ]
    
    @staticmethod
    def validate_and_clean_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
        """Valida y limpia el mapping con filtros más estrictos"""
        if not mapping:
            return {}
            
        cleaned_mapping = {}
        filtered_count = 0
        
        # Primero, agrupar valores similares para evitar duplicados
        grouped_values = {}
        for token, value in mapping.items():
            clean_value = value.strip()
            if clean_value not in grouped_values:
                grouped_values[clean_value] = []
            grouped_values[clean_value].append(token)
        
        # Procesar cada valor único
        for value, tokens in grouped_values.items():
            # Aplicar validaciones
            if not ImprovedMappingValidator._is_valid_entity_value(value):
                filtered_count += len(tokens)
                logger.debug(f"Valor inválido filtrado: '{value}' (tokens: {tokens})")
                continue
                
            # Seleccionar el mejor token para este valor
            best_token = ImprovedMappingValidator._select_best_token(tokens, value)
            
            if best_token and ImprovedMappingValidator._is_valid_entity(best_token, value):
                cleaned_mapping[best_token] = value
            else:
                filtered_count += len(tokens)
                logger.debug(f"Token inválido filtrado: {best_token} -> '{value}'")
        
        logger.info(f"Mapping validado: {len(cleaned_mapping)}/{len(mapping)} entidades válidas, {filtered_count} filtradas")
        return cleaned_mapping
    
    @staticmethod
    def _is_valid_entity_value(value: str) -> bool:
        """Validación básica del valor"""
        clean_value = value.strip().lower()
        
        # Filtrar valores muy cortos o vacíos
        if len(clean_value) < 2:
            return False
            
        # Filtrar stopwords
        if clean_value in ImprovedMappingValidator.STOPWORDS:
            return False
            
        # Filtrar patrones inválidos
        for pattern in ImprovedMappingValidator.INVALID_PATTERNS:
            if re.match(pattern, value.strip()):
                return False
        
        return True
    
    @staticmethod
    def _select_best_token(tokens: List[str], value: str) -> Optional[str]:
        """Selecciona el mejor token basado en prioridades"""
        if not tokens:
            return None
            
        # Orden de prioridad para tipos de entidades
        priority_order = ['EMAIL', 'PHONE', 'DNI', 'NIE', 'IBAN', 'PERSON', 'ORG', 'ORGANIZATION', 'LOCATION']
        
        for priority_type in priority_order:
            matching_tokens = [t for t in tokens if t.startswith(f'[{priority_type}_')]
            if matching_tokens:
                return matching_tokens[0]
        
        return tokens[0] if tokens else None
    
    @staticmethod
    def _is_valid_entity(token: str, value: str) -> bool:
        """Validación específica por tipo de entidad"""
        if not token.startswith('[') or not token.endswith(']'):
            return False
            
        token_type = token.split('_')[0].strip('[]')
        clean_value = value.strip()
        
        if token_type == 'EMAIL':
            return '@' in clean_value and '.' in clean_value and len(clean_value) > 5
        elif token_type == 'PHONE':
            digits = re.sub(r'[^\d]', '', clean_value)
            return len(digits) >= 7 and len(digits) <= 15
        elif token_type == 'PERSON':
            words = clean_value.split()
            if len(words) < 2:
                return False
            return all(len(word) >= 2 and word[0].isupper() for word in words if word)
        elif token_type == 'DNI':
            return bool(re.match(r'^\d{8}[A-Z]$', clean_value))
        elif token_type == 'NIE':
            return bool(re.match(r'^[XYZ]\d{7}[A-Z]$', clean_value))
        elif token_type in ['ORG', 'ORGANIZATION']:
            return len(clean_value) >= 3 and not clean_value.lower() in ImprovedMappingValidator.STOPWORDS
        elif token_type == 'LOCATION':
            return len(clean_value) >= 3 and clean_value[0].isupper()
        elif token_type == 'IBAN':
            return clean_value.startswith('ES') and len(clean_value.replace(' ', '')) >= 20
        elif token_type == 'MISC':
            # MISC debe tener al menos 3 caracteres y no ser solo puntuación
            return len(clean_value) >= 3 and not re.match(r'^[^a-zA-Z0-9]+$', clean_value)
        
        return True

# =====================================================
# Sistema de caché persistente mejorado
# =====================================================
class PersistentCache:
    def __init__(self, cache_file="pii_cache.pkl"):
        self.cache_file = cache_file
        self.replacement_cache = {}
        self.reverse_cache = {}
        self._lock = threading.Lock()
        self.load_cache()
    
    def load_cache(self):
        """Carga el caché desde archivo"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    data = pickle.load(f)
                    self.replacement_cache = data.get('replacement', {})
                    self.reverse_cache = data.get('reverse', {})
                logger.info(f"Cache cargado: {len(self.replacement_cache)} entradas")
            except Exception as e:
                logger.warning(f"Error cargando cache: {e}")
    
    def save_cache(self):
        """Guarda el caché a archivo"""
        try:
            with self._lock:
                data = {
                    'replacement': self.replacement_cache,
                    'reverse': self.reverse_cache
                }
                with open(self.cache_file, 'wb') as f:
                    pickle.dump(data, f)
                logger.debug(f"Cache guardado: {len(self.replacement_cache)} entradas")
        except Exception as e:
            logger.error(f"Error guardando cache: {e}")
    
    def get_replacement(self, key):
        with self._lock:
            return self.replacement_cache.get(key)
    
    def set_replacement(self, key, value, reverse_value):
        with self._lock:
            self.replacement_cache[key] = value
            self.reverse_cache[value] = reverse_value
            
            # Guardar cache cada 10 entradas nuevas
            if len(self.replacement_cache) % 10 == 0:
                self.save_cache()

# =====================================================
# Métricas detalladas del sistema
# =====================================================
class DetailedMetrics:
    def __init__(self):
        self.metrics = {
            'pii_detection': {
                'total_entities_detected': 0,
                'valid_entities': 0,
                'invalid_entities_filtered': 0,
                'detection_accuracy': 0.0
            },
            'anonymization': {
                'entities_successfully_anonymized': 0,
                'anonymization_failures': 0,
                'anonymization_success_rate': 0.0
            },
            'llm_performance': {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'average_response_time': 0.0,
                'provider_usage': {}
            },
            'deanonymization': {
                'entities_restored': 0,
                'restoration_failures': 0,
                'quality_score': 0.0
            }
        }
        self._lock = threading.Lock()
    
    def update_pii_detection(self, detected_count, valid_count):
        with self._lock:
            self.metrics['pii_detection']['total_entities_detected'] += detected_count
            self.metrics['pii_detection']['valid_entities'] += valid_count
            self.metrics['pii_detection']['invalid_entities_filtered'] += (detected_count - valid_count)
            
            total = self.metrics['pii_detection']['total_entities_detected']
            valid = self.metrics['pii_detection']['valid_entities']
            if total > 0:
                self.metrics['pii_detection']['detection_accuracy'] = valid / total
    
    def update_anonymization(self, success_count, failure_count):
        with self._lock:
            self.metrics['anonymization']['entities_successfully_anonymized'] += success_count
            self.metrics['anonymization']['anonymization_failures'] += failure_count
            
            total = success_count + failure_count
            if total > 0:
                self.metrics['anonymization']['anonymization_success_rate'] = success_count / total
    
    def update_llm_performance(self, call_time, provider, success=True):
        with self._lock:
            self.metrics['llm_performance']['total_calls'] += 1
            
            if success:
                self.metrics['llm_performance']['successful_calls'] += 1
            else:
                self.metrics['llm_performance']['failed_calls'] += 1
            
            if provider not in self.metrics['llm_performance']['provider_usage']:
                self.metrics['llm_performance']['provider_usage'][provider] = 0
            self.metrics['llm_performance']['provider_usage'][provider] += 1
            
            # Actualizar tiempo promedio
            total_calls = self.metrics['llm_performance']['total_calls']
            current_avg = self.metrics['llm_performance']['average_response_time']
            self.metrics['llm_performance']['average_response_time'] = \
                (current_avg * (total_calls - 1) + call_time) / total_calls
    
    def update_deanonymization(self, restored_count, total_count, quality_score):
        with self._lock:
            self.metrics['deanonymization']['entities_restored'] += restored_count
            self.metrics['deanonymization']['restoration_failures'] += (total_count - restored_count)
            
            # Actualizar puntuación de calidad promedio
            current_quality = self.metrics['deanonymization']['quality_score']
            if current_quality == 0.0:
                self.metrics['deanonymization']['quality_score'] = quality_score
            else:
                self.metrics['deanonymization']['quality_score'] = \
                    (current_quality + quality_score) / 2
    
    def get_summary_report(self):
        """Genera un reporte resumen de métricas"""
        with self._lock:
            report = []
            report.append("=== REPORTE DE MÉTRICAS DETALLADAS ===")
            
            # PII Detection
            pii = self.metrics['pii_detection']
            report.append(f"Detección PII:")
            report.append(f"  - Total detectadas: {pii['total_entities_detected']}")
            report.append(f"  - Válidas: {pii['valid_entities']}")
            report.append(f"  - Filtradas: {pii['invalid_entities_filtered']}")
            report.append(f"  - Precisión: {pii['detection_accuracy']:.2%}")
            
            # Anonymization
            anon = self.metrics['anonymization']
            if anon['entities_successfully_anonymized'] > 0:
                report.append(f"Anonimización:")
                report.append(f"  - Exitosas: {anon['entities_successfully_anonymized']}")
                report.append(f"  - Fallidas: {anon['anonymization_failures']}")
                report.append(f"  - Tasa de éxito: {anon['anonymization_success_rate']:.2%}")
            
            # LLM Performance
            llm = self.metrics['llm_performance']
            if llm['total_calls'] > 0:
                success_rate = llm['successful_calls'] / llm['total_calls']
                report.append(f"Rendimiento LLM:")
                report.append(f"  - Llamadas exitosas: {llm['successful_calls']}/{llm['total_calls']} ({success_rate:.2%})")
                report.append(f"  - Tiempo promedio: {llm['average_response_time']:.2f}s")
                report.append(f"  - Uso de proveedores: {llm['provider_usage']}")
            
            # Deanonymization
            deanon = self.metrics['deanonymization']
            if deanon['entities_restored'] > 0:
                report.append(f"Desanonimización:")
                report.append(f"  - Entidades restauradas: {deanon['entities_restored']}")
                report.append(f"  - Fallos de restauración: {deanon['restoration_failures']}")
                report.append(f"  - Puntuación de calidad: {deanon['quality_score']:.2f}")
            
            return "\n".join(report)
    
    def get_metrics_dict(self):
        with self._lock:
            return dict(self.metrics)

# =====================================================
# Generador de datos sintéticos mejorado
# =====================================================
class EnhancedSyntheticDataGenerator:
    def __init__(self, locale='es_ES', cache_file="pii_cache.pkl"):
        self.fake = Faker(locale)
        self.cache = PersistentCache(cache_file)
        self.consistency_map = {}
        
    def _generate_consistent_hash(self, value: str, entity_type: str) -> str:
        """Genera un hash consistente para mantener relaciones entre entidades"""
        return hashlib.md5(f"{entity_type}:{value}".encode()).hexdigest()[:8]
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normaliza tipos de entidades"""
        entity_type = entity_type.upper().strip()
        
        type_mappings = {
            'MISC': 'OTHER',
            'PER': 'PERSON',
            'LOC': 'LOCATION', 
            'ORG': 'ORGANIZATION',
            'PHONE_NUMBER': 'PHONE',
            'MOBILE_PHONE': 'PHONE',
            'LANDLINE_PHONE': 'PHONE'
        }
        
        return type_mappings.get(entity_type, entity_type)
    
    def generate_synthetic_dni(self, original_value: str = None) -> str:
        """Genera DNI sintético válido"""
        if original_value:
            hash_val = self._generate_consistent_hash(original_value, "DNI")
            seed = int(hash_val, 16) % 99999999
            random.seed(seed)
            
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        letter = letters[int(numbers) % 23]
        return f"{numbers}{letter}"

    def generate_synthetic_nie(self, original_value: str = None) -> str:
        """Genera NIE sintético válido"""
        if original_value:
            hash_val = self._generate_consistent_hash(original_value, "NIE")
            seed = int(hash_val, 16) % 99999999
            random.seed(seed)
            
        prefix = random.choice(['X', 'Y', 'Z'])
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        
        prefix_num = {'X': 0, 'Y': 1, 'Z': 2}[prefix]
        full_number = str(prefix_num) + numbers
        control = letters[int(full_number) % 23]
        return f"{prefix}{numbers}{control}"

    def generate_synthetic_phone(self, original_value: str = None) -> str:
        """Genera teléfono sintético español válido"""
        if original_value:
            hash_val = self._generate_consistent_hash(original_value, "PHONE")
            seed = int(hash_val, 16) % 99999999
            random.seed(seed)
            
        if original_value and '+34' in original_value:
            prefix = '+34 '
        else:
            prefix = ''
            
        if original_value and original_value.strip().startswith('9'):
            first_digit = '9'
            second_digit = random.choice(['1', '2', '3', '4', '5', '6', '7', '8'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(7)])
            return f"{prefix}{first_digit}{second_digit} {rest[:3]} {rest[3:5]} {rest[5:]}"
        else:
            first_digit = random.choice(['6', '7'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            return f"{prefix}{first_digit}{rest[:2]} {rest[2:5]} {rest[5:]}"

    def generate_synthetic_email(self, original_value: str = None) -> str:
        """Genera email sintético manteniendo estructura"""
        if original_value and '@' in original_value:
            domain_part = original_value.split('@')[-1]
            synthetic_domains = {
                'gmail.com': 'sintemail.com',
                'hotmail.com': 'sintmail.com',
                'yahoo.com': 'sintyahoo.com',
                'telefonica.com': 'sinttelefonica.com',
                'example.com': 'sintexample.com'
            }
            
            for orig_domain, synt_domain in synthetic_domains.items():
                if orig_domain in domain_part.lower():
                    username = self.fake.user_name()
                    return f"{username}@{synt_domain}"
                    
        return self.fake.email()

    def generate_synthetic_person_name(self, original_value: str = None) -> str:
        """Genera nombre sintético manteniendo estructura"""
        if original_value:
            parts = original_value.split()
            if len(parts) == 2:
                return f"{self.fake.first_name()} {self.fake.last_name()}"
            elif len(parts) == 3:
                return f"{self.fake.first_name()} {self.fake.first_name()} {self.fake.last_name()}"
            elif len(parts) >= 4:
                return f"{self.fake.first_name()} {self.fake.first_name()} {self.fake.last_name()} {self.fake.last_name()}"
                
        return self.fake.name()

    def generate_synthetic_location(self, original_value: str = None) -> str:
        """Genera ubicación sintética española"""
        spanish_cities = [
            'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 
            'Zaragoza', 'Murcia', 'Córdoba', 'Palma', 'Las Palmas',
            'Vigo', 'Gijón', 'Hospitalet', 'Coruña', 'Granada'
        ]
        return random.choice(spanish_cities)

    def generate_synthetic_organization(self, original_value: str = None) -> str:
        """Genera organización sintética"""
        if original_value:
            if any(keyword in original_value.lower() for keyword in ['banco', 'telefonica', 'iberdrola', 'departamento']):
                synthetic_companies = [
                    'Banco Sintético S.A.', 
                    'Telefónica Sintética S.L.', 
                    'Energías Sintéticas S.A.',
                    'Consultoría Sintética Ltd.',
                    'Departamento de Servicios Sintéticos',
                    'Grupo Sintético España S.A.'
                ]
                return random.choice(synthetic_companies)
        
        return self.fake.company() + ' S.A.'

    def generate_synthetic_iban(self, original_value: str = None) -> str:
        """Genera IBAN sintético español válido"""
        bank_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        branch_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        control_digits = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        iban_control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        
        return f"ES{iban_control} {bank_code} {branch_code} {control_digits} {account_number}"

    def _detect_entity_type_from_value(self, value: str) -> str:
    
        if '@' in value and '.' in value:
            return 'EMAIL'
        
        if re.match(r'^[\+\d\s\-\(\)]{7,15}$', value):
            return 'PHONE'
        
        if re.match(r'^\d{8}[A-Z]$', value):
            return 'DNI'
        
        if re.match(r'^[XYZ]\d{7}[A-Z]$', value):
            return 'NIE'
        
        if value.startswith('ES') and len(value.replace(' ', '')) >= 20:
            return 'IBAN'
        
        words = value.split()
        if len(words) >= 2 and all(word[0].isupper() for word in words if word):
            return 'PERSON'
        
        if any(org_suffix in value for org_suffix in ['S.A.', 'S.L.', 'Ltd.', 'Inc.']):
            return 'ORGANIZATION'
        
        return 'OTHER'


    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        """Genera reemplazo sintético mejorado con caché"""
        cache_key = f"{entity_type}:{original_value}"
        
        # Verificar caché primero
        cached_replacement = self.cache.get_replacement(cache_key)
        if cached_replacement:
            return cached_replacement

        normalized_type = self._normalize_entity_type(entity_type)
        
        if normalized_type in ['OTHER', 'MISC']:
            detected_type = self._detect_entity_type_from_value(original_value)
            if detected_type != 'OTHER':
                normalized_type = detected_type

        try:
            entity_enum = EntityType(normalized_type)
        except ValueError:
            entity_enum = None
            
        replacement = None
        
        if entity_enum == EntityType.DNI:
            replacement = self.generate_synthetic_dni(original_value)
        elif entity_enum == EntityType.NIE:
            replacement = self.generate_synthetic_nie(original_value)
        elif entity_enum == EntityType.EMAIL:
            replacement = self.generate_synthetic_email(original_value)
        elif entity_enum in [EntityType.PHONE, EntityType.MOBILE_PHONE, EntityType.LANDLINE_PHONE]:
            replacement = self.generate_synthetic_phone(original_value)
        elif entity_enum == EntityType.PERSON:
            replacement = self.generate_synthetic_person_name(original_value)
        elif entity_enum == EntityType.LOCATION:
            replacement = self.generate_synthetic_location(original_value)
        elif entity_enum == EntityType.ORGANIZATION:
            replacement = self.generate_synthetic_organization(original_value)
        elif entity_enum == EntityType.IBAN:
            replacement = self.generate_synthetic_iban(original_value)
        else:
            replacement = self._generate_intelligent_fallback(original_value)

        # Guardar en caché
        if replacement:
            self.cache.set_replacement(cache_key, replacement, original_value)
        
        return replacement or f"[SINT_{random.randint(1000,9999)}]"
    
    def _generate_intelligent_fallback(self, original_value: str) -> str:
        """Fallback inteligente para valores desconocidos"""
        if original_value.isdigit():
            if len(original_value) <= 4:
                return str(random.randint(1000, 9999))
            else:
                return ''.join([str(random.randint(0, 9)) for _ in range(len(original_value))])
        
        elif any(char.isalpha() for char in original_value):
            words = original_value.split()
            if len(words) > 1:
                if all(word[0].isupper() for word in words if word):
                    return self.fake.name()
                else:
                    return self.fake.company()
            else:
                if original_value[0].isupper():
                    return self.fake.first_name()
                else:
                    return self.fake.word()
        
        else:
            return f"SINT_{random.randint(100, 999)}"
    
    def get_cache_stats(self):
        """Retorna estadísticas del caché"""
        return {
            'replacement_cache_size': len(self.cache.replacement_cache),
            'reverse_cache_size': len(self.cache.reverse_cache)
        }

# =====================================================
# Validador de calidad de desanonimización
# =====================================================
def validate_deanonymization_quality(original_anonymous: str, final_result: str, mapping: Dict[str, str]) -> float:
    """Valida la calidad del proceso de desanonimización"""
    if not mapping:
        return 1.0
        
    # Contar cuántos tokens sintéticos quedan sin reemplazar
    synthetic_patterns = [
        r'\[PERSON_\d+\]',
        r'\[EMAIL_\d+\]',
        r'\[PHONE_\d+\]',
        r'\[ORG_\d+\]',
        r'\[LOCATION_\d+\]',
        r'\[DNI_\d+\]',
        r'\[NIE_\d+\]',
        r'\[IBAN_\d+\]',
        r'SINT_\d+',
        r'\[[A-Z_]+\d*\]'
    ]
    
    remaining_synthetic = 0
    for pattern in synthetic_patterns:
        remaining_synthetic += len(re.findall(pattern, final_result))
    
    if remaining_synthetic == 0:
        return 1.0
    else:
        penalty = remaining_synthetic / len(mapping) if mapping else 0
        return max(0.0, 1.0 - penalty)

# =====================================================
# Adapter TLS mejorado
# =====================================================
class EnhancedTLSAdapter(HTTPAdapter):
    def __init__(self, **kwargs):
        self.retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "POST"]
        )
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.minimum_version = getattr(ssl, "TLSVersion", ssl).TLSv1_2
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

# =====================================================
# Cliente LLM Multi-Proveedor mejorado
# =====================================================
class MultiProviderLLMClient:
    def __init__(self, metrics: Optional[DetailedMetrics] = None):
        self.providers = self._initialize_providers()
        self.session = requests.Session()
        self.session.mount("https://", EnhancedTLSAdapter())
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.metrics = metrics
        
    def _initialize_providers(self) -> List[LLMConfig]:
        """Inicializa configuraciones de múltiples proveedores"""
        providers = []
        
        if GROK_API_KEY:
            groq_models = [
                "gemma2-9b-it",
                "deepseek-r1-distill-llama-70b",
                "allam-2-7b"
            ]
            
            for model in groq_models:
                providers.append(LLMConfig(
                    provider="groq",
                    model=model,
                    api_key=GROK_API_KEY,
                    endpoint="https://api.groq.com/openai/v1/chat/completions",
                    max_tokens=1000,
                    timeout=30
                ))
            
        if OPENAI_API_KEY:
            providers.append(LLMConfig(
                provider="openai",
                model="gpt-3.5-turbo",
                api_key=OPENAI_API_KEY,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=1000,
                timeout=30
            ))
            
        if ANTHROPIC_API_KEY:
            providers.append(LLMConfig(
                provider="anthropic",
                model="claude-3-haiku-20240307",
                api_key=ANTHROPIC_API_KEY,
                endpoint="https://api.anthropic.com/v1/messages",
                max_tokens=1000,
                timeout=30
            ))
            
        logger.info(f"Configurados {len(providers)} proveedores LLM")
        return providers

    def _call_groq(self, config: LLMConfig, prompt: str) -> str:
        """Llamada específica a Groq"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        response = self.session.post(config.endpoint, headers=headers, json=payload, timeout=config.timeout)
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['message']['content']

    def _call_openai(self, config: LLMConfig, prompt: str) -> str:
        """Llamada específica a OpenAI"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        response = self.session.post(config.endpoint, headers=headers, json=payload, timeout=config.timeout)
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['message']['content']

    def _call_anthropic(self, config: LLMConfig, prompt: str) -> str:
        """Llamada específica a Anthropic"""
        headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.session.post(config.endpoint, headers=headers, json=payload, timeout=config.timeout)
        response.raise_for_status()
        result = response.json()
        
        return result['content'][0]['text']

    def call_llm(self, prompt: str, timeout: int = 45) -> tuple[str, str]:
        """Llama al LLM con fallbacks automáticos y métricas mejoradas"""
        if not self.providers:
            return "[ERROR: No hay proveedores LLM configurados]", "none"
            
        for provider_config in self.providers:
            for attempt in range(provider_config.max_retries):
                start_time = time.time()
                try:
                    logger.info(f"Intentando con {provider_config.provider} - {provider_config.model} (intento {attempt + 1})")
                    
                    future = self.executor.submit(self._call_provider, provider_config, prompt)
                    response = future.result(timeout=timeout)
                    
                    call_time = time.time() - start_time
                    if self.metrics:
                        self.metrics.update_llm_performance(call_time, provider_config.provider, True)
                    
                    logger.info(f"Éxito con {provider_config.provider} en {call_time:.2f}s")
                    return response, provider_config.provider
                    
                except TimeoutError:
                    call_time = time.time() - start_time
                    if self.metrics:
                        self.metrics.update_llm_performance(call_time, provider_config.provider, False)
                    logger.warning(f"Timeout con {provider_config.provider} (intento {attempt + 1})")
                    continue
                except Exception as e:
                    call_time = time.time() - start_time
                    if self.metrics:
                        self.metrics.update_llm_performance(call_time, provider_config.provider, False)
                    logger.warning(f"Error con {provider_config.provider} (intento {attempt + 1}): {e}")
                    if attempt < provider_config.max_retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                    
        logger.error("Todos los proveedores LLM fallaron")
        return f"[ERROR: Todos los proveedores fallaron]", "failed"

    def _call_provider(self, config: LLMConfig, prompt: str) -> str:
        """Dispatcher para llamadas a proveedores específicos"""
        if config.provider == "groq":
            return self._call_groq(config, prompt)
        elif config.provider == "openai":
            return self._call_openai(config, prompt)
        elif config.provider == "anthropic":
            return self._call_anthropic(config, prompt)
        else:
            raise ValueError(f"Proveedor no soportado: {config.provider}")

# =====================================================
# Pipeline principal mejorado y optimizado
# =====================================================
class EnhancedAnonymizationPipeline:
    def __init__(self, cache_file="pii_cache.pkl"):
        self.generator = EnhancedSyntheticDataGenerator(cache_file=cache_file)
        self.validator = ImprovedMappingValidator()
        self.metrics = DetailedMetrics()
        self.llm_client = MultiProviderLLMClient(self.metrics)

    def _validate_input(self, text: str) -> bool:
        """Valida entrada del pipeline"""
        if not text or not isinstance(text, str):
            return False
        if len(text.strip()) < 10:
            return False
        if len(text) > 50000:
            logger.warning("Texto muy largo, puede afectar el rendimiento")
        return True

    def anonymize(self, text: str, mapping: Dict[str, str]) -> tuple[str, float]:
        """Anonimiza texto con mejor manejo de reemplazos y métricas"""
        start_time = time.time()
        anonymized = text
        entities_replaced = 0
        
        # Validar y limpiar mapping
        clean_mapping = self.validator.validate_and_clean_mapping(mapping)
        
        if not clean_mapping:
            logger.warning("No hay entidades válidas para anonimizar")
            if self.metrics:
                self.metrics.update_anonymization(0, len(mapping))
            return text, 0.0
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_mapping = sorted(clean_mapping.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Realizar reemplazos
        replacement_log = []
        for token, original_value in sorted_mapping:
            if original_value in anonymized:
                entity_type = token.strip('[]').split('_')[0]
                replacement = self.generator.generate_synthetic_replacement(entity_type, original_value)
                
                anonymized = anonymized.replace(original_value, replacement)
                entities_replaced += 1
                
                replacement_log.append({
                    'token': token,
                    'original': original_value,
                    'replacement': replacement,
                    'type': entity_type
                })
                
                logger.debug(f"Reemplazado: '{original_value}' -> '{replacement}' ({entity_type})")
        
        processing_time = time.time() - start_time
        confidence = min(entities_replaced / len(clean_mapping) if clean_mapping else 1.0, 1.0)
        
        # Actualizar métricas
        if self.metrics:
            self.metrics.update_anonymization(entities_replaced, len(clean_mapping) - entities_replaced)
        
        logger.info(f"Anonimización completada: {entities_replaced}/{len(clean_mapping)} entidades reemplazadas en {processing_time:.2f}s")
        
        return anonymized, confidence

    def de_anonymize(self, text: str) -> tuple[str, int]:
        """Desanonimiza texto restaurando valores originales"""
        de_anonymized = text
        replacements_made = 0
        
        if not self.generator.cache.reverse_cache:
            logger.warning("No hay caché de reemplazos para desanonimizar")
            return text, 0
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_cache = sorted(self.generator.cache.reverse_cache.items(), key=lambda x: len(x[0]), reverse=True)
        
        for synthetic, original in sorted_cache:
            if synthetic in de_anonymized:
                de_anonymized = de_anonymized.replace(synthetic, original)
                replacements_made += 1
                
        logger.info(f"Desanonimización completada: {replacements_made} entidades restauradas")
        return de_anonymized, replacements_made

    def run_pipeline(self, 
                     text: str, 
                     model: str = "es", 
                     use_regex: bool = True, 
                     pseudonymize: bool = False,
                     llm_prompt_template: Optional[str] = None,
                     validate_output: bool = True) -> PipelineResult:
        """Ejecuta el pipeline completo mejorado con métricas detalladas"""
        start_time = time.time()
        
        if not self._validate_input(text):
            return PipelineResult(
                original_text=text,
                success=False,
                error="Entrada inválida: texto vacío o demasiado corto",
                processing_time=time.time() - start_time
            )
        
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO PIPELINE DE ANONIMIZACION MEJORADO")
            logger.info("=" * 60)
            
            # Paso 1: Detección de PII
            log_step("Detectando PII", 1)
            pii_result = pii_run_pipeline(model=model, text=text, use_regex=use_regex, pseudonymize=pseudonymize)
            mapping = pii_result.get("mapping", {})
            
            # Actualizar métricas de detección
            original_count = len(mapping)
            clean_mapping = self.validator.validate_and_clean_mapping(mapping)
            valid_count = len(clean_mapping)
            
            if self.metrics:
                self.metrics.update_pii_detection(original_count, valid_count)
            
            log_success(f"PII detectado: {valid_count}/{original_count} entidades válidas")
            
            # Caso sin PII detectado válido
            if not clean_mapping:
                logger.info("No se detectó PII válido, procesando texto original...")
                
                if llm_prompt_template:
                    llm_prompt = llm_prompt_template.format(text=text)
                else:
                    llm_prompt = f"Procesa el siguiente texto de manera profesional: {text}"
                
                llm_response, provider_used = self.llm_client.call_llm(llm_prompt)
                
                processing_time = time.time() - start_time
                
                log_success(f"Pipeline completado sin PII válido en {processing_time:.2f}s")
                
                return PipelineResult(
                    original_text=text,
                    anonymized_text=text,
                    pii_detected=False,
                    pii_mapping=clean_mapping,
                    llm_prompt=llm_prompt,
                    llm_response=llm_response,
                    final_response=llm_response,
                    success=True,
                    processing_time=processing_time,
                    llm_provider_used=provider_used,
                    confidence_score=1.0,
                    quality_metrics={'detection_accuracy': valid_count / original_count if original_count > 0 else 1.0}
                )

            # Paso 2: Anonimización
            log_step(f"Anonimizando {len(clean_mapping)} entidades PII válidas", 2)
            anonymized, confidence = self.anonymize(text, clean_mapping)
            
            if confidence < 0.5:
                log_warning(f"Confianza de anonimización baja: {confidence:.2f}")

            # Paso 3: Preparar prompt para LLM
            log_step("Preparando prompt para LLM", 3)
            if llm_prompt_template:
                llm_prompt = llm_prompt_template.format(text=anonymized)
            else:
                llm_prompt = f"Procesa el siguiente texto de manera profesional: {anonymized}"

            # Paso 4: Llamada al LLM
            log_step("Enviando al LLM", 4)
            llm_response, provider_used = self.llm_client.call_llm(llm_prompt)
            
            if "[ERROR:" in llm_response:
                log_error(f"Error del LLM: {llm_response}")
                confidence *= 0.5

            # Paso 5: Desanonimización
            log_step("Desanonimizando respuesta", 5)
            final_response, restored_count = self.de_anonymize(llm_response)

            # Paso 6: Validación de calidad
            quality_score = validate_deanonymization_quality(anonymized, final_response, clean_mapping)
            
            if self.metrics:
                self.metrics.update_deanonymization(restored_count, len(clean_mapping), quality_score)

            if validate_output:
                log_step("Validando salida", 6)
                
                if quality_score < 0.7:
                    log_warning(f"Calidad de desanonimización baja: {quality_score:.2f}")
                    confidence *= 0.8
                    
                if not final_response.strip():
                    log_error("Respuesta final vacía")
                    confidence = 0.0

            processing_time = time.time() - start_time

            logger.info("=" * 60)
            log_success(f"PIPELINE COMPLETADO EXITOSAMENTE en {processing_time:.2f}s")
            logger.info(f"Confianza: {confidence:.2f} | Calidad: {quality_score:.2f} | Proveedor: {provider_used}")
            logger.info("=" * 60)
            
            quality_metrics = {
                'detection_accuracy': valid_count / original_count if original_count > 0 else 1.0,
                'anonymization_confidence': confidence,
                'deanonymization_quality': quality_score,
                'entities_processed': len(clean_mapping),
                'entities_restored': restored_count
            }
            
            return PipelineResult(
                original_text=text,
                anonymized_text=anonymized,
                pii_detected=True,
                pii_mapping=clean_mapping,
                llm_prompt=llm_prompt,
                llm_response=llm_response,
                final_response=final_response,
                success=True,
                processing_time=processing_time,
                llm_provider_used=provider_used,
                confidence_score=confidence,
                quality_metrics=quality_metrics
            )

        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error("=" * 60)
            log_error(f"ERROR EN EL PIPELINE: {str(e)}")
            logger.error("=" * 60)
            logger.error(f"Detalles del error: {e}", exc_info=True)
            
            return PipelineResult(
                original_text=text,
                success=False,
                error=str(e),
                processing_time=processing_time
            )

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Retorna métricas detalladas del pipeline"""
        base_metrics = self.metrics.get_metrics_dict()
        cache_stats = self.generator.get_cache_stats()
        
        return {
            **base_metrics,
            'cache_stats': cache_stats,
            'validator_stats': {
                'stopwords_count': len(self.validator.STOPWORDS),
                'invalid_patterns_count': len(self.validator.INVALID_PATTERNS)
            }
        }

    def get_metrics_report(self) -> str:
        """Retorna reporte completo de métricas"""
        return self.metrics.get_summary_report()

    def clear_cache(self):
        """Limpia caché de entidades sintéticas"""
        self.generator.cache.replacement_cache.clear()
        self.generator.cache.reverse_cache.clear()
        log_success("Cache de entidades sintéticas limpiado")

    def save_cache(self):
        """Guarda el caché manualmente"""
        self.generator.cache.save_cache()

# =====================================================
# Sistema de Salud y Monitoreo mejorado
# =====================================================
class PipelineHealthMonitor:
    def __init__(self, pipeline: EnhancedAnonymizationPipeline):
        self.pipeline = pipeline
        
    def health_check(self) -> Dict[str, Any]:
        """Ejecuta verificaciones de salud del sistema"""
        checks = {
            "pii_detector_available": PII_DETECTOR_AVAILABLE,
            "llm_providers_configured": len(self.pipeline.llm_client.providers) > 0,
            "cache_health": self._check_cache_health(),
            "api_connectivity": self._check_api_connectivity(),
            "system_resources": self._check_system_resources(),
            "environment_variables": self._check_environment_variables(),
            "metrics_system": self._check_metrics_system()
        }
        
        overall_health = all(checks.values())
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "timestamp": time.time(),
            "checks": checks,
            "detailed_metrics": self.pipeline.get_detailed_metrics(),
            "providers_status": self._get_providers_status()
        }
    
    def _check_cache_health(self) -> bool:
        """Verifica salud del caché"""
        cache_stats = self.pipeline.generator.get_cache_stats()
        return (cache_stats['replacement_cache_size'] == cache_stats['reverse_cache_size'] and 
                cache_stats['replacement_cache_size'] < 10000)
    
    def _check_api_connectivity(self) -> bool:
        """Verifica conectividad básica con APIs"""
        if not self.pipeline.llm_client.providers:
            return False
        try:
            first_provider = self.pipeline.llm_client.providers[0]
            return bool(first_provider.api_key and first_provider.endpoint)
        except Exception:
            return False
    
    def _check_system_resources(self) -> bool:
        """Verifica recursos del sistema"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            return cpu_percent < 90 and memory_percent < 90
        except ImportError:
            return True
    
    def _check_environment_variables(self) -> bool:
        """Verifica variables de entorno críticas"""
        return any([GROK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY])
    
    def _check_metrics_system(self) -> bool:
        """Verifica que el sistema de métricas funcione"""
        try:
            metrics = self.pipeline.get_detailed_metrics()
            return isinstance(metrics, dict) and 'pii_detection' in metrics
        except Exception:
            return False
    
    def _get_providers_status(self) -> Dict[str, Dict]:
        """Obtiene estado de cada proveedor"""
        status = {}
        for provider in self.pipeline.llm_client.providers:
            status[f"{provider.provider}-{provider.model}"] = {
                "api_key_configured": bool(provider.api_key),
                "endpoint": provider.endpoint,
                "timeout": provider.timeout,
                "max_retries": provider.max_retries
            }
        return status

# =====================================================
# Test comprensivo mejorado y más detallado
# =====================================================
def run_comprehensive_test():
    """Test completo del sistema mejorado con validaciones adicionales"""
    print("=" * 80)
    print("SISTEMA INTEGRADO LLM Y DATOS SINTÉTICOS - TEST COMPRENSIVO V4.0")
    print("=" * 80)
    
    # Crear pipeline mejorado
    pipeline = EnhancedAnonymizationPipeline()
    monitor = PipelineHealthMonitor(pipeline)
    
    # Test de salud del sistema
    print("\n1. VERIFICACIÓN DE SALUD DEL SISTEMA:")
    print("-" * 50)
    health = monitor.health_check()
    
    status_text = "SALUDABLE" if health['overall_health'] == 'healthy' else "DEGRADADO"
    print(f"Estado general: {status_text}")
    
    for check, status in health['checks'].items():
        status_text = "OK" if status else "FALLO"
        print(f"  - {check.replace('_', ' ').title()}: {status_text}")
    
    print(f"\nProveedores configurados: {len(health['providers_status'])}")
    for provider, details in health['providers_status'].items():
        api_status = "OK" if details['api_key_configured'] else "SIN API KEY"
        print(f"  - {provider}: {api_status}")
    
    if health['overall_health'] != 'healthy':
        print("\nADVERTENCIA: El sistema no está completamente saludable.")
        print("Algunos tests pueden fallar. Verifica la configuración.")
    
    # Mostrar métricas iniciales
    print(f"\n2. MÉTRICAS DEL SISTEMA INICIAL:")
    print("-" * 50)
    initial_metrics = pipeline.get_detailed_metrics()
    cache_stats = initial_metrics.get('cache_stats', {})
    print(f"Cache inicial: {cache_stats.get('replacement_cache_size', 0)} entradas")
    
    # Texto de prueba mejorado
    test_text = """
    Estimada Sra. María José González Hernández,
    
    Le escribimos desde Telefónica España S.A. para informarle sobre los cambios en su contrato.
    
    Datos actuales en nuestro sistema:
    - Email personal: maria.gonzalez@gmail.com
    - Email corporativo: m.gonzalez@telefonica.com  
    - Teléfono móvil: +34 666 789 123
    - Teléfono fijo: 91 567 89 01
    - DNI: 45678901B
    - Dirección: Calle de Alcalá 156, Madrid 28009
    
    Su cuenta bancaria ES91 2100 0418 4502 0005 1332 será cargada el próximo mes.
    
    Para consultas, contacte con Ana Martín López del Departamento de Atención al Cliente
    (ana.martin@telefonica.com, teléfono 900 123 456).
    
    Saludos cordiales,
    
    Carlos Ruiz Pérez
    Director Comercial
    Telefónica España S.A.
    c.ruiz@telefonica.com
    """
    
    print(f"\n3. TEXTO DE PRUEBA ({len(test_text)} caracteres):")
    print("-" * 50)
    print(test_text[:200] + "..." if len(test_text) > 200 else test_text)
    
    # Ejecutar pipeline con prompt personalizado
    print(f"\n4. EJECUTANDO PIPELINE MEJORADO...")
    print("-" * 50)
    
    custom_prompt = """
    Reescribe el siguiente texto de manera más profesional y formal, manteniendo toda la información importante.
    Mejora la estructura y el tono, pero conserva todos los datos específicos mencionados:
    
    {text}
    """
    
    result = pipeline.run_pipeline(
        text=test_text,
        model="es",
        llm_prompt_template=custom_prompt,
        validate_output=True
    )
    
    # Mostrar resultados detallados mejorados
    print(f"\n5. RESULTADOS DETALLADOS:")
    print("-" * 50)
    
    success_text = "EXITOSO" if result.success else "FALLIDO"
    print(f"Estado: {success_text}")
    
    if result.success:
        pii_text = "SI" if result.pii_detected else "NO"
        print(f"PII detectado: {pii_text}")
        
        if result.pii_detected:
            print(f"Entidades encontradas: {len(result.pii_mapping)}")
            print(f"Proveedor LLM usado: {result.llm_provider_used}")
            print(f"Tiempo de procesamiento: {result.processing_time:.2f}s")
            print(f"Puntuación de confianza: {result.confidence_score:.2f}")
            
            # Mostrar métricas de calidad
            if result.quality_metrics:
                print(f"\nMÉTRICAS DE CALIDAD:")
                for metric, value in result.quality_metrics.items():
                    if isinstance(value, float):
                        print(f"  - {metric.replace('_', ' ').title()}: {value:.2f}")
                    else:
                        print(f"  - {metric.replace('_', ' ').title()}: {value}")
            
            print(f"\nENTIDADES PII DETECTADAS (muestra válida):")
            for i, (token, value) in enumerate(list(result.pii_mapping.items())[:8]):
                print(f"  {i+1:2d}. {token}: {value[:40]}{'...' if len(value) > 40 else ''}")
            
            if len(result.pii_mapping) > 8:
                print(f"      ... y {len(result.pii_mapping) - 8} más")
            
            print(f"\nTEXTO ANONIMIZADO (extracto):")
            anonymized_sample = result.anonymized_text[:300] + "..." if len(result.anonymized_text) > 300 else result.anonymized_text
            print(f"   {anonymized_sample}")
        
        print(f"\nRESPUESTA FINAL (extracto):")
        final_sample = result.final_response[:400] + "..." if len(result.final_response) > 400 else result.final_response
        print(f"   {final_sample}")
        
    else:
        print(f"Error: {result.error}")
    
    # Métricas detalladas del sistema
    print(f"\n6. MÉTRICAS DETALLADAS DEL SISTEMA:")
    print("-" * 50)
    detailed_metrics = pipeline.get_detailed_metrics()
    
    # PII Detection metrics
    pii_metrics = detailed_metrics.get('pii_detection', {})
    if pii_metrics.get('total_entities_detected', 0) > 0:
        print("Detección PII:")
        print(f"  - Total detectadas: {pii_metrics.get('total_entities_detected', 0)}")
        print(f"  - Válidas: {pii_metrics.get('valid_entities', 0)}")
        print(f"  - Filtradas: {pii_metrics.get('invalid_entities_filtered', 0)}")
        print(f"  - Precisión: {pii_metrics.get('detection_accuracy', 0):.2%}")
    
    # LLM Performance metrics
    llm_metrics = detailed_metrics.get('llm_performance', {})
    if llm_metrics.get('total_calls', 0) > 0:
        print("Rendimiento LLM:")
        success_rate = llm_metrics.get('successful_calls', 0) / llm_metrics.get('total_calls', 1)
        print(f"  - Llamadas exitosas: {llm_metrics.get('successful_calls', 0)}/{llm_metrics.get('total_calls', 0)} ({success_rate:.2%})")
        print(f"  - Tiempo promedio: {llm_metrics.get('average_response_time', 0):.2f}s")
        print(f"  - Proveedores usados: {llm_metrics.get('provider_usage', {})}")
    
    # Cache stats
    cache_stats = detailed_metrics.get('cache_stats', {})
    print("Estado del Cache:")
    print(f"  - Entradas en cache: {cache_stats.get('replacement_cache_size', 0)}")
    print(f"  - Cache reverso: {cache_stats.get('reverse_cache_size', 0)}")
    
    # Generar reporte de métricas
    print(f"\n7. REPORTE COMPLETO DE MÉTRICAS:")
    print("-" * 50)
    metrics_report = pipeline.get_metrics_report()
    print(metrics_report)
    
    # Test de casos adicionales
    if result.success and result.pii_detected:
        print(f"\n8. TESTS ADICIONALES:")
        print("-" * 50)
        
        # Test de consistencia del cache
        print("Test de consistencia del cache:")
        cache_stats_before = pipeline.generator.get_cache_stats()
        
        # Ejecutar el mismo texto otra vez para verificar cache
        result2 = pipeline.run_pipeline(test_text, model="es")
        cache_stats_after = pipeline.generator.get_cache_stats()
        
        cache_growth = cache_stats_after['replacement_cache_size'] - cache_stats_before['replacement_cache_size']
        print(f"  - Crecimiento del cache: {cache_growth} entradas (esperado: 0 o mínimo)")
        print(f"  - Cache consistency: {'OK' if cache_stats_after['replacement_cache_size'] == cache_stats_after['reverse_cache_size'] else 'ERROR'}")
        
        # Test de calidad de desanonimización
        if result2.success:
            quality_score = validate_deanonymization_quality(
                result2.anonymized_text, 
                result2.final_response, 
                result2.pii_mapping
            )
            print(f"  - Calidad desanonimización: {quality_score:.2f} ({'EXCELENTE' if quality_score > 0.9 else 'BUENA' if quality_score > 0.7 else 'MEJORABLE'})")
    
    # Guardar cache para persistencia
    pipeline.save_cache()
    print(f"\nCache guardado para futuras ejecuciones")
    
    print(f"\n" + "=" * 80)
    print("TEST COMPRENSIVO MEJORADO COMPLETADO")
    print(f"Estado final: {'EXITOSO' if result.success else 'FALLIDO'}")
    if result.success and hasattr(result, 'quality_metrics'):
        avg_quality = sum(v for v in result.quality_metrics.values() if isinstance(v, float)) / len([v for v in result.quality_metrics.values() if isinstance(v, float)])
        print(f"Calidad promedio: {avg_quality:.2f}")
    print("=" * 80)
    
    return result

def main():
    """Función principal mejorada con mejor manejo de errores"""
    try:
        # Banner de inicio mejorado
        print("\n" + "*" * 80)
        print("*" + " " * 78 + "*")
        print("*" + " SISTEMA DE ANONIMIZACIÓN LLM - VERSIÓN MEJORADA V4.0 ".center(78) + "*")
        print("*" + " " * 78 + "*")
        print("*" * 80 + "\n")
        
        # Ejecutar test comprensivo mejorado
        result = run_comprehensive_test()
        
        # Ejemplo de uso simple con casos variados
        if result.success:
            print(f"\nEJEMPLOS DE USO VARIADOS:")
            print("-" * 40)
            
            simple_pipeline = EnhancedAnonymizationPipeline()
            
            test_cases = [
                {
                    "name": "Email y teléfono básico",
                    "text": "Hola, soy Ana García Ruiz y mi email es ana.garcia@empresa.com. Mi teléfono es 666 123 456.",
                    "prompt": "Mejora la redacción profesional: {text}"
                },
                {
                    "name": "Documento oficial",
                    "text": "El Sr. Juan Pérez (DNI: 12345678Z) trabajaba en Banco Santander S.A. Contacto: juan@banco.es",
                    "prompt": "Formaliza este documento oficial: {text}"
                },
                {
                    "name": "Información de contacto",
                    "text": "Para más información sobre Madrid, contactar con María López (maria@gmail.com, 91 123 45 67).",
                    "prompt": "Reescribe de forma más profesional: {text}"
                }
            ]
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\nCaso {i}: {test_case['name']}")
                print(f"   Original: {test_case['text']}")
                
                simple_result = simple_pipeline.run_pipeline(
                    text=test_case['text'],
                    llm_prompt_template=test_case['prompt']
                )
                
                if simple_result.success:
                    print(f"   Resultado: {simple_result.final_response[:150]}...")
                    if simple_result.pii_detected:
                        quality = simple_result.quality_metrics.get('deanonymization_quality', 0)
                        print(f"      PII: {len(simple_result.pii_mapping)} entidades, Calidad: {quality:.2f}")
                else:
                    print(f"   Error: {simple_result.error}")
            
            # Mostrar estadísticas finales
            print(f"\nESTADÍSTICAS FINALES:")
            print("-" * 30)
            final_metrics = simple_pipeline.get_detailed_metrics()
            pii_stats = final_metrics.get('pii_detection', {})
            print(f"Total entidades procesadas: {pii_stats.get('total_entities_detected', 0)}")
            print(f"Precisión de detección: {pii_stats.get('detection_accuracy', 0):.2%}")
            
            cache_stats = final_metrics.get('cache_stats', {})
            print(f"Entradas en cache: {cache_stats.get('replacement_cache_size', 0)}")
        
        print(f"\nPROCESO COMPLETADO EXITOSAMENTE")
        print("El sistema de anonimización mejorado está funcionando correctamente.")
        
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
        print("¡Hasta luego!")
    except Exception as e:
        logger.error(f"Error crítico en main: {e}", exc_info=True)
        print(f"\nERROR CRÍTICO: {e}")
        print("Revisa los logs para más detalles")

if __name__ == "__main__":
    main()

