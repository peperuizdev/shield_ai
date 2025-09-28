import random
import os
import sys
import json
import time
import ssl
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
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
# Configuración de logging mejorada
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('llm_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# Cargar variables de entorno
# =====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

# Variables de configuración
GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("SHIELD_AI_GROK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Fallback
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Fallback

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
# Importar el detector de PII con mejores fallbacks
# =====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
<<<<<<< HEAD
    from pii_detector import run_pipeline as pii_run_pipeline
    PII_DETECTOR_AVAILABLE = True
=======
    from .pii_detector import run_pipeline as pii_run_pipeline
>>>>>>> 4fb12fa62de7121e6a0d9c7dd4080379c634bef3
except ImportError:
    logger.warning("No se pudo importar run_pipeline. Usando función mock mejorada.")
    PII_DETECTOR_AVAILABLE = False
    
    def pii_run_pipeline(model="es", text="", use_regex=True, pseudonymize=False):
        # Mock más realista para desarrollo
        import re
        mapping = {}
        
        # Detectar emails básicos
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for i, email in enumerate(emails, 1):
            mapping[f"[EMAIL_{i}]"] = email
            
        # Detectar nombres propios básicos (mayúscula seguida de minúsculas)
        names = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b', text)
        for i, name in enumerate(names[:3], 1):  # Limitar a 3 nombres
            if len(name.split()) >= 2:  # Solo nombres compuestos
                mapping[f"[PERSON_{i}]"] = name
                
        # Detectar teléfonos básicos
        phones = re.findall(r'(?:\+34\s?)?[6-9]\d{2}\s?\d{3}\s?\d{3}', text)
        for i, phone in enumerate(phones, 1):
            mapping[f"[PHONE_{i}]"] = phone
            
        return {"mapping": mapping, "anonymized_text": text}

# =====================================================
# Generador de datos sintéticos mejorado
# =====================================================
class EnhancedSyntheticDataGenerator:
    def __init__(self, locale='es_ES'):
        self.fake = Faker(locale)
        self.replacement_cache = {}
        self.reverse_cache = {}
        self.consistency_map = {}  # Para mantener consistencia entre entidades relacionadas
        
    def _generate_consistent_hash(self, value: str, entity_type: str) -> str:
        """Genera un hash consistente para mantener relaciones entre entidades"""
        return hashlib.md5(f"{entity_type}:{value}".encode()).hexdigest()[:8]
        
    def generate_synthetic_dni(self, original_value: str = None) -> str:
        """Genera DNI sintético con algoritmo de validación real"""
        if original_value:
            # Usar hash para consistencia
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
        
        # Convertir prefix a número para cálculo
        prefix_num = {'X': 0, 'Y': 1, 'Z': 2}[prefix]
        full_number = str(prefix_num) + numbers
        control = letters[int(full_number) % 23]
        return f"{prefix}{numbers}{control}"

    def generate_synthetic_phone(self, original_value: str = None) -> str:
        """Genera teléfono sintético manteniendo formato español"""
        if original_value:
            hash_val = self._generate_consistent_hash(original_value, "PHONE")
            seed = int(hash_val, 16) % 99999999
            random.seed(seed)
            
        # Mantener estructura de teléfonos españoles
        if original_value and '+34' in original_value:
            prefix = '+34 '
        else:
            prefix = ''
            
        first_digit = random.choice(['6', '7', '9'])  # Móviles españoles típicos
        rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{prefix}{first_digit}{rest[:2]} {rest[2:5]} {rest[5:]}"

    def generate_synthetic_email(self, original_value: str = None) -> str:
        """Genera email sintético manteniendo estructura similar"""
        if original_value:
            # Mantener dominio similar si es conocido
            domain_part = original_value.split('@')[-1] if '@' in original_value else None
            if domain_part and any(d in domain_part.lower() for d in ['gmail', 'hotmail', 'yahoo', 'telefonica', 'empresa']):
                # Usar dominio sintético pero similar
                synthetic_domains = {
                    'gmail': 'sintemail.com',
                    'hotmail': 'sintmail.com',
                    'yahoo': 'sintyahoo.com',
                    'telefonica': 'sinttelefonica.com'
                }
                for orig_domain, synt_domain in synthetic_domains.items():
                    if orig_domain in domain_part.lower():
                        username = self.fake.user_name()
                        return f"{username}@{synt_domain}"
                        
        return self.fake.email()

    def generate_synthetic_person_name(self, original_value: str = None) -> str:
        """Genera nombre sintético manteniendo estructura (nombre(s) + apellido(s))"""
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
        """Genera ubicación sintética manteniendo contexto español"""
        spanish_cities = ['Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 'Zaragoza', 'Murcia', 'Córdoba']
        return random.choice(spanish_cities)

    def generate_synthetic_organization(self, original_value: str = None) -> str:
        """Genera organización sintética"""
        if original_value and any(keyword in original_value.lower() for keyword in ['bank', 'banco', 'telefonica', 'iberdrola']):
            synthetic_companies = ['Banco Sintético S.A.', 'Telefónica Sintética', 'Energías Sintéticas', 'Consultoría Sintética']
            return random.choice(synthetic_companies)
        return self.fake.company()

    def generate_synthetic_iban(self, original_value: str = None) -> str:
        """Genera IBAN sintético válido español"""
        # IBAN español sintético (ES + 2 dígitos control + 4 dígitos banco + 4 dígitos sucursal + 2 control + 10 cuenta)
        bank_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        branch_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        control_digits = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        
        # Control IBAN simplificado (no real, solo para demo)
        iban_control = ''.join([str(random.randint(0, 9)) for _ in range(2)])
        
        return f"ES{iban_control}{bank_code}{branch_code}{control_digits}{account_number}"

    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        """Genera reemplazo sintético con caché y consistencia"""
        cache_key = f"{entity_type}:{original_value}"
        
        if cache_key in self.replacement_cache:
            return self.replacement_cache[cache_key]

        try:
            entity_enum = EntityType(entity_type)
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
            # Fallback para entidades desconocidas
            replacement = f"[SYNTHETIC_{entity_type}_{random.randint(1000,9999)}]"

        # Guardar en caché bidireccional
        self.replacement_cache[cache_key] = replacement
        self.reverse_cache[replacement] = original_value
        
        return replacement

# =====================================================
# Adapter TLS mejorado con retry strategy
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
<<<<<<< HEAD
# Cliente LLM Multi-Proveedor con Fallbacks
=======
# Cliente LLM usando Grok - Versión Original
>>>>>>> 4fb12fa62de7121e6a0d9c7dd4080379c634bef3
# =====================================================
class MultiProviderLLMClient:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.session = requests.Session()
        self.session.mount("https://", EnhancedTLSAdapter())
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def _initialize_providers(self) -> List[LLMConfig]:
        """Inicializa configuraciones de múltiples proveedores con modelos actuales"""
        providers = []
        
        # Groq (modelos actuales válidos - actualizado Sept 2025)
        if GROK_API_KEY:
            # Modelos actuales disponibles en Groq
            groq_models = [
                "gemma2-9b-it",  # Modelo activo y rápido
                "deepseek-r1-distill-llama-70b",  # Modelo potente
                "allam-2-7b",  # Alternativa
                "meta-llama/llama-4-scout-17b-16e-instruct"  # Modelo nuevo
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
            
        # OpenAI (fallback)
        if OPENAI_API_KEY:
            providers.append(LLMConfig(
                provider="openai",
                model="gpt-3.5-turbo",
                api_key=OPENAI_API_KEY,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=1000,
                timeout=30
            ))
            
        # Anthropic (fallback)
        if ANTHROPIC_API_KEY:
            providers.append(LLMConfig(
                provider="anthropic",
                model="claude-3-haiku-20240307",
                api_key=ANTHROPIC_API_KEY,
                endpoint="https://api.anthropic.com/v1/messages",
                max_tokens=1000,
                timeout=30
            ))
            
        if not providers:
            logger.warning("No se configuraron proveedores LLM válidos")
            
        logger.info(f"Configurados {len(providers)} proveedores LLM con modelos actuales")
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
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        return result.get("output_text", "[ERROR: respuesta vacía]")

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
        """
        Llama al LLM con fallbacks automáticos
        Returns: (response_text, provider_used)
        """
        if not self.providers:
            return "[ERROR: No hay proveedores LLM configurados]", "none"
            
        for provider_config in self.providers:
            for attempt in range(provider_config.max_retries):
                try:
                    logger.info(f"Intentando con {provider_config.provider} (intento {attempt + 1})")
                    
                    # Usar ThreadPoolExecutor para timeout robusto
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
        return f"[ERROR: Todos los proveedores fallaron. Prompt: {prompt[:100]}...]", "failed"

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
# Pipeline mejorado con métricas y validación
# =====================================================
class EnhancedAnonymizationPipeline:
    def __init__(self):
        self.generator = EnhancedSyntheticDataGenerator()
        self.llm_client = MultiProviderLLMClient()
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
        if len(text.strip()) < 10:  # Muy corto para procesar
            return False
        if len(text) > 50000:  # Muy largo para procesar eficientemente
            logger.warning("Texto muy largo, puede afectar el rendimiento")
        return True

<<<<<<< HEAD
    def anonymize(self, text: str, mapping: Dict[str, str]) -> tuple[str, float]:
        """Anonimiza texto con métricas de confianza"""
        start_time = time.time()
=======
# =====================================================
# Cliente LLM Mejorado - Propuesta
# =====================================================
class LLMClientPropuesta:
    def __init__(self):
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = GROK_API_KEY
        self.model = "llama-3.1-8b-instant"  # Modelo actualizado que funciona en Groq
        self.max_retries = 3
        self.session = requests.Session()
        self.session.mount("https://", TLSAdapter())
        
        if not self.api_key:
            logger.error("GROK_API_KEY no encontrada. LLMClientPropuesta no funcionará.")

    def call_grok(self, prompt: str, model: str = None, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Llama a la API de Groq con manejo mejorado de errores y parsing de respuestas.
        
        Args:
            prompt: Texto a enviar al modelo
            model: Modelo específico a usar (opcional)
            max_tokens: Máximo número de tokens en respuesta
            temperature: Creatividad del modelo (0.0 - 1.0)
        """
        if not self.api_key:
            return "[ERROR: GROK_API_KEY no configurada]"
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Enviando request a Groq (intento {attempt + 1}/{self.max_retries})")
                response = self.session.post(self.endpoint, headers=headers, json=payload, timeout=30)
                
                # Log del status code para debugging
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 400:
                    error_detail = response.json() if response.content else {"error": "Bad Request"}
                    logger.error(f"Error 400 - Payload: {payload}")
                    logger.error(f"Error 400 - Response: {error_detail}")
                    return f"[ERROR: Bad Request - {error_detail.get('error', {}).get('message', 'Formato incorrecto')}]"
                
                response.raise_for_status()
                result = response.json()
                
                # Logging para debugging
                logger.debug(f"Respuesta completa de Groq: {result}")
                
                # Parsing correcto para API de Groq/OpenAI
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"].strip()
                        if content:
                            logger.info("Respuesta exitosa de Groq")
                            return content
                
                # Fallbacks para otros formatos posibles
                content = result.get("output_text") or result.get("text") or result.get("response")
                if content:
                    return content.strip()
                
                logger.warning(f"Respuesta de Groq sin contenido válido: {result}")
                return "[ERROR: Respuesta vacía o formato inesperado de Groq]"
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en intento {attempt+1}")
                if attempt == self.max_retries - 1:
                    return "[ERROR: Timeout - Groq no respondió en 30 segundos]"
                    
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP Error en intento {attempt+1}: {e}")
                if e.response.status_code == 401:
                    return "[ERROR: API Key inválida o sin permisos]"
                elif e.response.status_code == 429:
                    logger.warning("Rate limit alcanzado, esperando más tiempo...")
                    time.sleep(2 ** (attempt + 2))  # Espera más tiempo en rate limits
                    continue
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"Error de conexión en intento {attempt+1}")
                if attempt == self.max_retries - 1:
                    return "[ERROR: No se puede conectar a Groq API]"
                    
            except Exception as e:
                logger.warning(f"Error inesperado en intento {attempt+1}: {type(e).__name__}: {e}")
                
            # Backoff exponencial entre intentos
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Esperando {wait_time}s antes del siguiente intento...")
                time.sleep(wait_time)
        
        logger.error("Todos los intentos con Groq fallaron")
        return f"[ERROR: No se pudo procesar con Groq después de {self.max_retries} intentos. Prompt: {prompt[:100]}...]"

    async def call_grok_stream(self, prompt: str, model: str = None, max_tokens: int = 500, temperature: float = 0.7):
        """
        Llama a la API de Groq con streaming real usando Server-Sent Events.
        
        Args:
            prompt: Texto a enviar al modelo
            model: Modelo específico a usar (opcional)
            max_tokens: Máximo número de tokens en respuesta
            temperature: Creatividad del modelo (0.0 - 1.0)
            
        Yields:
            str: Cada chunk/token de texto que viene del modelo en tiempo real
        """
        if not self.api_key:
            yield "[ERROR: GROK_API_KEY no configurada]"
            return
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Check if prompt contains system instructions (starts with special format)
        if prompt.startswith("SYSTEM:"):
            parts = prompt.split("USER:", 1)
            system_content = parts[0].replace("SYSTEM:", "").strip()
            user_content = parts[1].strip() if len(parts) > 1 else ""
            
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True  # ← ACTIVAR STREAMING REAL
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Enviando streaming request a Groq (intento {attempt + 1}/{self.max_retries})")
                
                # Usar stream=True para obtener respuesta en chunks
                response = self.session.post(
                    self.endpoint, 
                    headers=headers, 
                    json=payload, 
                    timeout=30,
                    stream=True  # ← STREAMING HTTP
                )
                
                response.raise_for_status()
                logger.info(f"Streaming response status: {response.status_code}")
                
                # Procesar líneas SSE en tiempo real
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8').strip()
                        
                        # Formato SSE: "data: {json}"
                        if line_text.startswith('data: '):
                            data_json = line_text[6:]  # Remover "data: "
                            
                            # Fin del stream
                            if data_json.strip() == '[DONE]':
                                logger.info("Stream completado correctamente")
                                return
                            
                            try:
                                data = json.loads(data_json)
                                
                                # Extraer contenido del chunk
                                if 'choices' in data and len(data['choices']) > 0:
                                    choice = data['choices'][0]
                                    if 'delta' in choice and 'content' in choice['delta']:
                                        chunk_content = choice['delta']['content']
                                        if chunk_content:
                                            yield chunk_content
                                            
                            except json.JSONDecodeError:
                                # Ignorar líneas que no son JSON válido
                                continue
                            except KeyError:
                                # Ignorar chunks sin contenido
                                continue
                
                # Si llegamos aquí, el stream terminó correctamente
                return
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en streaming intento {attempt+1}")
                if attempt == self.max_retries - 1:
                    yield "[ERROR: Timeout - Groq no respondió en 30 segundos]"
                    return
                    
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP Error en streaming intento {attempt+1}: {e}")
                if e.response.status_code == 401:
                    yield "[ERROR: API Key inválida o sin permisos]"
                    return
                elif e.response.status_code == 429:
                    logger.warning("Rate limit alcanzado en streaming, esperando...")
                    time.sleep(2 ** (attempt + 2))
                    continue
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"Error de conexión en streaming intento {attempt+1}")
                if attempt == self.max_retries - 1:
                    yield "[ERROR: No se puede conectar a Groq API para streaming]"
                    return
                    
            except Exception as e:
                logger.warning(f"Error inesperado en streaming intento {attempt+1}: {type(e).__name__}: {e}")
                
            # Backoff exponencial entre intentos
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Esperando {wait_time}s antes del siguiente intento de streaming...")
                time.sleep(wait_time)
        
        logger.error("Todos los intentos de streaming con Groq fallaron")
        yield f"[ERROR: No se pudo hacer streaming con Groq después de {self.max_retries} intentos]"

    def deanonymize_chunk(self, chunk: str, mapping: Dict[str, str]) -> str:
        """
        Deanonymiza un chunk de texto aplicando el mapping de entidades.
        Optimizado para procesar chunks pequeños en tiempo real.
        
        Args:
            chunk: Fragmento de texto a deanonymizar
            mapping: Diccionario {valor_falso: valor_real}
        
        Returns:
            str: Chunk deanonymizado
        """
        if not mapping or not chunk:
            return chunk
            
        deanonymized = chunk
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        
        for fake_value, real_value in sorted_mapping:
            if fake_value in deanonymized:
                deanonymized = deanonymized.replace(fake_value, real_value)
                
        return deanonymized

    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con la API de Groq.
        
        Returns:
            Dict con información del estado de la conexión
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "API Key no configurada",
                "api_key_present": False
            }
        
        test_prompt = "Responde solo con 'OK' si puedes procesar este mensaje."
        start_time = time.time()
        
        try:
            result = self.call_grok(test_prompt, max_tokens=10)
            processing_time = time.time() - start_time
            
            if "[ERROR:" in result:
                return {
                    "status": "error", 
                    "message": result,
                    "api_key_present": True,
                    "processing_time": processing_time
                }
            else:
                return {
                    "status": "success",
                    "message": "Conexión exitosa con Groq",
                    "api_key_present": True,
                    "test_response": result,
                    "processing_time": processing_time,
                    "model": self.model
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error en test: {str(e)}",
                "api_key_present": True,
                "processing_time": time.time() - start_time
            }

# =====================================================
# Pipeline completo: anonimización → LLM → desanonimización
# =====================================================
class AnonymizationPipeline:
    def __init__(self):
        self.generator = SyntheticDataGenerator()
        self.llm_client = LLMClient()

    def anonymize(self, text: str, mapping: Dict[str, str]) -> str:
>>>>>>> 4fb12fa62de7121e6a0d9c7dd4080379c634bef3
        anonymized = text
        entities_replaced = 0
        
        for token, original_value in mapping.items():
            if original_value in text:  # Verificar que realmente existe
                entity_type = token.strip('[]').split('_')[0]
                replacement = self.generator.generate_synthetic_replacement(entity_type, original_value)
                anonymized = anonymized.replace(original_value, replacement)
                entities_replaced += 1
                
        processing_time = time.time() - start_time
        confidence = min(entities_replaced / len(mapping) if mapping else 1.0, 1.0)
        
        logger.info(f"Anonimización completada: {entities_replaced}/{len(mapping)} entidades reemplazadas en {processing_time:.2f}s")
        return anonymized, confidence

    def de_anonymize(self, text: str) -> str:
        """Desanonimiza texto restaurando valores originales"""
        de_anonymized = text
        replacements_made = 0
        
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_cache = sorted(self.generator.reverse_cache.items(), key=lambda x: len(x[0]), reverse=True)
        
        for synthetic, original in sorted_cache:
            if synthetic in de_anonymized:
                de_anonymized = de_anonymized.replace(synthetic, original)
                replacements_made += 1
                
        logger.info(f"Desanonimización completada: {replacements_made} entidades restauradas")
        return de_anonymized

    def run_pipeline(self, 
                     text: str, 
                     model: str = "es", 
                     use_regex: bool = True, 
                     pseudonymize: bool = False,
                     llm_prompt_template: Optional[str] = None,
                     validate_output: bool = True) -> PipelineResult:
        """
        Ejecuta el pipeline completo con manejo robusto de errores
        """
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
            logger.info("Iniciando pipeline de anonimización...")
            
            # Paso 1: Detección de PII
            logger.info("Detectando PII...")
            if PII_DETECTOR_AVAILABLE:
                pii_result = pii_run_pipeline(model=model, text=text, use_regex=use_regex, pseudonymize=pseudonymize)
            else:
                pii_result = pii_run_pipeline(model=model, text=text, use_regex=use_regex, pseudonymize=pseudonymize)
                
            mapping = pii_result.get("mapping", {})
            logger.info(f"PII detectado: {len(mapping)} entidades encontradas")

            # Caso sin PII detectado
            if not mapping:
                logger.info("No se detectó PII, procesando texto original...")
                llm_response, provider_used = self.llm_client.call_llm(
                    llm_prompt_template.format(text=text) if llm_prompt_template else text
                )
                
                processing_time = time.time() - start_time
                self.metrics["successful_runs"] += 1
                self._update_metrics(processing_time, provider_used)
                
                return PipelineResult(
                    original_text=text,
                    anonymized_text=text,
                    pii_detected=False,
                    pii_mapping={},
                    llm_response=llm_response,
                    final_response=llm_response,
                    success=True,
                    processing_time=processing_time,
                    llm_provider_used=provider_used,
                    confidence_score=1.0
                )

            # Paso 2: Anonimización
            logger.info(f"Anonimizando {len(mapping)} entidades PII...")
            anonymized, confidence = self.anonymize(text, mapping)

            # Paso 3: Preparar prompt para LLM
            if llm_prompt_template:
                llm_prompt = llm_prompt_template.format(text=anonymized)
            else:
                llm_prompt = f"Procesa el siguiente texto de manera profesional: {anonymized}"

            # Paso 4: Llamada al LLM
            logger.info("Enviando al LLM...")
            llm_response, provider_used = self.llm_client.call_llm(llm_prompt)

            # Paso 5: Desanonimización
            logger.info("Desanonimizando respuesta...")
            final_response = self.de_anonymize(llm_response)

            # Paso 6: Validación opcional
            if validate_output:
                if "[ERROR:" in llm_response:
                    logger.warning("Respuesta del LLM contiene errores")
                    confidence *= 0.7
                    
                if len(final_response) < len(llm_response) * 0.5:
                    logger.warning("La desanonimización puede haber fallado parcialmente")
                    confidence *= 0.8

            processing_time = time.time() - start_time
            self.metrics["successful_runs"] += 1
            self._update_metrics(processing_time, provider_used)

            logger.info(f"Pipeline completado exitosamente en {processing_time:.2f}s")
            
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
            
            logger.error(f"Error en el pipeline: {str(e)}", exc_info=True)
            
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
        logger.info("Caché de entidades sintéticas limpiado")

# =====================================================
# Sistema de Salud y Monitoreo
# =====================================================
class PipelineHealthMonitor:
    def __init__(self, pipeline: EnhancedAnonymizationPipeline):
        self.pipeline = pipeline
        self.health_checks = []
        
    def health_check(self) -> Dict[str, Any]:
        """Ejecuta verificaciones de salud del sistema"""
        checks = {
            "pii_detector_available": PII_DETECTOR_AVAILABLE,
            "llm_providers_configured": len(self.pipeline.llm_client.providers) > 0,
            "cache_health": self._check_cache_health(),
            "api_connectivity": self._check_api_connectivity(),
            "system_resources": self._check_system_resources()
        }
        
        overall_health = all(checks.values())
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "timestamp": time.time(),
            "checks": checks,
            "metrics": self.pipeline.get_metrics()
        }
    
    def _check_cache_health(self) -> bool:
        """Verifica salud del caché"""
        cache_size = len(self.pipeline.generator.replacement_cache)
        reverse_cache_size = len(self.pipeline.generator.reverse_cache)
        
        # Verificar consistencia
        return cache_size == reverse_cache_size and cache_size < 10000  # Límite razonable
    
    def _check_api_connectivity(self) -> bool:
        """Verifica conectividad básica con APIs"""
        if not self.pipeline.llm_client.providers:
            return False
            
        # Test simple con el primer proveedor
        try:
            # No hacer llamada real, solo verificar configuración
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
            # Si psutil no está disponible, asumir OK
            return True

# =====================================================
# Utilidades y Helpers
# =====================================================
class PipelineUtils:
    @staticmethod
    def validate_pii_mapping(mapping: Dict[str, str]) -> bool:
        """Valida estructura del mapping de PII"""
        if not isinstance(mapping, dict):
            return False
            
        for token, value in mapping.items():
            if not token.startswith('[') or not token.endswith(']'):
                return False
            if not isinstance(value, str) or not value.strip():
                return False
                
        return True
    
    @staticmethod
    def estimate_processing_time(text_length: int, pii_count: int) -> float:
        """Estima tiempo de procesamiento basado en longitud y PII"""
        base_time = 2.0  # Tiempo base en segundos
        text_factor = text_length / 1000 * 0.5  # 0.5s por cada 1000 caracteres
        pii_factor = pii_count * 0.3  # 0.3s por cada entidad PII
        llm_time = 5.0  # Tiempo estimado para LLM
        
        return base_time + text_factor + pii_factor + llm_time
    
    @staticmethod
    def sanitize_for_logging(text: str, max_length: int = 100) -> str:
        """Sanitiza texto para logging sin exponer PII"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

# =====================================================
# Configurador de Pipeline
# =====================================================
class PipelineConfig:
    """Configuración centralizada del pipeline"""
    
    def __init__(self):
        self.pii_model = "es"
        self.use_regex = True
        self.pseudonymize = False
        self.validate_output = True
        self.max_text_length = 50000
        self.llm_timeout = 45
        self.synthetic_data_locale = 'es_ES'
        self.enable_metrics = True
        self.enable_caching = True
        self.log_level = logging.INFO
        
    def from_env(self) -> 'PipelineConfig':
        """Carga configuración desde variables de entorno"""
        self.pii_model = os.getenv("PII_MODEL", self.pii_model)
        self.use_regex = os.getenv("USE_REGEX", "true").lower() == "true"
        self.pseudonymize = os.getenv("PSEUDONYMIZE", "false").lower() == "true"
        self.validate_output = os.getenv("VALIDATE_OUTPUT", "true").lower() == "true"
        self.max_text_length = int(os.getenv("MAX_TEXT_LENGTH", self.max_text_length))
        self.llm_timeout = int(os.getenv("LLM_TIMEOUT", self.llm_timeout))
        self.synthetic_data_locale = os.getenv("SYNTHETIC_DATA_LOCALE", self.synthetic_data_locale)
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_level = getattr(logging, log_level_str, logging.INFO)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte configuración a diccionario"""
        return {
            "pii_model": self.pii_model,
            "use_regex": self.use_regex,
            "pseudonymize": self.pseudonymize,
            "validate_output": self.validate_output,
            "max_text_length": self.max_text_length,
            "llm_timeout": self.llm_timeout,
            "synthetic_data_locale": self.synthetic_data_locale,
            "enable_metrics": self.enable_metrics,
            "enable_caching": self.enable_caching,
            "log_level": logging.getLevelName(self.log_level)
        }

# =====================================================
# Factory para crear pipelines configurados
# =====================================================
class PipelineFactory:
    @staticmethod
    def create_pipeline(config: Optional[PipelineConfig] = None) -> EnhancedAnonymizationPipeline:
        """Crea pipeline con configuración específica"""
        if config is None:
            config = PipelineConfig().from_env()
            
        # Configurar logging
        logging.getLogger().setLevel(config.log_level)
        
        # Crear pipeline
        pipeline = EnhancedAnonymizationPipeline()
        
        # Configurar generador de datos sintéticos
        pipeline.generator = EnhancedSyntheticDataGenerator(locale=config.synthetic_data_locale)
        
        # Aplicar configuraciones
        if not config.enable_caching:
            pipeline.generator.replacement_cache = {}
            pipeline.generator.reverse_cache = {}
            
        logger.info(f"Pipeline creado con configuración: {config.to_dict()}")
        return pipeline

# =====================================================
# Ejemplos de uso y testing
# =====================================================
def run_comprehensive_test():
    """Ejecuta test comprensivo del sistema"""
    print("=" * 80)
    print("SISTEMA INTEGRADO LLM Y DATOS SINTÉTICOS - TEST COMPRENSIVO")
    print("=" * 80)
    
    # Crear configuración personalizada
    config = PipelineConfig()
    config.validate_output = True
    config.enable_metrics = True
    
    # Crear pipeline
    pipeline = PipelineFactory.create_pipeline(config)
    monitor = PipelineHealthMonitor(pipeline)
    
    # Test de salud del sistema
    print("\n1. VERIFICACIÓN DE SALUD DEL SISTEMA:")
    health = monitor.health_check()
    print(f"Estado general: {health['overall_health'].upper()}")
    for check, status in health['checks'].items():
        print(f"  - {check}: {'✓' if status else '✗'}")
    
    # Test con texto complejo
    test_text = """
    Estimado Sr. Juan Pérez García,
    
    Le escribo desde Telefónica España S.A. para informarle sobre su cuenta.
    Sus datos de contacto registrados son:
    - Email: juan.perez@telefonica.com
    - Teléfono móvil: +34 666 123 456
    - Teléfono fijo: 91 123 45 67
    - DNI: 12345678Z
    - Dirección: Calle Gran Vía 123, Madrid
    
    Su IBAN ES91 2100 0418 4502 0005 1332 está asociado a esta cuenta.
    
    Para cualquier consulta, contacte con nosotros.
    
    Atentamente,
    María González López
    Departamento de Atención al Cliente
    maria.gonzalez@telefonica.com
    """
    
    print(f"\n2. TEXTO ORIGINAL ({len(test_text)} caracteres):")
    print(PipelineUtils.sanitize_for_logging(test_text, 150))
    
    # Ejecutar pipeline
    print("\n3. EJECUTANDO PIPELINE...")
    estimated_time = PipelineUtils.estimate_processing_time(len(test_text), 8)
    print(f"Tiempo estimado: {estimated_time:.1f}s")
    
    result = pipeline.run_pipeline(
        text=test_text,
        model="es",
        llm_prompt_template="Reescribe este texto de manera más formal y profesional, manteniendo toda la información importante: {text}",
        validate_output=True
    )
    
    # Mostrar resultados
    print(f"\n4. RESULTADOS:")
    print(f"Éxito: {'✓' if result.success else '✗'}")
    if result.success:
        print(f"PII detectado: {'Sí' if result.pii_detected else 'No'}")
        print(f"Entidades encontradas: {len(result.pii_mapping)}")
        print(f"Proveedor LLM: {result.llm_provider_used}")
        print(f"Tiempo de procesamiento: {result.processing_time:.2f}s")
        print(f"Puntuación de confianza: {result.confidence_score:.2f}")
        
        if result.pii_detected:
            print(f"\nEntidades PII detectadas:")
            for token, value in list(result.pii_mapping.items())[:5]:  # Mostrar solo 5
                sanitized_value = PipelineUtils.sanitize_for_logging(value, 20)
                print(f"  - {token}: {sanitized_value}")
            
            print(f"\nTexto anonimizado (muestra):")
            print(PipelineUtils.sanitize_for_logging(result.anonymized_text, 200))
        
        print(f"\nRespuesta final (muestra):")
        print(PipelineUtils.sanitize_for_logging(result.final_response, 300))
        
    else:
        print(f"Error: {result.error}")
    
    # Métricas finales
    print(f"\n5. MÉTRICAS DEL SISTEMA:")
    metrics = pipeline.get_metrics()
    for key, value in metrics.items():
        print(f"  - {key}: {value}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETADO")
    print("=" * 80)
    
    return result

def main():
    """Función principal mejorada"""
    try:
        # Ejecutar test comprensivo
        result = run_comprehensive_test()
        
        # Ejemplo de uso simple
        print("\n\nEJEMPLO DE USO SIMPLE:")
        print("-" * 40)
        
        simple_pipeline = PipelineFactory.create_pipeline()
        
        simple_text = "Hola, soy Ana García y mi email es ana@example.com"
        simple_result = simple_pipeline.run_pipeline(
            text=simple_text,
            llm_prompt_template="Mejora la redacción de este texto: {text}"
        )
        
        if simple_result.success:
            print(f"Original: {simple_text}")
            print(f"Resultado: {simple_result.final_response}")
        else:
            print(f"Error: {simple_result.error}")
            
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en main: {e}", exc_info=True)
        print(f"\nError inesperado: {e}")

if __name__ == "__main__":
    main()