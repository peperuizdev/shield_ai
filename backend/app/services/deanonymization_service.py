"""
Shield AI - Deanonymization Service

Service layer containing all deanonymization business logic.
Separated from HTTP layer for better organization and testability.
"""

import asyncio
import logging
from typing import AsyncGenerator, List, Tuple, Dict

logger = logging.getLogger(__name__)


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


# === CORE DEANONYMIZATION FUNCTIONS ===

def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create reverse map for deanonymization
    (fake_data -> original_data)
    
    Args:
        anonymization_map: Dictionary mapping original_data -> fake_data
        
    Returns:
        Dictionary mapping fake_data -> original_data
    """
    return {fake_data: original_data for original_data, fake_data in anonymization_map.items()}


def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Replace anonymized data with original data in text.
    Maintains exact structure (spaces, punctuation, etc.)
    
    Args:
        text: Text containing anonymized data
        reverse_map: Dictionary mapping fake_data -> original_data
        
    Returns:
        Text with original data restored
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
    
    Args:
        text_chunk: Current chunk of text
        reverse_map: Dictionary mapping fake_data -> original_data
        buffer: Buffer of accumulated chunks
        
    Returns:
        Tuple of (deanonymized_chunk, updated_buffer)
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


# === HIGH-LEVEL SERVICE FUNCTIONS ===

def process_deanonymization(session_id: str, model_response: str, anonymization_map: Dict[str, str]) -> Dict:
    """
    Process complete deanonymization for a given text and session.
    
    Args:
        session_id: Session identifier
        model_response: Text to deanonymize
        anonymization_map: Original anonymization mapping
        
    Returns:
        Dictionary with deanonymization results
    """
    try:
        logger.info(f"Processing deanonymization for session: {session_id}")
        
        # Create reverse map
        reverse_map = create_reverse_map(anonymization_map)
        
        # Deanonymize text
        deanonymized_text = deanonymize_text(model_response, reverse_map)
        
        # Count replacements made
        replacements_made = len([k for k, v in reverse_map.items() if k in model_response])
        
        result = {
            "session_id": session_id,
            "original_response": model_response,
            "deanonymized_response": deanonymized_text,
            "replacements_made": replacements_made
        }
        
        logger.info(f"Deanonymization completed for session {session_id}, {replacements_made} replacements made")
        return result
        
    except Exception as e:
        logger.error(f"Error in deanonymization for session {session_id}: {str(e)}")
        raise


async def generate_dual_stream(session_id: str, anonymization_map: Dict[str, str]) -> AsyncGenerator[str, None]:
    """
    Generate dual stream (anonymous + deanonymized) for a session.
    
    Args:
        session_id: Session identifier
        anonymization_map: Original anonymization mapping
        
    Yields:
        JSON-formatted SSE messages
    """
    import json
    
    try:
        logger.info(f"Starting dual stream for session: {session_id}")
        
        # Create reverse map
        reverse_map = create_reverse_map(anonymization_map)
        
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


async def generate_deanonymized_stream(session_id: str, anonymization_map: Dict[str, str]) -> AsyncGenerator[str, None]:
    """
    Generate deanonymized-only stream for a session.
    
    Args:
        session_id: Session identifier
        anonymization_map: Original anonymization mapping
        
    Yields:
        JSON-formatted SSE messages
    """
    import json
    
    try:
        logger.info(f"Starting deanonymized stream for session: {session_id}")
        
        # Create reverse map
        reverse_map = create_reverse_map(anonymization_map)
        
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
        
        logger.info(f"Completed deanonymized stream for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in deanonymized stream for session {session_id}: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def test_full_process(session_id: str) -> Dict:
    """
    Execute complete test process for deanonymization.
    
    Args:
        session_id: Session identifier for testing
        
    Returns:
        Dictionary with complete test results
    """
    from services.session_manager import store_anonymization_map, get_anonymization_map
    
    try:
        logger.info(f"Starting full test process for session: {session_id}")
        
        # 1. Setup dummy session
        dummy_map = dummy_anonymization_map()
        store_anonymization_map(session_id, dummy_map)
        
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
        
        result = {
            "session_id": session_id,
            "step_1_anonymization_map": anonymization_map,
            "step_2_anonymized_response": anonymized_response,
            "step_3_deanonymized_response": deanonymized_response
        }
        
        logger.info(f"Full test process completed for session {session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in full test process for session {session_id}: {str(e)}")
        raise