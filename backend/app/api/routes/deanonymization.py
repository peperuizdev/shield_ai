"""
Shield AI - Deanonymization Router

FastAPI router for deanonymization endpoints.
Delegates business logic to service layer.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

# Import service layer functions
from services.deanonymization_service import (
    dummy_anonymization_map,
    process_deanonymization,
    generate_dual_stream,
    generate_deanonymized_stream,
    generate_dual_stream_get,
    generate_deanonymized_stream_get,
    test_full_process
)

from services.session_manager import store_anonymization_map

router = APIRouter(prefix="/deanonymize", tags=["Deanonymization"])

class DeAnonymizationRequest(BaseModel):
    text: str
    session_id: str

class StreamingDeAnonymizationRequest(BaseModel):
    session_id: str

# =====================================================
# MAIN DEANONYMIZATION ENDPOINT
# =====================================================

@router.post("/")
async def deanonymize_text_endpoint(request: DeAnonymizationRequest):
    """
    Deanonymize text using session data.
    
    HTTP layer - delegates processing to service.
    """
    try:
        result = process_deanonymization(request.text, request.session_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing deanonymization: {str(e)}")

# =====================================================
# STREAMING ENDPOINTS (POST)
# =====================================================

@router.post("/stream-dual")
async def stream_dual_deanonymization(request: StreamingDeAnonymizationRequest):
    """
    Stream dual response (anonymous + deanonymized) for a session.
    
    Returns real-time stream with both anonymous and deanonymized content.
    """
    try:
        return StreamingResponse(
            generate_dual_stream(request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in dual streaming: {str(e)}")

@router.post("/stream")
async def stream_deanonymization(request: StreamingDeAnonymizationRequest):
    """
    Stream deanonymized response for a session.
    
    Returns real-time stream with deanonymized content only.
    """
    try:
        return StreamingResponse(
            generate_deanonymized_stream(request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in deanonymization streaming: {str(e)}")

# =====================================================
# STREAMING ENDPOINTS (GET - for backwards compatibility)
# =====================================================

@router.get("/dual-stream/{session_id}")
async def dual_stream_get(session_id: str):
    """
    GET version of dual stream for backward compatibility.
    """
    try:
        return StreamingResponse(
            generate_dual_stream_get(session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in dual streaming: {str(e)}")

@router.get("/deanonymize-stream/{session_id}")
async def deanonymize_stream_get(session_id: str):
    """
    GET version of deanonymization stream for backward compatibility.
    """
    try:
        return StreamingResponse(
            generate_deanonymized_stream_get(session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in deanonymization streaming: {str(e)}")

# =====================================================
# TESTING ENDPOINTS
# =====================================================

@router.get("/test/{session_id}")
async def test_deanonymization_process(session_id: str):
    """
    Test complete deanonymization process with dummy data.
    """
    try:
        result = test_full_process(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in test process: {str(e)}")

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