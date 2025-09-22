import random
import os
import sys
import json
import time
import ssl
from typing import Dict, Any, Optional, List
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from dotenv import load_dotenv
from faker import Faker

# =====================================================
# Configurar logging
# =====================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# Cargar variables de entorno desde la raíz del proyecto
# =====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # services -> app -> backend -> raíz
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("SHIELD_AI_GROK_API_KEY")
if not GROK_API_KEY:
    logger.warning("No se encontró GROK_API_KEY en .env")

# =====================================================
# Importar el detector de PII
# =====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from pii_detector import run_pipeline as pii_run_pipeline
except ImportError:
    logger.warning("No se pudo importar run_pipeline. Usando función mock.")
    def pii_run_pipeline(model="es", text="", use_regex=True, pseudonymize=False):
        return {"mapping": {"[EMAIL_1]": "juanperez@gmail.com", "[PERSON_1]": "Juan Pérez"}}

# =====================================================
# Generación de datos sintéticos con Faker
# =====================================================
class SyntheticDataGenerator:
    def __init__(self):
        self.fake = Faker('es_ES')
        self.replacement_cache = {}
        self.reverse_cache = {}

    def generate_synthetic_dni(self) -> str:
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        letter = letters[int(numbers) % 23]
        return f"{numbers}{letter}"

    def generate_synthetic_nie(self) -> str:
        prefix = random.choice(['X', 'Y', 'Z'])
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        control = letters[int(numbers) % 23]
        return f"{prefix}{numbers}{control}"

    def generate_synthetic_phone(self) -> str:
        return self.fake.phone_number()

    def generate_synthetic_email(self) -> str:
        return self.fake.email()

    def generate_synthetic_person_name(self) -> str:
        return self.fake.name()

    def generate_synthetic_location(self) -> str:
        return self.fake.city()

    def generate_synthetic_organization(self) -> str:
        return self.fake.company()

    def generate_synthetic_iban(self) -> str:
        return self.fake.iban()

    def generate_synthetic_replacement(self, entity_type: str, original_value: str) -> str:
        cache_key = f"{entity_type}:{original_value}"
        if cache_key in self.replacement_cache:
            return self.replacement_cache[cache_key]

        replacement = None
        if entity_type == "DNI":
            replacement = self.generate_synthetic_dni()
        elif entity_type == "NIE":
            replacement = self.generate_synthetic_nie()
        elif entity_type == "EMAIL":
            replacement = self.generate_synthetic_email()
        elif entity_type in ["PHONE", "MOBILE_PHONE", "LANDLINE_PHONE"]:
            replacement = self.generate_synthetic_phone()
        elif entity_type == "PERSON":
            replacement = self.generate_synthetic_person_name()
        elif entity_type == "LOCATION":
            replacement = self.generate_synthetic_location()
        elif entity_type == "ORGANIZATION":
            replacement = self.generate_synthetic_organization()
        elif entity_type == "IBAN":
            replacement = self.generate_synthetic_iban()
        else:
            replacement = f"[{entity_type}_FAKER_{random.randint(100,999)}]"

        self.replacement_cache[cache_key] = replacement
        self.reverse_cache[replacement] = original_value
        return replacement

# =====================================================
# Adapter TLS para Windows
# =====================================================
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.minimum_version = getattr(ssl, "TLSVersion", ssl).TLSv1_2
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context()
        context.minimum_version = getattr(ssl, "TLSVersion", ssl).TLSv1_2
        kwargs["ssl_context"] = context
        return super().proxy_manager_for(*args, **kwargs)

# =====================================================
# Cliente LLM usando Grok
# =====================================================
class LLMClient:
    def __init__(self):
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = GROK_API_KEY
        self.model = "grok-3.1"
        self.max_retries = 3
        self.session = requests.Session()
        self.session.mount("https://", TLSAdapter())

    def call_grok(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(self.endpoint, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                return result.get("output_text", "[ERROR: respuesta vacía de Grok]")
            except Exception as e:
                logger.warning(f"Error con Grok (intento {attempt+1}): {e}")
                time.sleep(2 ** attempt)
        logger.error("Todos los intentos con Grok fallaron")
        return f"[ERROR: No se pudo procesar con Grok. Prompt: {prompt[:100]}...]"

# =====================================================
# Pipeline completo: anonimización → LLM → desanonimización
# =====================================================
class AnonymizationPipeline:
    def __init__(self):
        self.generator = SyntheticDataGenerator()
        self.llm_client = LLMClient()

    def anonymize(self, text: str, mapping: Dict[str, str]) -> str:
        anonymized = text
        for token, original_value in mapping.items():
            entity_type = token.strip('[]').split('_')[0]
            replacement = self.generator.generate_synthetic_replacement(entity_type, original_value)
            anonymized = anonymized.replace(original_value, replacement)
        return anonymized

    def de_anonymize(self, text: str) -> str:
        de_anonymized = text
        for synthetic, original in self.generator.reverse_cache.items():
            de_anonymized = de_anonymized.replace(synthetic, original)
        return de_anonymized

    def run_pipeline(self, 
                     text: str, 
                     model: str = "es", 
                     use_regex: bool = True, 
                     pseudonymize: bool = False,
                     llm_prompt_template: Optional[str] = None) -> Dict[str, Any]:
        try:
            logger.info("Detectando PII...")
            pii_result = pii_run_pipeline(model=model, text=text, use_regex=use_regex, pseudonymize=pseudonymize)
            mapping = pii_result.get("mapping", {})

            if not mapping:
                logger.info("No se detectó PII, enviando texto original al LLM")
                llm_response = self.llm_client.call_grok(text)
                return {
                    "original_text": text,
                    "anonymized_text": text,
                    "pii_detected": False,
                    "pii_mapping": {},
                    "llm_response": llm_response,
                    "final_response": llm_response,
                    "success": True
                }

            logger.info(f"Anonimizando {len(mapping)} entidades PII...")
            anonymized = self.anonymize(text, mapping)

            if llm_prompt_template:
                llm_prompt = llm_prompt_template.format(text=anonymized)
            else:
                llm_prompt = f"Procesa el siguiente texto: {anonymized}"

            logger.info("Enviando al LLM (Grok)...")
            llm_response = self.llm_client.call_grok(llm_prompt)
            final_response = self.de_anonymize(llm_response)

            return {
                "original_text": text,
                "anonymized_text": anonymized,
                "pii_detected": True,
                "pii_mapping": mapping,
                "llm_prompt": llm_prompt,
                "llm_response": llm_response,
                "final_response": final_response,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error en el pipeline: {str(e)}")
            return {
                "original_text": text,
                "error": str(e),
                "success": False
            }

# =====================================================
# Ejemplo de uso
# =====================================================
def main():
    pipeline = AnonymizationPipeline()

    text = """
    Hola, soy Juan Pérez García y trabajo en Telefónica España.
    Mi email es juan.perez@telefonica.com y mi teléfono es +34 666 123 456.
    Mi DNI es 12345678Z y vivo en Madrid.
    Por favor, contacta conmigo para discutir el proyecto.
    """

    print("=" * 60)
    print("PIPELINE DE ANONIMIZACIÓN CON LLM (GROK)")
    print("=" * 60)
    print(f"Texto original:\n{text}")
    print("\n" + "=" * 60)

    result = pipeline.run_pipeline(
        text=text,
        model="es",
        llm_prompt_template="Reescribe este texto de manera más formal y profesional: {text}"
    )

    if result["success"]:
        print(f"PII detectado: {result['pii_detected']}")
        if result['pii_detected']:
            print(f"Texto anonimizado:\n{result['anonymized_text']}")
            print(f"\nEntidades PII encontradas: {list(result['pii_mapping'].keys())}")
        print(f"\nRespuesta del LLM:\n{result['llm_response']}")
        print(f"\nRespuesta final (de-anonimizada):\n{result['final_response']}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
