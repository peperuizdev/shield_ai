import random
import os
import sys
import json
import time
import ssl
import hashlib
import re
import locale
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

# =====================================================
# Configuración de logging compatible con Windows
# =====================================================
IS_WINDOWS = sys.platform.startswith('win')
ENCODING = locale.getpreferredencoding()

# Configuración de logging compatible con Windows
if IS_WINDOWS and ENCODING.lower() in ['cp1252', 'windows-1252']:
    # Logging sin emojis para Windows
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('llm_pipeline.log', encoding='utf-8')
        ]
    )
    
    # Definir funciones de logging sin emojis
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
    # Logging con emojis para sistemas Unix/Linux
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('llm_pipeline.log', encoding='utf-8')
        ]
    )
    
    # Funciones de logging con emojis
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

logger = logging.getLogger(__name__)

# =====================================================
# Cargar variables de entorno - CORREGIDO
# =====================================================
def load_environment():
    """Carga variables de entorno de múltiples ubicaciones posibles"""
    # Primero intentar en el directorio actual
    current_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(current_env):
        load_dotenv(dotenv_path=current_env)
        logger.info(f"Loaded .env from: {current_env}")
        return True
    
    # Luego intentar en el directorio padre
    parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(parent_env):
        load_dotenv(dotenv_path=parent_env)
        logger.info(f"Loaded .env from: {parent_env}")
        return True
    
    # Finalmente, intentar la lógica original
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    env_path = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded .env from: {env_path}")
        return True
    
    logger.warning("No .env file found")
    return False

# Cargar variables de entorno
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
        # Filtrar nombres muy comunes que podrían ser falsos positivos
        valid_names = []
        for name in names:
            words = name.split()
            if len(words) >= 2 and all(len(word) >= 3 for word in words):
                if not any(common in name.lower() for common in ['estimado', 'atentamente', 'departamento']):
                    valid_names.append(name)
        
        for i, name in enumerate(valid_names[:3], 1):  # Máximo 3 nombres
            mapping[f"[PERSON_{i}]"] = name
                
        # Detectar teléfonos españoles
        phone_patterns = [
            r'\+34\s?[6-9]\d{2}\s?\d{3}\s?\d{3}',  # +34 formato
            r'\b[6-9]\d{2}\s?\d{3}\s?\d{3}\b',     # Sin +34
            r'\b9[0-9]\s?\d{3}\s?\d{2}\s?\d{2}\b'  # Fijos
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
            
        # Detectar organizaciones (palabras con S.A., S.L., etc.)
        org_pattern = r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]+(?:S\.A\.|S\.L\.|Ltd\.|Inc\.)\b'
        orgs = re.findall(org_pattern, text)
        for i, org in enumerate(orgs, 1):
            mapping[f"[ORG_{i}]"] = org.strip()
            
        # Detectar ciudades españolas comunes
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Zaragoza', 'Málaga', 
                 'Murcia', 'Palma', 'Bilbao', 'Córdoba', 'Alicante', 'Valladolid']
        for city in cities:
            if city in text:
                city_count = len([k for k in mapping.keys() if k.startswith('[LOCATION_')]) + 1
                mapping[f"[LOCATION_{city_count}]"] = city
                
        logger.info(f"Mock PII detector encontró {len(mapping)} entidades")
        return {"mapping": mapping, "anonymized_text": text}

# =====================================================
# Validador de Mappings mejorado
# =====================================================
class MappingValidator:
    STOPWORDS = {
        'el', 'la', 'de', 'en', 'un', 'una', 'con', 'su', 'es', 'se', 'por', 'para',
        'del', 'al', 'le', 'les', 'me', 'te', 'nos', 'os', 'lo', 'las', 'los', 'an'
    }
    
    @staticmethod
    def validate_and_clean_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
        """Valida y limpia el mapping de PII detectado"""
        cleaned_mapping = {}
        
        for token, value in mapping.items():
            # Limpiar valores
            clean_value = value.strip()
            
            # Filtrar valores muy cortos
            if len(clean_value) < 2:
                logger.debug(f"Valor muy corto ignorado: '{clean_value}'")
                continue
                
            # Filtrar stopwords y fragmentos comunes
            if clean_value.lower() in MappingValidator.STOPWORDS:
                logger.debug(f"Stopword ignorada: '{clean_value}'")
                continue
                
            # Filtrar tokens malformados
            if not (token.startswith('[') and token.endswith(']')):
                logger.warning(f"Token malformado ignorado: '{token}'")
                continue
            
            # Validar patrones específicos
            if MappingValidator._is_valid_entity(token, clean_value):
                cleaned_mapping[token] = clean_value
            else:
                logger.debug(f"Entidad inválida ignorada: {token} -> '{clean_value}'")
        
        logger.info(f"Mapping validado: {len(cleaned_mapping)}/{len(mapping)} entidades válidas")
        return cleaned_mapping
    
    @staticmethod
    def _is_valid_entity(token: str, value: str) -> bool:
        """Valida si una entidad es realmente válida según su tipo"""
        token_type = token.split('_')[0].strip('[]')
        
        if token_type == 'EMAIL':
            return '@' in value and '.' in value
        elif token_type == 'PHONE':
            return bool(re.match(r'^[\+\d\s\-\(\)]{7,15}$', value))
        elif token_type == 'PERSON':
            words = value.split()
            return len(words) >= 2 and all(word[0].isupper() for word in words)
        elif token_type == 'DNI':
            return bool(re.match(r'^\d{8}[A-Z]$', value))
        elif token_type == 'NIE':
            return bool(re.match(r'^[XYZ]\d{7}[A-Z]$', value))
        elif token_type == 'IBAN':
            return value.startswith('ES') and len(value.replace(' ', '')) >= 20
        
        return True  # Para otros tipos, aceptar por defecto

# =====================================================
# Generador de datos sintéticos corregido
# =====================================================
class EnhancedSyntheticDataGenerator:
    def __init__(self, locale='es_ES'):
        self.fake = Faker(locale)
        self.replacement_cache = {}
        self.reverse_cache = {}
        self.consistency_map = {}
        
    def _generate_consistent_hash(self, value: str, entity_type: str) -> str:
        """Genera un hash consistente para mantener relaciones entre entidades"""
        return hashlib.md5(f"{entity_type}:{value}".encode()).hexdigest()[:8]
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normaliza tipos de entidades"""
        entity_type = entity_type.upper().strip()
        
        # Mapeo de correcciones comunes
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
            
        # Mantener formato similar al original
        if original_value and '+34' in original_value:
            prefix = '+34 '
        else:
            prefix = ''
            
        # Generar número válido español
        if original_value and original_value.strip().startswith('9'):
            # Teléfono fijo
            first_digit = '9'
            second_digit = random.choice(['1', '2', '3', '4', '5', '6', '7', '8'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(7)])
            return f"{prefix}{first_digit}{second_digit} {rest[:3]} {rest[3:5]} {rest[5:]}"
        else:
            # Teléfono móvil
            first_digit = random.choice(['6', '7'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            return f"{prefix}{first_digit}{rest[:2]} {rest[2:5]} {rest[5:]}"

    def generate_synthetic_email(self, original_value: str = None) -> str:
        """Genera email sintético manteniendo estructura"""
        if original_value and '@' in original_value:
            domain_part = original_value.split('@')[-1]
            # Mantener dominios conocidos pero hacerlos sintéticos
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
            # Mantener tipo de organización similar
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
        # Estructura IBAN española: ES + 2 dígitos + 4 banco + 4 sucursal + 2 control + 10 cuenta
        bank_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        branch_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        control_digits = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        iban_control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        
        return f"ES{iban_control} {bank_code} {branch_code} {control_digits} {account_number}"

    def _detect_entity_type_from_value(self, value: str) -> str:
        """Detecta el tipo de entidad basándose en el valor"""
        # Email
        if '@' in value and '.' in value:
            return 'EMAIL'
        
        # Teléfono
        if re.match(r'^[\+\d\s\-\(\)]{7,15}$', value):
            return 'PHONE'
            
        # DNI
        if re.match(r'^\d{8}[A-Z]$', value):
            return 'DNI'
            
        # NIE
        if re.match(r'^[XYZ]\d{7}[A-Z]$', value):
            return 'NIE'
            
        # IBAN
        if value.startswith('ES') and len(value.replace(' ', '')) >= 20:
            return 'IBAN'
            
        # Nombre (múltiples palabras con mayúscula)
        words = value.split()
        if len(words) >= 2 and all(word[0].isupper() for word in words if word):
            return 'PERSON'
            
        # Organización (contiene S.A., S.L., etc.)
        if any(org_suffix in value for org_suffix in ['S.A.', 'S.L.', 'Ltd.', 'Inc.']):
            return 'ORGANIZATION'
            
        return 'OTHER'

    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        """Genera reemplazo sintético mejorado"""
        cache_key = f"{entity_type}:{original_value}"
        
        if cache_key in self.replacement_cache:
            return self.replacement_cache[cache_key]

        # Normalizar tipo
        normalized_type = self._normalize_entity_type(entity_type)
        
        # Si el tipo normalizado no es útil, detectar desde el valor
        if normalized_type in ['OTHER', 'MISC']:
            detected_type = self._detect_entity_type_from_value(original_value)
            if detected_type != 'OTHER':
                normalized_type = detected_type

        # Generar reemplazo según tipo
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
            # Fallback inteligente
            replacement = self._generate_intelligent_fallback(original_value)

        # Guardar en caché
        if replacement:
            self.replacement_cache[cache_key] = replacement
            self.reverse_cache[replacement] = original_value
        
        return replacement or f"[SINT_{random.randint(1000,9999)}]"
    
    def _generate_intelligent_fallback(self, original_value: str) -> str:
        """Fallback inteligente para valores desconocidos"""
        # Analizar el valor para generar algo apropiado
        if original_value.isdigit():
            # Números puros
            if len(original_value) <= 4:
                return str(random.randint(1000, 9999))
            else:
                return ''.join([str(random.randint(0, 9)) for _ in range(len(original_value))])
        
        elif any(char.isalpha() for char in original_value):
            # Contiene letras
            words = original_value.split()
            if len(words) > 1:
                # Múltiples palabras - probablemente nombre o empresa
                if all(word[0].isupper() for word in words if word):
                    return self.fake.name()
                else:
                    return self.fake.company()
            else:
                # Una palabra
                if original_value[0].isupper():
                    return self.fake.first_name()
                else:
                    return self.fake.word()
        
        else:
            # Otros caracteres
            return f"SINT_{random.randint(100, 999)}"

# =====================================================
# Adapter TLS
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
# Cliente LLM Multi-Proveedor
# =====================================================
class MultiProviderLLMClient:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.session = requests.Session()
        self.session.mount("https://", EnhancedTLSAdapter())
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def _initialize_providers(self) -> List[LLMConfig]:
        """Inicializa configuraciones de múltiples proveedores"""
        providers = []
        
        # Groq con modelos válidos actualizados
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
            
        # OpenAI
        if OPENAI_API_KEY:
            providers.append(LLMConfig(
                provider="openai",
                model="gpt-3.5-turbo",
                api_key=OPENAI_API_KEY,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=1000,
                timeout=30
            ))
            
        # Anthropic
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
        """Llama al LLM con fallbacks automáticos"""
        if not self.providers:
            return "[ERROR: No hay proveedores LLM configurados]", "none"
            
        for provider_config in self.providers:
            for attempt in range(provider_config.max_retries):
                try:
                    logger.info(f"Intentando con {provider_config.provider} - {provider_config.model} (intento {attempt + 1})")
                    
                    future = self.executor.submit(self._call_provider, provider_config, prompt)
                    response = future.result(timeout=timeout)
                    
                    logger.info(f"Éxito con {provider_config.provider}")
                    return response, provider_config.provider
                    
                except TimeoutError:
                    logger.warning(f"Timeout con {provider_config.provider} (intento {attempt + 1})")
                    continue
                except Exception as e:
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
# Pipeline corregido y optimizado
# =====================================================
class EnhancedAnonymizationPipeline:
    def __init__(self):
        self.generator = EnhancedSyntheticDataGenerator()
        self.llm_client = MultiProviderLLMClient()
        self.validator = MappingValidator()
        self.metrics = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "avg_processing_time": 0.0,
            "providers_used": {}
        }

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
        """Anonimiza texto con mejor manejo de reemplazos y orden correcto"""
        start_time = time.time()
        anonymized = text
        entities_replaced = 0
        
        # Validar y limpiar mapping
        clean_mapping = self.validator.validate_and_clean_mapping(mapping)
        
        if not clean_mapping:
            logger.warning("No hay entidades válidas para anonimizar")
            return text, 0.0
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_mapping = sorted(clean_mapping.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Realizar reemplazos
        replacement_log = []
        for token, original_value in sorted_mapping:
            if original_value in anonymized:
                # Extraer tipo de entidad del token
                entity_type = token.strip('[]').split('_')[0]
                
                # Generar reemplazo sintético
                replacement = self.generator.generate_synthetic_replacement(entity_type, original_value)
                
                # Realizar reemplazo
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
        
        logger.info(f"Anonimización completada: {entities_replaced}/{len(clean_mapping)} entidades reemplazadas en {processing_time:.2f}s")
        
        # Log de reemplazos para debug
        if replacement_log:
            logger.debug("Resumen de reemplazos realizados:")
            for log_entry in replacement_log[:5]:  # Solo primeros 5 para no spam
                logger.debug(f"  {log_entry['type']}: {log_entry['original'][:20]}... -> {log_entry['replacement'][:20]}...")
        
        return anonymized, confidence

    def de_anonymize(self, text: str) -> str:
        """Desanonimiza texto restaurando valores originales"""
        de_anonymized = text
        replacements_made = 0
        
        if not self.generator.reverse_cache:
            logger.warning("No hay caché de reemplazos para desanonimizar")
            return text
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_cache = sorted(self.generator.reverse_cache.items(), key=lambda x: len(x[0]), reverse=True)
        
        replacement_log = []
        for synthetic, original in sorted_cache:
            if synthetic in de_anonymized:
                de_anonymized = de_anonymized.replace(synthetic, original)
                replacements_made += 1
                replacement_log.append((synthetic, original))
                
        logger.info(f"Desanonimización completada: {replacements_made} entidades restauradas")
        
        # Log de desanonimización para debug
        if replacement_log:
            logger.debug("Resumen de desanonimización:")
            for synthetic, original in replacement_log[:5]:
                logger.debug(f"  {synthetic[:20]}... -> {original[:20]}...")
                
        return de_anonymized

    def run_pipeline(self, 
                     text: str, 
                     model: str = "es", 
                     use_regex: bool = True, 
                     pseudonymize: bool = False,
                     llm_prompt_template: Optional[str] = None,
                     validate_output: bool = True) -> PipelineResult:
        """Ejecuta el pipeline completo mejorado"""
        start_time = time.time()
        self.metrics["total_runs"] += 1
        
        # Validación de entrada
        if not self._validate_input(text):
            self.metrics["failed_runs"] += 1
            return PipelineResult(
                original_text=text,
                success=False,
                error="Entrada inválida: texto vacío o demasiado corto",
                processing_time=time.time() - start_time
            )
        
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO PIPELINE DE ANONIMIZACION")
            logger.info("=" * 60)
            
            # Paso 1: Detección de PII
            log_step("Detectando PII", 1)
            pii_result = pii_run_pipeline(model=model, text=text, use_regex=use_regex, pseudonymize=pseudonymize)
            mapping = pii_result.get("mapping", {})
            
            log_success(f"PII detectado: {len(mapping)} entidades encontradas")
            if mapping:
                logger.debug("Entidades detectadas:")
                for token, value in list(mapping.items())[:5]:
                    logger.debug(f"  - {token}: {value[:30]}...")

            # Caso sin PII detectado
            if not mapping:
                logger.info("No se detecto PII, procesando texto original...")
                
                # Preparar prompt
                if llm_prompt_template:
                    llm_prompt = llm_prompt_template.format(text=text)
                else:
                    llm_prompt = f"Procesa el siguiente texto de manera profesional: {text}"
                
                # Llamar al LLM
                llm_response, provider_used = self.llm_client.call_llm(llm_prompt)
                
                processing_time = time.time() - start_time
                self.metrics["successful_runs"] += 1
                self._update_metrics(processing_time, provider_used)
                
                log_success(f"Pipeline completado sin PII en {processing_time:.2f}s")
                
                return PipelineResult(
                    original_text=text,
                    anonymized_text=text,
                    pii_detected=False,
                    pii_mapping={},
                    llm_prompt=llm_prompt,
                    llm_response=llm_response,
                    final_response=llm_response,
                    success=True,
                    processing_time=processing_time,
                    llm_provider_used=provider_used,
                    confidence_score=1.0
                )

            # Paso 2: Anonimización
            log_step(f"Anonimizando {len(mapping)} entidades PII", 2)
            anonymized, confidence = self.anonymize(text, mapping)
            
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
            final_response = self.de_anonymize(llm_response)

            # Paso 6: Validación opcional
            if validate_output:
                log_step("Validando salida", 6)
                
                if len(final_response) < len(llm_response) * 0.5:
                    log_warning("La desanonimización puede haber fallado parcialmente")
                    confidence *= 0.8
                    
                if not final_response.strip():
                    log_error("Respuesta final vacía")
                    confidence = 0.0

            processing_time = time.time() - start_time
            self.metrics["successful_runs"] += 1
            self._update_metrics(processing_time, provider_used)

            logger.info("=" * 60)
            log_success(f"PIPELINE COMPLETADO EXITOSAMENTE en {processing_time:.2f}s")
            logger.info(f"Confianza: {confidence:.2f} | Proveedor: {provider_used}")
            logger.info("=" * 60)
            
            return PipelineResult(
                original_text=text,
                anonymized_text=anonymized,
                pii_detected=True,
                pii_mapping=mapping,
                llm_prompt=llm_prompt,
                llm_response=llm_response,
                final_response=final_response,
                success=True,
                processing_time=processing_time,
                llm_provider_used=provider_used,
                confidence_score=confidence
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics["failed_runs"] += 1
            self._update_metrics(processing_time, "none")
            
            logger.error("=" * 60)
            log_error(f"ERROR EN EL PIPELINE: {str(e)}")
            logger.error("=" * 60)
            logger.exception("Detalles del error:")
            
            return PipelineResult(
                original_text=text,
                success=False,
                error=str(e),
                processing_time=processing_time
            )

    def _update_metrics(self, processing_time: float, provider_used: str):
        """Actualiza métricas del pipeline"""
        # Actualizar tiempo promedio
        total_time = self.metrics["avg_processing_time"] * (self.metrics["total_runs"] - 1)
        self.metrics["avg_processing_time"] = (total_time + processing_time) / self.metrics["total_runs"]
        
        # Actualizar uso de proveedores
        if provider_used not in self.metrics["providers_used"]:
            self.metrics["providers_used"][provider_used] = 0
        self.metrics["providers_used"][provider_used] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas del pipeline"""
        success_rate = (self.metrics["successful_runs"] / self.metrics["total_runs"]) * 100 if self.metrics["total_runs"] > 0 else 0
        
        return {
            **self.metrics,
            "success_rate_percentage": round(success_rate, 2),
            "cache_size": len(self.generator.replacement_cache),
            "reverse_cache_size": len(self.generator.reverse_cache)
        }

    def clear_cache(self):
        """Limpia caché de entidades sintéticas"""
        self.generator.replacement_cache.clear()
        self.generator.reverse_cache.clear()
        log_success("Cache de entidades sinteticas limpiado")

    def get_replacement_summary(self) -> Dict[str, Any]:
        """Retorna resumen de reemplazos realizados"""
        return {
            "total_replacements": len(self.generator.replacement_cache),
            "cache_sample": dict(list(self.generator.replacement_cache.items())[:10]),
            "reverse_cache_sample": dict(list(self.generator.reverse_cache.items())[:10])
        }

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
            "environment_variables": self._check_environment_variables()
        }
        
        overall_health = all(checks.values())
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "timestamp": time.time(),
            "checks": checks,
            "metrics": self.pipeline.get_metrics(),
            "providers_status": self._get_providers_status()
        }
    
    def _check_cache_health(self) -> bool:
        """Verifica salud del caché"""
        cache_size = len(self.pipeline.generator.replacement_cache)
        reverse_cache_size = len(self.pipeline.generator.reverse_cache)
        return cache_size == reverse_cache_size and cache_size < 10000
    
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
# Test comprehensivo mejorado y compatible
# =====================================================
def run_comprehensive_test():
    """Test completo del sistema con mejor logging y validación"""
    print("=" * 80)
    print("SISTEMA INTEGRADO LLM Y DATOS SINTÉTICOS - TEST COMPRENSIVO V3.0")
    print("=" * 80)
    
    # Crear pipeline
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
    
    # Texto de prueba más realista
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
    
    print(f"\n2. TEXTO DE PRUEBA ({len(test_text)} caracteres):")
    print("-" * 50)
    print(test_text[:200] + "..." if len(test_text) > 200 else test_text)
    
    # Ejecutar pipeline con prompt personalizado
    print(f"\n3. EJECUTANDO PIPELINE...")
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
    
    # Mostrar resultados detallados
    print(f"\n4. RESULTADOS DETALLADOS:")
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
            
            print(f"\nENTIDADES PII DETECTADAS (muestra):")
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
    
    # Métricas del sistema
    print(f"\n5. MÉTRICAS DEL SISTEMA:")
    print("-" * 50)
    metrics = pipeline.get_metrics()
    for key, value in metrics.items():
        if key == 'providers_used':
            print(f"  Proveedores usados: {value}")
        elif key.endswith('_percentage'):
            print(f"  {key}: {value}%")
        elif 'time' in key:
            print(f"  {key}: {value:.2f}s")
        else:
            print(f"  {key}: {value}")
    
    # Resumen de reemplazos
    if result.success and result.pii_detected:
        print(f"\n6. RESUMEN DE REEMPLAZOS:")
        print("-" * 50)
        replacement_summary = pipeline.get_replacement_summary()
        print(f"  Total de reemplazos en caché: {replacement_summary['total_replacements']}")
        
        if replacement_summary['cache_sample']:
            print(f"  Muestra de reemplazos:")
            for i, (key, value) in enumerate(list(replacement_summary['cache_sample'].items())[:3]):
                print(f"    {i+1}. {key[:30]}... -> {value[:30]}...")
    
    print(f"\n" + "=" * 80)
    print("TEST COMPRENSIVO COMPLETADO")
    print(f"Estado final: {'EXITOSO' if result.success else 'FALLIDO'}")
    print("=" * 80)
    
    return result

def main():
    """Función principal con mejor manejo de errores y logging"""
    try:
        # Banner de inicio
        print("\n" + "*" * 80)
        print("*" + " " * 78 + "*")
        print("*" + " SISTEMA DE ANONIMIZACIÓN LLM - VERSIÓN OPTIMIZADA ".center(78) + "*")
        print("*" + " " * 78 + "*")
        print("*" * 80 + "\n")
        
        # Ejecutar test comprensivo
        result = run_comprehensive_test()
        
        # Ejemplo de uso simple adicional
        if result.success:
            print(f"\nEJEMPLO DE USO SIMPLE:")
            print("-" * 40)
            
            simple_pipeline = EnhancedAnonymizationPipeline()
            
            simple_examples = [
                "Hola, soy Ana García Ruiz y mi email es ana.garcia@empresa.com. Mi teléfono es 666 123 456.",
                "El Sr. Juan Pérez trabajaba en Banco Santander S.A. Su DNI es 12345678Z.",
                "Contactar con María López (maria@gmail.com) para más información sobre Madrid."
            ]
            
            for i, simple_text in enumerate(simple_examples, 1):
                print(f"\nEjemplo {i}:")
                print(f"   Original: {simple_text}")
                
                simple_result = simple_pipeline.run_pipeline(
                    text=simple_text,
                    llm_prompt_template="Mejora la redacción profesional de este texto: {text}"
                )
                
                if simple_result.success:
                    print(f"   Resultado: {simple_result.final_response[:200]}...")
                    if simple_result.pii_detected:
                        print(f"      PII detectado: {len(simple_result.pii_mapping)} entidades")
                else:
                    print(f"   Error: {simple_result.error}")
        
        print(f"\nPROCESO COMPLETADO EXITOSAMENTE")
        
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
        print("¡Hasta luego!")
    except Exception as e:
        logger.error(f"Error crítico en main: {e}", exc_info=True)
        print(f"\nERROR CRÍTICO: {e}")
        print("Revisa los logs para más detalles")

if __name__ == "__main__":
    main()