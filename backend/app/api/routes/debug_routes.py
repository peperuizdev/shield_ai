"""
Debug endpoint para inspeccionar mapas de anonimización en Redis
"""
from fastapi import APIRouter, HTTPException
import logging

router = APIRouter(prefix="/debug", tags=["Debug"])
logger = logging.getLogger(__name__)

@router.get("/session/{session_id}/mapping")
async def debug_session_mapping(session_id: str):
    """
    Debug: Ver el mapa de anonimización guardado en Redis para una sesión.
    """
    try:
        from services.session.anonymization import get_anonymization_map
        
        mapping = get_anonymization_map(session_id)
        
        return {
            "session_id": session_id,
            "mapping_found": mapping is not None,
            "mapping": mapping,
            "mapping_type": type(mapping).__name__,
            "mapping_keys": list(mapping.keys()) if mapping else [],
            "mapping_values": list(mapping.values()) if mapping else [],
            "entry_count": len(mapping) if mapping else 0
        }
        
    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "mapping_found": False
        }

@router.get("/session/{session_id}/all-data")
async def debug_session_all_data(session_id: str):
    """
    Debug: Ver todos los datos guardados para una sesión.
    """
    try:
        from services.session.anonymization import get_anonymization_map
        from services.session.llm_data import get_anonymized_request, get_llm_response
        
        mapping = None
        anonymized_request = None
        llm_response = None
        
        try:
            mapping = get_anonymization_map(session_id)
        except:
            pass
            
        try:
            anonymized_request = get_anonymized_request(session_id)
        except:
            pass
            
        try:
            llm_response = get_llm_response(session_id)
        except:
            pass
        
        return {
            "session_id": session_id,
            "mapping": {
                "found": mapping is not None,
                "data": mapping,
                "count": len(mapping) if mapping else 0
            },
            "anonymized_request": {
                "found": anonymized_request is not None,
                "data": anonymized_request[:200] + "..." if anonymized_request and len(anonymized_request) > 200 else anonymized_request
            },
            "llm_response": {
                "found": llm_response is not None,
                "data": llm_response[:200] + "..." if llm_response and len(llm_response) > 200 else llm_response
            }
        }
        
    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e)
        }