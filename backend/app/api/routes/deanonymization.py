"""
Shield AI - Deanonymization Router

FastAPI router for deanonymization endpoints.
Delegates business logic to service layer.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import service layer functions
from services.deanonymization_service import (
    dummy_anonymization_map,
    process_deanonymization,
    generate_dual_stream,
    generate_deanonymized_stream,
    test_full_process
)
from services.session_manager import get_anonymization_map, store_anonymization_map
from models.requests import DeAnonymizationRequest

# Create router instance
router = APIRouter(prefix="/deanonymize", tags=["deanonymization"])


# === REQUEST MODELS ===

class StreamingDeAnonymizationRequest(BaseModel):
    """Request model for streaming deanonymization."""
    session_id: str


# === ENDPOINTS ===

@router.post("/", response_model=dict)
async def deanonymize_text_endpoint(request: DeAnonymizationRequest):
    """
    Deanonymize text using session's anonymization map.
    
    HTTP layer - delegates business logic to service.
    """
    try:
        # Get session's anonymization map
        anonymization_map = get_anonymization_map(request.session_id)
        if not anonymization_map:
            raise HTTPException(
                status_code=404,
                detail=f"Anonymization map not found for session: {request.session_id}"
            )
        
        # Delegate to service layer
        result = process_deanonymization(
            request.session_id,
            request.model_response,
            anonymization_map
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/stream-dual")
async def stream_dual_response(request: StreamingDeAnonymizationRequest):
    """
    Stream dual anonymous and deanonymized text side by side.
    
    HTTP layer - delegates streaming logic to service.
    """
    try:
        # Get session's anonymization map
        anonymization_map = get_anonymization_map(request.session_id)
        if not anonymization_map:
            raise HTTPException(
                status_code=404,
                detail=f"Anonymization map not found for session: {request.session_id}"
            )
        
        # Delegate streaming to service layer
        return StreamingResponse(
            generate_dual_stream(request.session_id, anonymization_map),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up dual stream: {str(e)}")


@router.post("/stream")
async def stream_deanonymized_response(request: StreamingDeAnonymizationRequest):
    """
    Stream deanonymized text only.
    
    HTTP layer - delegates streaming logic to service.
    """
    try:
        # Get session's anonymization map
        anonymization_map = get_anonymization_map(request.session_id)
        if not anonymization_map:
            raise HTTPException(
                status_code=404,
                detail=f"Anonymization map not found for session: {request.session_id}"
            )
        
        # Delegate streaming to service layer
        return StreamingResponse(
            generate_deanonymized_stream(request.session_id, anonymization_map),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up deanonymized stream: {str(e)}")


@router.get("/test/{session_id}")
async def test_deanonymization_process(session_id: str):
    """
    Test complete deanonymization process.
    
    HTTP layer - delegates test logic to service.
    """
    try:
        # Delegate test process to service layer
        result = test_full_process(session_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/setup-dummy/{session_id}")
async def setup_dummy_session(session_id: str):
    """
    Setup dummy session for testing.
    
    HTTP layer - delegates setup to service.
    """
    try:
        # Get dummy map from service and store it
        dummy_map = dummy_anonymization_map()
        store_anonymization_map(session_id, dummy_map)
        
        return {
            "message": f"Dummy session {session_id} configured successfully",
            "session_id": session_id,
            "anonymization_map": dummy_map
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up dummy session: {str(e)}")