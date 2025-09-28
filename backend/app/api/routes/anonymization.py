from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter(prefix="/anonymize")
logger = logging.getLogger(__name__)

class AnonymizeRequest(BaseModel):
    text: str
    model: Optional[str] = 'es'
    use_regex: Optional[bool] = False
    pseudonymize: Optional[bool] = False
    session_id: Optional[str] = None  # Guardar mapeo en Redis si se proporciona session_id

@router.post('/')
def anonymize(req: AnonymizeRequest):
    try:
        # Local import to avoid startup time for heavy deps
        from services.pii_detector import run_pipeline
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PII service not available: {exc}")

    out = run_pipeline(req.model, req.text, use_regex=req.use_regex, pseudonymize=req.pseudonymize, save_mapping=False)
    
    # Guardar mapeo en Redis si se proporciona session_id
    if req.session_id and out.get('mapping'):
        try:
            from services.session_manager import store_anonymization_map
            store_anonymization_map(req.session_id, out['mapping'])
        except Exception as e:
            # No fallar si Redis falla, pero loggear el error
            print(f"Warning: Failed to store mapping in Redis: {e}")
    
    return out

@router.get("/session/{session_id}/anonymized-request")
async def get_anonymized_request(session_id: str):
    """
    Obtiene el texto anonimizado que fue enviado al LLM para una sesión específica
    """
    print(f"🔥 ENDPOINT START: Getting anonymized request for session: {session_id}")
    logger.info(f"� ENDPOINT START: Getting anonymized request for session: {session_id}")
    
    try:
        from services.session_manager import get_anonymized_request, get_session_manager
        from core.redis_client import get_redis_client
        
        print(f"🔍 DEBUGGING session: {session_id}")
        logger.info(f"� DEBUGGING session: {session_id}")
        
        # Obtener texto anonimizado directamente
        print(f"🔍 Calling get_anonymized_request...")
        anonymized_text = get_anonymized_request(session_id)
        
        print(f"� Result from get_anonymized_request: {anonymized_text is not None}")
        logger.info(f"� Result from get_anonymized_request: {anonymized_text is not None}")
        
        if anonymized_text:
            print(f"📄 Text length: {len(anonymized_text)}")
            print(f"📄 Text preview: {anonymized_text[:50]}...")
        
        if not anonymized_text:
            print(f"❌ NO TEXT FOUND for session {session_id}")
            logger.error(f"❌ NO TEXT FOUND for session {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Anonymized request not found for session {session_id}. Make sure you've executed a chat first."
            )
        
        return {
            "session_id": session_id,
            "anonymized_request": anonymized_text,
            "text_length": len(anonymized_text),
            "preview": anonymized_text[:200] + "..." if len(anonymized_text) > 200 else anonymized_text
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting anonymized request for {session_id}: {exc}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")

@router.get("/debug-redis/{session_id}")
async def debug_redis_keys(session_id: str):
    """
    Debug endpoint para inspeccionar directamente todas las claves de Redis para una sesión
    """
    try:
        from services.session_manager import get_session_manager
        from core.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        manager = get_session_manager()
        
        # Buscar todas las claves relacionadas con esta sesión
        all_keys = redis_client.keys("*")
        session_keys = [key for key in all_keys if session_id in str(key)]
        
        # Claves específicas que deberían existir
        mapping_key = f"{manager.key_prefix}:{session_id}"
        llm_key = f"{manager.key_prefix}:llm:{session_id}"
        request_key = f"{manager.key_prefix}:request:{session_id}"
        
        result = {
            "session_id": session_id,
            "redis_prefix": manager.key_prefix,
            "all_session_keys": session_keys,
            "expected_keys": {
                "mapping_key": mapping_key,
                "llm_key": llm_key, 
                "request_key": request_key
            },
            "key_exists": {
                "mapping": redis_client.exists(mapping_key),
                "llm": redis_client.exists(llm_key),
                "request": redis_client.exists(request_key)
            },
            "key_ttl": {
                "mapping": redis_client.ttl(mapping_key),
                "llm": redis_client.ttl(llm_key),
                "request": redis_client.ttl(request_key)
            }
        }
        
        # Si existe la clave request, intentar obtener el valor
        if redis_client.exists(request_key):
            try:
                raw_value = redis_client.get(request_key)
                result["request_data"] = {
                    "raw_type": str(type(raw_value)),
                    "raw_length": len(raw_value) if raw_value else 0,
                    "decoded_preview": raw_value.decode('utf-8')[:100] if raw_value else None
                }
            except Exception as e:
                result["request_data"] = {"error": str(e)}
        
        return result
        
    except Exception as e:
        return {"error": str(e), "session_id": session_id}

@router.get("/test")
async def test_endpoint():
    """Test endpoint para verificar que el router funciona"""
    return {"message": "Anonymization router is working!", "routes": ["/", "/session/{id}/anonymized-request", "/debug-redis/{id}"]}