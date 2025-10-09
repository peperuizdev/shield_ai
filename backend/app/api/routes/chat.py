"""
Endpoint de chat que integra:
1. Pipeline de anonimización del equipo (sin tocar)
2. MultiProviderLLMClient para Grok, OpenAI y Anthropic
3. Sistema de desanonimización propio
4. Sistema de datos sintéticos mejorado

CAMBIOS REALIZADOS EN ESTE ARCHIVO:
- Importar synthetic_data_generator para unificar generación de datos falsos
- Modificar endpoint /streaming para retornar StreamingResponse real
- Usar generate_real_time_dual_stream() para streaming SSE correcto
- Guardar texto anonimizado en Redis para que test.html pueda cargarlo
- FORZAR use_realistic_fake=True para siempre usar datos sintéticos realistas
- ELIMINAR post-procesamiento redundante (PASO 2.2) ya que pii_detector lo hace
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
import logging
import time
import json

from services.llm_integration import MultiProviderLLMClient, LLMClientPropuesta
from services.deanonymization_service import generate_real_time_dual_stream

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

def anonymize_with_existing_map(text: str, existing_mapping: Dict[str, str]) -> str:
    """
    Anonimiza texto usando un mapa existente de anonimización.
    """
    result = text
    inverted_map = {real_name: fake_name for fake_name, real_name in existing_mapping.items()}
    sorted_items = sorted(inverted_map.items(), key=lambda x: len(x[0]), reverse=True)
    for real_data, fake_data in sorted_items:
        if real_data in result:
            result = result.replace(real_data, fake_data)
            logger.debug(f"✅ Reemplazo: '{real_data}' -> '{fake_data}'")
    logger.debug(f"Anonimizado con mapa existente: '{text}' -> '{result}'")
    return result

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    llm_prompt_template: Optional[str] = None
    model: Optional[str] = "es"
    use_regex: Optional[bool] = True
    pseudonymize: Optional[bool] = False
    save_mapping: Optional[bool] = True
    use_realistic_fake: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str]
    pii_detected: bool
    processing_time: float
    anonymized_used: bool
    llm_model: str

@router.post("/streaming")
async def chat_stream_propuesta(request: ChatRequest):
    try:
        start_time = time.time()
        session_id = request.session_id or f"stream_session_{int(time.time())}"
        existing_mapping = None

        # PASO 1: OBTENER MAPA EXISTENTE
        if request.save_mapping and session_id:
            try:
                from services.session.anonymization import get_anonymization_map
                existing_mapping = get_anonymization_map(session_id)
                logger.info(f"MAPA EXISTENTE ENCONTRADO para sesión {session_id}: {len(existing_mapping)} entidades")
            except Exception:
                existing_mapping = None

        # PASO 2: ANONIMIZACIÓN
        if existing_mapping:
            anonymized_text = anonymize_with_existing_map(request.message, existing_mapping)
            mapping = existing_mapping
            pii_detected = True
        else:
            try:
                from services.pii_detector import run_pipeline
            except ImportError:
                raise HTTPException(status_code=500, detail="Pipeline de anonimización no disponible")

            anonymization_result = run_pipeline(
                model=request.model,
                text=request.message,
                use_regex=request.use_regex,
                pseudonymize=False,
                save_mapping=False,
                use_realistic_fake=True
            )
            anonymized_text = anonymization_result.get('anonymized', request.message)
            mapping = anonymization_result.get('mapping', {})
            pii_detected = bool(mapping)

        # PASO 3: GUARDAR MAPA EN REDIS
        if mapping and request.save_mapping:
            try:
                from services.session.anonymization import store_anonymization_map
                from services.session.llm_data import store_anonymized_request
                store_anonymization_map(session_id, mapping)
                store_anonymized_request(session_id, anonymized_text)
                logger.info(f"✅ Texto anonimizado guardado en Redis para sesión {session_id}")
            except Exception as e:
                logger.warning(f"No se pudo guardar mapa en Redis: {e}")

        # PASO 4: PREPARAR PROMPT PARA LLM
        if request.llm_prompt_template:
            llm_prompt = request.llm_prompt_template.format(text=anonymized_text)
        else:
            llm_prompt = f"Actúa como un asistente útil, en caso de que proporcione nombre no lo abrevies, ignora diferencias entre el nombre y el correo (no digas nada al respecto), si hay algun numero de telefono devuelve sus espacios con guiones solo en este formato por ejemplo (+34-654-768-750) de igual forma responde de manera clara y completa a la siguiente consulta: {anonymized_text}"

        # PASO 5: RETORNAR STREAMING RESPONSE REAL
        llm_client = LLMClientPropuesta()
        
        return StreamingResponse(
            generate_real_time_dual_stream(
                session_id=session_id,
                llm_prompt=llm_prompt,
                mapping=mapping,
                llm_client=llm_client
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en chat streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en streaming: {str(e)}")

@router.post("/test-anonymization-consistency")
async def test_anonymization_consistency(request: ChatRequest):
    try:
        from services.session.anonymization import get_anonymization_map, store_anonymization_map
        session_id = request.session_id or "test_consistency"

        try:
            existing_map = get_anonymization_map(session_id)
            has_existing_map = True
        except:
            existing_map = None
            has_existing_map = False

        if has_existing_map:
            anonymized = anonymize_with_existing_map(request.message, existing_map)
            action = "used_existing_map"
        else:
            anonymized = request.message.replace("Juan Pérez", "María González").replace("Madrid", "Barcelona")
            action = "created_new_map"
            simple_map = {"Juan Pérez": "María González", "Madrid": "Barcelona"}
            try:
                store_anonymization_map(session_id, simple_map)
            except Exception as e:
                logger.warning(f"No se pudo guardar mapa simple: {e}")

        return {
            "session_id": session_id,
            "original_message": request.message,
            "anonymized_message": anonymized,
            "action": action,
            "has_existing_map": has_existing_map,
            "existing_map_size": len(existing_map) if existing_map else 0,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error en test de consistencia: {e}")
        raise HTTPException(status_code=500, detail=f"Error en test: {str(e)}")