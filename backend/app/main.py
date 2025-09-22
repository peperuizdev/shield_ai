"""
Shield AI - Main Application Module

Main module for the Shield AI application.
Contains application setup and router mounting.
"""

# Import shared infrastructure
from core.app import app

# Montar routers de health, sessions y anonimización ===
from api.routes.health import router as health_router
from api.routes.sessions import router as sessions_router
from api.routes.anonymization import router as anonymization_router
from api.routes.deanonymization import router as deanonymization_router

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(anonymization_router, tags=["Anonymization"])
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
        await asyncio.sleep(0.1)  # Simulate streaming delay
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

@app.post("/deanonymize")
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
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error in deanonymization: {str(e)}")


@app.get("/dual-stream/{session_id}")
async def dual_streaming_response(session_id: str):
    """
    Streaming endpoint that sends both anonymized and deanonymized response simultaneously.
    """
    try:
        # Get anonymization map
        anonymization_map = get_anonymization_map(session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        async def generate_dual_stream():
            # First, collect full anonymized response
            anonymous_chunks = []
            async for chunk in dummy_llm_response_stream("dummy prompt"):
                anonymous_chunks.append(chunk)
            
            # Rebuild complete anonymized text
            full_anonymous_text = ''.join(anonymous_chunks)
            
            # Deanonymize complete text preserving structure
            full_deanonymized_text = deanonymize_text(full_anonymous_text, reverse_map)
            
            # Now send both texts chunk by chunk synchronized
            anonymous_pos = 0
            deanonymized_pos = 0
            chunk_size = 1  # Send character by character for maximum synchronization
            
            while anonymous_pos < len(full_anonymous_text) or deanonymized_pos < len(full_deanonymized_text):
                # Send anonymized chunk
                if anonymous_pos < len(full_anonymous_text):
                    anon_end = min(anonymous_pos + chunk_size, len(full_anonymous_text))
                    anon_chunk = full_anonymous_text[anonymous_pos:anon_end]
                    yield f"data: {{'type': 'anonymous', 'chunk': '{anon_chunk}'}}\n\n"
                    anonymous_pos = anon_end
                
                # Send corresponding deanonymized chunk
                if deanonymized_pos < len(full_deanonymized_text):
                    deanon_end = min(deanonymized_pos + chunk_size, len(full_deanonymized_text))
                    deanon_chunk = full_deanonymized_text[deanon_pos:deanon_end]
                    yield f"data: {{'type': 'deanonymized', 'chunk': '{deanon_chunk}'}}\n\n"
                    deanonymized_pos = deanon_end
                
                # Small pause for visual effect
                await asyncio.sleep(0.05)
            
            yield f"data: {{'type': 'status', 'status': 'complete'}}\n\n"
        
        return StreamingResponse(
            generate_dual_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")


@app.get("/deanonymize-stream/{session_id}")
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
                    import json
                    yield f"data: {json.dumps({'chunk': deanonymized_chunk})}\n\n"
            
            # Process any remaining content in buffer
            if buffer:
                final_text = ''.join(buffer)
                final_deanonymized = deanonymize_text(final_text, reverse_map)
                import json
                yield f"data: {json.dumps({'chunk': final_deanonymized})}\n\n"
            
            import json
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
        
        return StreamingResponse(
            generate_deanonymized_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")


@app.get("/test-full-process/{session_id}")
async def test_full_process(session_id: str):
    """
    Test endpoint that executes the complete process.
    """
    # Import session manager functions
    from services.session_manager import store_anonymization_map
    
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


# === MAIN APPLICATION ENTRY POINT ===

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )