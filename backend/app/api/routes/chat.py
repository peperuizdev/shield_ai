"""
Shield AI - Chat Router

Endpoint de chat que integra:
1. Pipeline de anonimización del equipo (sin tocar)
2. LLMClient existente para Grok
3. Sistema de desanonimización propio
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import time
import json

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

# === REQUEST/RESPONSE MODELS ===

class ChatRequest(BaseModel):
    message: str                                    # Prompt del usuario
    session_id: Optional[str] = None               # Para guardar mapas en Redis
    llm_prompt_template: Optional[str] = None      # Template personalizado para LLM
    model: Optional[str] = "es"                    # Idioma para PII detection
    use_regex: Optional[bool] = True               # Detectar PII con regex
    pseudonymize: Optional[bool] = True            # Usar pseudónimos realistas
    save_mapping: Optional[bool] = True            # Guardar mapa en Redis
    use_realistic_fake: Optional[bool] = True      # Usar datos falsos realistas con Faker (por defecto)

class ChatResponse(BaseModel):
    response: str                    # Respuesta final al usuario
    session_id: Optional[str]        # ID de sesión usado
    pii_detected: bool              # Si se detectó información sensible
    processing_time: float          # Tiempo total de procesamiento
    anonymized_used: bool           # Si se usó anonimización
    llm_model: str                  # Modelo LLM utilizado

class StreamingChatRequest(BaseModel):
    session_id: str                 # ID de sesión para streaming
    llm_prompt_template: Optional[str] = None  # Template para LLM

# === MAIN CHAT ENDPOINT ===

@router.post("/", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    """
    Endpoint principal de chat que:
    1. Usa pipeline de anonimización del equipo (sin modificar)
    2. Envía prompt anonimizado al LLMClient existente
    3. Usa sistema de desanonimización propio para respuesta final
    """
    try:
        start_time = time.time()
        
        # ===== PASO 1: ANONIMIZACIÓN USANDO PIPELINE DEL EQUIPO =====
        try:
            # Import dinámico para evitar startup issues
            from services.pii_detector import run_pipeline
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Pipeline de anonimización no disponible"
            )

        # Usar exactamente el mismo pipeline que usa el endpoint /anonymize
        anonymization_result = run_pipeline(
            model=request.model,
            text=request.message,
            use_regex=request.use_regex,
            pseudonymize=request.pseudonymize,
            save_mapping=False,  # Lo guardaremos nosotros en Redis si es necesario
            use_realistic_fake=request.use_realistic_fake
        )
        
        anonymized_text = anonymization_result.get('anonymized', request.message)
        mapping = anonymization_result.get('mapping', {})
        pii_detected = bool(mapping)
        
        logger.info(f"PII detectado: {pii_detected}, entidades: {len(mapping)}")
        
        # ===== PASO 2: GUARDAR MAPA EN REDIS SI ES NECESARIO =====
        if request.save_mapping and request.session_id and mapping:
            try:
                from services.session_manager import store_anonymization_map
                store_anonymization_map(request.session_id, mapping)
                logger.info(f"Mapa guardado en Redis para sesión {request.session_id}")
            except Exception as e:
                logger.warning(f"No se pudo guardar mapa en Redis: {e}")
        
        # ===== PASO 3: ENVÍO AL LLM USANDO CLIENTE EXISTENTE =====
        try:
            from services.llm_integration import LLMClient
            
            # Verificar que tenemos API key
            import os
            api_key = os.getenv("GROK_API_KEY") or os.getenv("SHIELD_AI_GROK_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="GROK_API_KEY no configurada en variables de entorno"
                )
                
        except ImportError as e:
            logger.error(f"Error importando LLMClient: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cliente LLM no disponible: {str(e)}"
            )
        
        llm_client = LLMClient()
        
        # Preparar prompt para LLM
        if request.llm_prompt_template:
            llm_prompt = request.llm_prompt_template.format(text=anonymized_text)
        else:
            # Template por defecto para chat conversacional
            llm_prompt = f"Actúa como un asistente útil y responde de manera clara y completa a la siguiente consulta: {anonymized_text}"
        
        logger.info("Enviando consulta a Grok LLM...")
        llm_response = llm_client.call_grok(llm_prompt)
        
        # ===== PASO 4: DESANONIMIZACIÓN USANDO SISTEMA PROPIO =====
        final_response = llm_response
        
        if pii_detected and mapping:
            try:
                # Usar función de desanonimización existente
                from services.deanonymization_service import create_reverse_map, deanonymize_text
                
                # Crear mapa inverso (datos_falsos -> datos_originales)
                reverse_map = create_reverse_map(mapping)
                
                # Desanonimizar respuesta del LLM
                final_response = deanonymize_text(llm_response, reverse_map)
                
                logger.info("Respuesta desanonimizada exitosamente")
                
            except Exception as e:
                logger.error(f"Error en desanonimización: {e}")
                # Si falla desanonimización, devolver respuesta anonimizada
                final_response = llm_response
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=final_response,
            session_id=request.session_id,
            pii_detected=pii_detected,
            processing_time=round(processing_time, 3),
            anonymized_used=pii_detected,
            llm_model="mixtral-8x7b-32768"  # Modelo usado por LLMClient
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error procesando consulta: {str(e)}"
        )

# === STREAMING CHAT ENDPOINT CON DUAL STREAM ===

@router.post("/stream-propuesta")
async def chat_stream_propuesta(request: ChatRequest):
    """
    Endpoint de chat con streaming dual que muestra:
    1. Stream anónimo: Lo que ve el LLM (datos falsos)
    2. Stream deanonymizado: Lo que ve el usuario (datos reales)
    
    Combina chat + anonimización + LLM + dual streaming en un solo endpoint.
    """
    try:
        # ===== PASO 1: ANONIMIZACIÓN USANDO PIPELINE DEL EQUIPO =====
        try:
            from services.pii_detector import run_pipeline
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Pipeline de anonimización no disponible"
            )

        anonymization_result = run_pipeline(
            model=request.model,
            text=request.message,
            use_regex=request.use_regex,
            pseudonymize=request.pseudonymize,
            save_mapping=False,
            use_realistic_fake=request.use_realistic_fake
        )
        
        anonymized_text = anonymization_result.get('anonymized', request.message)
        mapping = anonymization_result.get('mapping', {})
        pii_detected = bool(mapping)
        
        logger.info(f"PII detectado para streaming: {pii_detected}, entidades: {len(mapping)}")
        
        # ===== PASO 2: GUARDAR MAPA EN REDIS =====
        session_id = request.session_id or f"stream_session_{int(time.time())}"
        
        if mapping:
            try:
                from services.session_manager import store_anonymization_map
                store_anonymization_map(session_id, mapping)
                logger.info(f"Mapa guardado para streaming en sesión {session_id}")
            except Exception as e:
                logger.warning(f"No se pudo guardar mapa en Redis: {e}")
        
        # ===== PASO 3: OBTENER RESPUESTA DEL LLM =====
        try:
            from services.llm_integration import LLMClientPropuesta
        except ImportError as e:
            logger.error(f"Error importando LLMClientPropuesta: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cliente LLM Propuesta no disponible: {str(e)}"
            )
        
        llm_client = LLMClientPropuesta()
        
        if request.llm_prompt_template:
            llm_prompt = request.llm_prompt_template.format(text=anonymized_text)
        else:
            llm_prompt = f"Actúa como un asistente útil y responde de manera clara y completa a la siguiente consulta: {anonymized_text}"
        
        logger.info("Obteniendo respuesta del LLM para streaming...")
        llm_response = llm_client.call_grok(llm_prompt)
        
        # ===== PASO 4: GUARDAR RESPUESTA DEL LLM EN REDIS PARA STREAMING =====
        try:
            from services.session_manager import store_llm_response
            store_llm_response(session_id, llm_response)
            logger.info("Respuesta del LLM guardada para streaming")
        except Exception as e:
            logger.warning(f"No se pudo guardar respuesta del LLM: {e}")
        
        # ===== PASO 5: GENERAR STREAMING DUAL =====
        from services.deanonymization_service import generate_chat_dual_stream
        
        return StreamingResponse(
            generate_chat_dual_stream(session_id, llm_response, mapping),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en chat streaming: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en streaming: {str(e)}"
        )

# === STREAMING CHAT ENDPOINT ===

@router.post("/stream")
async def chat_stream_with_llm(request: StreamingChatRequest):
    """
    Endpoint de streaming para chat en tiempo real.
    Usa el mapa de anonimización guardado en la sesión.
    """
    try:
        # Verificar que existe mapa de anonimización en la sesión
        from services.session_manager import get_anonymization_map
        
        anonymization_map = get_anonymization_map(request.session_id)
        if not anonymization_map:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró mapa de anonimización para sesión: {request.session_id}"
            )
        
        # Usar streaming de desanonimización existente con LLM
        from services.deanonymization_service import generate_deanonymized_stream_get
        
        return StreamingResponse(
            generate_deanonymized_stream_get(request.session_id, anonymization_map),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en streaming chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en streaming: {str(e)}"
        )

# === CHAT ENDPOINT CON LLM CLIENT PROPUESTA ===

@router.post("/propuesta", response_model=ChatResponse)
async def chat_with_llm_propuesta(request: ChatRequest):
    """
    Endpoint de chat usando LLMClientPropuesta mejorado:
    1. Usa pipeline de anonimización del equipo (sin modificar)
    2. Envía prompt anonimizado al LLMClientPropuesta mejorado
    3. Usa sistema de desanonimización propio para respuesta final
    """
    try:
        start_time = time.time()
        
        # ===== PASO 1: ANONIMIZACIÓN USANDO PIPELINE DEL EQUIPO =====
        try:
            from services.pii_detector import run_pipeline
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Pipeline de anonimización no disponible"
            )

        anonymization_result = run_pipeline(
            model=request.model,
            text=request.message,
            use_regex=request.use_regex,
            pseudonymize=request.pseudonymize,
            save_mapping=False,
            use_realistic_fake=request.use_realistic_fake
        )
        
        anonymized_text = anonymization_result.get('anonymized', request.message)
        mapping = anonymization_result.get('mapping', {})
        pii_detected = bool(mapping)
        
        logger.info(f"PII detectado: {pii_detected}, entidades: {len(mapping)}")
        
        # ===== PASO 2: GUARDAR MAPA EN REDIS SI ES NECESARIO =====
        if request.save_mapping and request.session_id and mapping:
            try:
                from services.session_manager import store_anonymization_map
                store_anonymization_map(request.session_id, mapping)
                logger.info(f"Mapa guardado en Redis para sesión {request.session_id}")
            except Exception as e:
                logger.warning(f"No se pudo guardar mapa en Redis: {e}")
        
        # ===== PASO 3: ENVÍO AL LLM USANDO CLIENTE MEJORADO =====
        try:
            from services.llm_integration import LLMClientPropuesta
        except ImportError as e:
            logger.error(f"Error importando LLMClientPropuesta: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cliente LLM Propuesta no disponible: {str(e)}"
            )
        
        llm_client = LLMClientPropuesta()
        
        # Preparar prompt para LLM
        if request.llm_prompt_template:
            llm_prompt = request.llm_prompt_template.format(text=anonymized_text)
        else:
            llm_prompt = f"Actúa como un asistente útil y responde de manera clara y completa a la siguiente consulta: {anonymized_text}"
        
        logger.info("Enviando consulta a Grok LLM (Propuesta)...")
        llm_response = llm_client.call_grok(llm_prompt)
        
        # ===== PASO 4: DESANONIMIZACIÓN USANDO SISTEMA PROPIO =====
        final_response = llm_response
        
        if pii_detected and mapping and not "[ERROR:" in llm_response:
            try:
                from services.deanonymization_service import create_reverse_map, deanonymize_text
                
                # Debug: log del mapping para diagnóstico
                logger.info(f"Mapping original: {mapping}")
                
                reverse_map = create_reverse_map(mapping)
                logger.info(f"Reverse map: {reverse_map}")
                
                final_response = deanonymize_text(llm_response, reverse_map)
                
                logger.info("Respuesta desanonimizada exitosamente")
                logger.info(f"Respuesta antes: {llm_response[:100]}...")
                logger.info(f"Respuesta después: {final_response[:100]}...")
                
            except Exception as e:
                logger.error(f"Error en desanonimización: {e}")
                final_response = llm_response
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=final_response,
            session_id=request.session_id,
            pii_detected=pii_detected,
            processing_time=round(processing_time, 3),
            anonymized_used=pii_detected,
            llm_model="llama3-8b-8192"  # Modelo usado por LLMClientPropuesta
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en chat propuesta endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error procesando consulta: {str(e)}"
        )

# === ENDPOINT DE CONFIGURACIÓN ===

@router.post("/setup-test/{session_id}")
async def setup_test_chat_session(session_id: str):
    """
    Configurar sesión de prueba para chat.
    Usa la misma funcionalidad que el sistema de desanonimización.
    """
    try:
        from services.deanonymization_service import dummy_anonymization_map
        from services.session_manager import store_anonymization_map
        
        # Usar el mapa dummy existente
        dummy_map = dummy_anonymization_map()
        store_anonymization_map(session_id, dummy_map)
        
        return {
            "message": f"Sesión de chat {session_id} configurada para pruebas",
            "session_id": session_id,
            "anonymization_map": dummy_map,
            "chat_ready": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error configurando sesión de prueba: {str(e)}"
        )

# === ENDPOINT DE STATUS ===

@router.get("/status")
async def chat_service_status():
    """
    Verificar estado de los servicios necesarios para chat.
    """
    status = {
        "chat_service": "available",
        "pii_detection": False,
        "llm_client": False,
        "llm_client_propuesta": False,
        "deanonymization": False,
        "redis_session": False,
        "timestamp": time.time()
    }
    
    # Verificar PII detection
    try:
        from services.pii_detector import run_pipeline
        status["pii_detection"] = True
    except:
        pass
    
    # Verificar LLM client original
    try:
        from services.llm_integration import LLMClient
        status["llm_client"] = True
    except:
        pass
    
    # Verificar LLM client propuesta
    try:
        from services.llm_integration import LLMClientPropuesta
        status["llm_client_propuesta"] = True
    except:
        pass
    
    # Verificar desanonimización
    try:
        from services.deanonymization_service import deanonymize_text
        status["deanonymization"] = True
    except:
        pass
    
    # Verificar Redis
    try:
        from services.session_manager import get_anonymization_map
        status["redis_session"] = True
    except:
        pass
    
    status["all_services_ready"] = all([
        status["pii_detection"],
        status["llm_client"], 
        status["deanonymization"],
        status["redis_session"]
    ])
    
    status["all_services_ready_propuesta"] = all([
        status["pii_detection"],
        status["llm_client_propuesta"], 
        status["deanonymization"],
        status["redis_session"]
    ])
    
    return status

# === ENDPOINT PARA PROBAR LLM CLIENT PROPUESTA ===

@router.post("/test-llm-propuesta")
async def test_llm_client_propuesta(request: dict):
    """
    Endpoint para probar la nueva clase LLMClientPropuesta.
    """
    try:
        from services.llm_integration import LLMClientPropuesta
        
        client = LLMClientPropuesta()
        
        # Test de conexión
        connection_test = client.test_connection()
        
        # Test con prompt personalizado si se proporciona
        prompt = request.get("prompt", "Hola, ¿puedes responder en español?")
        
        if connection_test["status"] == "success":
            start_time = time.time()
            response = client.call_grok(prompt)
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "connection_test": connection_test,
                "prompt": prompt,
                "response": response,
                "processing_time": round(processing_time, 3),
                "model_used": client.model
            }
        else:
            return {
                "status": "connection_failed",
                "connection_test": connection_test,
                "prompt": prompt
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "prompt": request.get("prompt", "")
        }