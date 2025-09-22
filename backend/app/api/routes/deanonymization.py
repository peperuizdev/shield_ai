"""
Shield AI - Deanonymization Router

FastAPI router containing all deanonymization endpoints and core logic.
"""

import asyncio
import json
from typing import AsyncGenerator, List, Tuple, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import shared infrastructure
from core.redis_client import get_redis_client
from services.session_manager import get_anonymization_map, store_anonymization_map
from models.requests import DeAnonymizationRequest

# Create router instance
router = APIRouter(prefix="/deanonymize", tags=["deanonymization"])


# === DEANONYMIZATION-SPECIFIC MODELS ===

class StreamingDeAnonymizationRequest(BaseModel):
    """Request model for streaming deanonymization."""
    session_id: str


# === DUMMY FUNCTIONS FOR LLM SIMULATION ===

def dummy_anonymization_map() -> Dict[str, str]:
    """
    Function that simulates a typical anonymization map
    that would have been generated in the previous anonymization process.
    """
    return {
        # Full names
        "Juan Pérez": "María González",
        # Emails
        "juan.perez@email.com": "maria.gonzalez@email.com", 
        # Phones
        "612345678": "687654321",
        # DNIs
        "12345678A": "87654321B",
        # Addresses - keep base address same to avoid issues
        "Calle Mayor 123": "Avenida Libertad 456",
        # Cities
        "Madrid": "Barcelona",
        # Postal codes
        "28001": "08001",
        # Banks
        "Banco Santander": "Banco BBVA",
        # IBANs
        "ES91 2100 0418 4502 0005 1332": "ES76 0182 6473 8901 2345 6789"
    }


async def dummy_llm_response_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Dummy function that simulates LLM streaming response
    with anonymized data.
    """
    response_text = """Hola María González, gracias por contactar con nosotros desde Barcelona. 
    Hemos recibido tu consulta sobre los servicios bancarios del Banco BBVA. 
    Confirmo que hemos registrado tu información:
    - Email: maria.gonzalez@email.com
    - Teléfono: 687654321
    - DNI: 87654321B
    - Dirección: Avenida Libertad 456, Barcelona, 08001
    - IBAN: ES76 0182 6473 8901 2345 6789
    
    Procederemos con tu solicitud en las próximas 24 horas."""
    
    words = response_text.split()
    for word in words:
        await asyncio.sleep(0.3)  # Simulate streaming delay (increased for better readability)
        yield word + " "


# === MAIN DEANONYMIZATION FUNCTIONS ===

def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create reverse map for deanonymization
    (fake_data -> original_data)
    """
    return {fake_data: original_data for original_data, fake_data in anonymization_map.items()}


def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Replace anonymized data with original data in text.
    Maintains exact structure (spaces, punctuation, etc.)
    """
    result = text
    
    # Sort by length descending to avoid partial replacements
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        # Exact replacement maintaining structure
        result = result.replace(fake_data, original_data)
    
    return result


async def deanonymize_streaming_text(
    text_chunk: str, 
    reverse_map: Dict[str, str], 
    buffer: List[str]
) -> Tuple[str, List[str]]:
    """
    Deanonymize text in streaming, handling words that may be split
    across chunks.
    """
    # Add current chunk to buffer
    buffer.append(text_chunk)
    
    # Join buffer for processing
    full_text = ''.join(buffer)
    
    # Try to deanonymize full buffer text
    deanonymized = deanonymize_text(full_text, reverse_map)
    
    # If there are changes, means we found something to replace
    if deanonymized != full_text:
        # Clear buffer and return deanonymized text
        return deanonymized, []
    else:
        # If buffer is too long and no matches, release part of buffer
        if len(buffer) > 10:  # Keep only last elements
            result = ''.join(buffer[:-5])  # Return part of buffer
            return result, buffer[-5:]  # Keep last 5 chunks
        
        # No matches yet, maintain buffer
        return "", buffer


# === DEANONYMIZATION ENDPOINTS ===

@router.post("/")
async def deanonymize_response(request: DeAnonymizationRequest):
    """
    Deanonymize a complete response (without streaming).
    """
    try:
        # Get anonymization map
        anonymization_map = get_anonymization_map(request.session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        # Deanonymize text
        deanonymized_text = deanonymize_text(request.model_response, reverse_map)
        
        return {
            "session_id": request.session_id,
            "original_response": request.model_response,
            "deanonymized_response": deanonymized_text,
            "replacements_made": len([k for k, v in reverse_map.items() if k in request.model_response])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in deanonymization: {str(e)}")


@router.get("/dual-stream/{session_id}")
async def dual_streaming_response(session_id: str):
    """
    Streaming endpoint that sends both anonymized and deanonymized response simultaneously.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting dual stream for session: {session_id}")
        
        # Get anonymization map
        anonymization_map = get_anonymization_map(session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        async def generate_dual_stream():
            try:
                logger.debug("Generating LLM response chunks...")
                
                # First, collect full anonymized response
                anonymous_chunks = []
                async for chunk in dummy_llm_response_stream("dummy prompt"):
                    anonymous_chunks.append(chunk)
                
                logger.debug(f"Collected {len(anonymous_chunks)} chunks from LLM")
                
                # Rebuild complete anonymized text
                full_anonymous_text = ''.join(anonymous_chunks)
                
                # Deanonymize complete text preserving structure
                full_deanonymized_text = deanonymize_text(full_anonymous_text, reverse_map)
                
                logger.debug(f"Anonymous text length: {len(full_anonymous_text)}, Deanonymized text length: {len(full_deanonymized_text)}")
                
                # Now send both texts chunk by chunk synchronized
                anonymous_pos = 0
                deanonymized_pos = 0
                chunk_size = 2  # Send 2 characters at a time for more gradual effect
                
                chunks_sent = 0
                while anonymous_pos < len(full_anonymous_text) or deanonymized_pos < len(full_deanonymized_text):
                    # Send anonymized chunk
                    if anonymous_pos < len(full_anonymous_text):
                        anon_end = min(anonymous_pos + chunk_size, len(full_anonymous_text))
                        anon_chunk = full_anonymous_text[anonymous_pos:anon_end]
                        # Use json.dumps to properly escape the chunk
                        yield f"data: {json.dumps({'type': 'anonymous', 'chunk': anon_chunk})}\n\n"
                        anonymous_pos = anon_end
                    
                    # Send corresponding deanonymized chunk
                    if deanonymized_pos < len(full_deanonymized_text):
                        deanon_end = min(deanonymized_pos + chunk_size, len(full_deanonymized_text))
                        deanon_chunk = full_deanonymized_text[deanonymized_pos:deanon_end]
                        # Use json.dumps to properly escape the chunk
                        yield f"data: {json.dumps({'type': 'deanonymized', 'chunk': deanon_chunk})}\n\n"
                        deanonymized_pos = deanon_end
                    
                    chunks_sent += 1
                    
                    # Increased pause for more comfortable reading speed
                    await asyncio.sleep(0.1)
                
                logger.info(f"Completed dual stream for session {session_id}, sent {chunks_sent} chunk pairs")
                yield f"data: {json.dumps({'type': 'status', 'status': 'complete'})}\n\n"
                
            except Exception as stream_error:
                logger.error(f"Error in stream generation: {str(stream_error)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(stream_error)})}\n\n"
        
        return StreamingResponse(
            generate_dual_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")


@router.get("/stream/{session_id}")
async def deanonymize_streaming_response(session_id: str):
    """
    Streaming endpoint that simulates receiving LLM response and deanonymizing in real time.
    """
    try:
        # Get anonymization map
        anonymization_map = get_anonymization_map(session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        async def generate_deanonymized_stream():
            buffer = []
            
            # Simulate receiving streaming LLM response
            async for chunk in dummy_llm_response_stream("dummy prompt"):
                # Process chunk with deanonymization
                deanonymized_chunk, buffer = await deanonymize_streaming_text(
                    chunk, reverse_map, buffer
                )
                
                if deanonymized_chunk:
                    yield f"data: {json.dumps({'chunk': deanonymized_chunk})}\n\n"
            
            # Process any remaining content in buffer
            if buffer:
                final_text = ''.join(buffer)
                final_deanonymized = deanonymize_text(final_text, reverse_map)
                yield f"data: {json.dumps({'chunk': final_deanonymized})}\n\n"
            
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
        
        return StreamingResponse(
            generate_deanonymized_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")


@router.get("/test-full-process/{session_id}")
async def test_full_process(session_id: str):
    """
    Test endpoint that executes the complete process.
    """
    # 1. Setup dummy session
    store_anonymization_map(session_id, dummy_anonymization_map())
    
    # 2. Simulate model response with anonymized data
    anonymized_response = """Estimado usuario María González de Barcelona, 
    hemos procesado su solicitud. Sus datos registrados son:
    Email: maria.gonzalez@email.com
    Teléfono: 687654321
    Puede contactarnos en Avenida Libertad 456."""
    
    # 3. Deanonymize
    anonymization_map = get_anonymization_map(session_id)
    reverse_map = create_reverse_map(anonymization_map)
    deanonymized_response = deanonymize_text(anonymized_response, reverse_map)
    
    return {
        "session_id": session_id,
        "step_1_anonymization_map": anonymization_map,
        "step_2_anonymized_response": anonymized_response,
        "step_3_deanonymized_response": deanonymized_response
    }