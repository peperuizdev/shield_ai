import os
import sys
import json
import time
import ssl
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('llm_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("SHIELD_AI_GROK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not any([GROK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY]):
    logger.warning("No se encontraron claves de API para LLM")

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

class MultiProviderLLMClient:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.session = requests.Session()
        self.session.mount("https://", EnhancedTLSAdapter())
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def _initialize_providers(self) -> List[LLMConfig]:
        """Inicializa configuraciones de múltiples proveedores con modelos actuales"""
        providers = []
        
        if GROK_API_KEY:
            groq_models = [
                "gemma2-9b-it",
                "deepseek-r1-distill-llama-70b",
                "allam-2-7b",
                "meta-llama/llama-4-scout-17b-16e-instruct"
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

class LLMClientPropuesta:
    def __init__(self):
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = GROK_API_KEY
        self.model = "llama-3.1-8b-instant"
        self.max_retries = 3
        self.session = requests.Session()
        self.session.mount("https://", EnhancedTLSAdapter())
        
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
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 400:
                    error_detail = response.json() if response.content else {"error": "Bad Request"}
                    logger.error(f"Error 400 - Payload: {payload}")
                    logger.error(f"Error 400 - Response: {error_detail}")
                    return f"[ERROR: Bad Request - {error_detail.get('error', {}).get('message', 'Formato incorrecto')}]"
                
                response.raise_for_status()
                result = response.json()
                
                logger.debug(f"Respuesta completa de Groq: {result}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"].strip()
                        if content:
                            logger.info("Respuesta exitosa de Groq")
                            return content
                
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
                    time.sleep(2 ** (attempt + 2))
                    continue
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"Error de conexión en intento {attempt+1}")
                if attempt == self.max_retries - 1:
                    return "[ERROR: No se puede conectar a Groq API]"
                    
            except Exception as e:
                logger.warning(f"Error inesperado en intento {attempt+1}: {type(e).__name__}: {e}")
                
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
            "stream": True
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Enviando streaming request a Groq (intento {attempt + 1}/{self.max_retries})")
                
                response = self.session.post(
                    self.endpoint, 
                    headers=headers, 
                    json=payload, 
                    timeout=30,
                    stream=True
                )
                
                response.raise_for_status()
                logger.info(f"Streaming response status: {response.status_code}")
                
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8').strip()
                        
                        if line_text.startswith('data: '):
                            data_json = line_text[6:]
                            
                            if data_json.strip() == '[DONE]':
                                logger.info("Stream completado correctamente")
                                return
                            
                            try:
                                data = json.loads(data_json)
                                
                                if 'choices' in data and len(data['choices']) > 0:
                                    choice = data['choices'][0]
                                    if 'delta' in choice and 'content' in choice['delta']:
                                        chunk_content = choice['delta']['content']
                                        if chunk_content:
                                            yield chunk_content
                                            
                            except json.JSONDecodeError:
                                continue
                            except KeyError:
                                continue
                
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
                
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Esperando {wait_time}s antes del siguiente intento de streaming...")
                time.sleep(wait_time)
        
        logger.error("Todos los intentos de streaming con Groq fallaron")
        yield f"[ERROR: No se pudo hacer streaming con Groq después de {self.max_retries} intentos]"

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