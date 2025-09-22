"""
Shield AI - Deanonymization Service

Business logic for deanonymization operations.
Contains all core functions for text deanonymization, streaming, and testing.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, AsyncGenerator
from .session_manager import get_anonymization_map, store_anonymization_map

logger = logging.getLogger(__name__)

# =====================================================
# DUMMY DATA FUNCTIONS (FOR TESTING)
# =====================================================

def dummy_anonymization_map() -> Dict[str, str]:
    """
    Create a dummy anonymization map for testing purposes.
    
    Returns:
        Dict mapping original data to fake data for testing
    """
    return {
        "Juan Pérez": "María González",
        "juan.perez@email.com": "maria.gonzalez@email.com",
        "Madrid": "Barcelona", 
        "+34 612 345 678": "+34 687 654 321",
        "Calle Mayor 123": "Avenida Diagonal 456",
        "12345678A": "87654321B",
        "Banco Santander": "Banco BBVA",
        "ES91 2100 0418 4502 0005 1332": "ES76 0182 6473 8901 2345 6789",
        "Empresa ABC S.L.": "Corporación XYZ S.A."
    }

async def dummy_llm_response_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Simulate an LLM response stream for testing.
    
    Args:
        prompt: The prompt sent to the LLM (for realism)
        
    Yields:
        str: Words from a simulated LLM response
    """
    # Simulated LLM response with fake data
    response_words = [
        "Hola", "María", "González,", "gracias", "por", "contactar", "con", "nosotros.",
        "Hemos", "recibido", "tu", "consulta", "desde", "Barcelona", "y", "la", "estamos",
        "procesando.", "Tu", "email", "maria.gonzalez@email.com", "ha", "sido", "registrado.",
        "El", "teléfono", "+34", "687", "654", "321", "será", "contactado", "pronto.",
        "Banco", "BBVA", "procesará", "la", "transacción", "desde", "la", "cuenta",
        "ES76", "0182", "6473", "8901", "2345", "6789.", "La", "dirección", "Avenida",
        "Diagonal", "456", "está", "confirmada.", "Corporación", "XYZ", "S.A.", "se",
        "pondrá", "en", "contacto", "contigo.", "Saludos", "cordiales."
    ]
    
    for word in response_words:
        await asyncio.sleep(0.3)  # Slower streaming for better UX
        yield word

# =====================================================
# CORE DEANONYMIZATION FUNCTIONS
# =====================================================

def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create reverse mapping for deanonymization.
    
    Args:
        anonymization_map: Dictionary mapping pseudonym -> original data (from PII pipeline)
        
    Returns:
        Dictionary mapping pseudonym -> original data (same as input, no inversion needed)
    """
    # El mapping del pipeline PII ya viene como pseudonym -> original
    # No necesitamos invertirlo
    return anonymization_map

def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Replace fake data with original data in text.
    
    Args:
        text: Text containing fake data
        reverse_map: Dictionary mapping fake -> original data
        
    Returns:
        Text with original data restored
    """
    result = text
    # Sort by length (descending) to avoid partial replacements
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        result = result.replace(fake_data, original_data)
    
    return result

async def deanonymize_streaming_text(text_stream: AsyncGenerator[str, None], 
                                   reverse_map: Dict[str, str]) -> AsyncGenerator[str, None]:
    """
    Deanonymize text as it streams in.
    
    Args:
        text_stream: Async generator of text chunks
        reverse_map: Dictionary mapping fake -> original data
        
    Yields:
        str: Deanonymized text chunks
    """
    buffer = ""
    
    async for chunk in text_stream:
        buffer += chunk
        
        # Check for complete replacements in buffer
        for fake_data, original_data in reverse_map.items():
            if fake_data in buffer:
                buffer = buffer.replace(fake_data, original_data)
        
        # Yield processed chunks (word by word for smoother streaming)
        words = buffer.split()
        if len(words) > 1:
            # Yield all complete words except the last (might be incomplete)
            for word in words[:-1]:
                yield word + " "
            buffer = words[-1]  # Keep last word in buffer
        
        await asyncio.sleep(0.1)  # Slower streaming for better UX
    
    # Yield remaining buffer
    if buffer:
        yield buffer

def process_deanonymization(text: str, session_id: str) -> Dict[str, Any]:
    """
    Complete deanonymization process using session data from Redis.
    
    Args:
        text: Text to deanonymize
        session_id: Session ID for retrieving anonymization map
        
    Returns:
        Dictionary with deanonymization results
    """
    try:
        # Get anonymization map from Redis
        anonymization_map = get_anonymization_map(session_id)
        
        if not anonymization_map:
            return {
                "success": False,
                "error": f"No anonymization map found for session {session_id}",
                "original_text": text,
                "deanonymized_text": text
            }
        
        # Create reverse map and deanonymize
        reverse_map = create_reverse_map(anonymization_map)
        deanonymized = deanonymize_text(text, reverse_map)
        
        return {
            "success": True,
            "original_text": text,
            "deanonymized_text": deanonymized,
            "session_id": session_id,
            "replacements_made": len([k for k in reverse_map.keys() if k in text])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original_text": text,
            "deanonymized_text": text
        }

# =====================================================
# STREAMING FUNCTIONS
# =====================================================

async def generate_dual_stream(session_id: str) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream showing both anonymous and deanonymized text.
    
    Args:
        session_id: Session ID for retrieving anonymization map
        
    Yields:
        str: SSE formatted data
    """
    try:
        # Get anonymization map from Redis
        anonymization_map = get_anonymization_map(session_id)
        
        if not anonymization_map:
            yield f"data: {json.dumps({'error': f'No map found for session {session_id}'})}\n\n"
            return
        
        # Create reverse map for deanonymization
        reverse_map = create_reverse_map(anonymization_map)
        
        # Simulate LLM response stream
        llm_stream = dummy_llm_response_stream("Process user query with anonymized data")
        
        async for word in llm_stream:
            # Send anonymous chunk (as received from LLM)
            anonymous_data = {
                "type": "anonymous",
                "chunk": word,
                "session_id": session_id
            }
            yield f"data: {json.dumps(anonymous_data)}\n\n"
            
            # Deanonymize the chunk
            deanonymized_chunk = deanonymize_text(word, reverse_map)
            
            # Send deanonymized chunk
            deanonymized_data = {
                "type": "deanonymized", 
                "chunk": deanonymized_chunk,
                "session_id": session_id
            }
            yield f"data: {json.dumps(deanonymized_data)}\n\n"
    
    except Exception as e:
        error_data = {"error": str(e), "session_id": session_id}
        yield f"data: {json.dumps(error_data)}\n\n"

async def generate_deanonymized_stream(session_id: str) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream with only deanonymized text.
    
    Args:
        session_id: Session ID for retrieving anonymization map
        
    Yields:
        str: SSE formatted data with deanonymized content
    """
    try:
        # Get anonymization map from Redis
        anonymization_map = get_anonymization_map(session_id)
        
        if not anonymization_map:
            yield f"data: {json.dumps({'error': f'No map found for session {session_id}'})}\n\n"
            return
        
        # Create reverse map for deanonymization
        reverse_map = create_reverse_map(anonymization_map)
        
        # Simulate LLM response stream
        llm_stream = dummy_llm_response_stream("Process user query")
        
        # Deanonymize streaming text
        deanonymized_stream = deanonymize_streaming_text(llm_stream, reverse_map)
        
        async for chunk in deanonymized_stream:
            data = {
                "type": "deanonymized",
                "chunk": chunk,
                "session_id": session_id
            }
            yield f"data: {json.dumps(data)}\n\n"
    
    except Exception as e:
        error_data = {"error": str(e), "session_id": session_id}
        yield f"data: {json.dumps(error_data)}\n\n"

# =====================================================
# GET STREAMING FUNCTIONS (for backwards compatibility)
# =====================================================

async def generate_dual_stream_get(session_id: str) -> AsyncGenerator[str, None]:
    """
    GET version of dual stream for backward compatibility.
    """
    async for chunk in generate_dual_stream(session_id):
        yield chunk

async def generate_deanonymized_stream_get(session_id: str) -> AsyncGenerator[str, None]:
    """
    GET version of deanonymized stream for backward compatibility.
    """
    async for chunk in generate_deanonymized_stream(session_id):
        yield chunk

# =====================================================
# TESTING FUNCTIONS
# =====================================================

def test_full_process(session_id: str) -> Dict[str, Any]:
    """
    Test complete deanonymization process with dummy data.
    
    Args:
        session_id: Session ID to use for testing
        
    Returns:
        Dictionary with test results
    """
    try:
        # Setup dummy session
        dummy_map = dummy_anonymization_map()
        store_anonymization_map(session_id, dummy_map)
        
        # Test text with fake data (as if coming from LLM)
        test_text = ("Hola María González, hemos procesado tu solicitud desde Barcelona. "
                    "Tu email maria.gonzalez@email.com ha sido registrado correctamente. "
                    "El Banco BBVA procesará la transferencia.")
        
        # Process deanonymization
        result = process_deanonymization(test_text, session_id)
        
        # Add test metadata
        result.update({
            "test_session": True,
            "dummy_map_used": dummy_map,
            "test_text_input": test_text
        })
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Test failed: {str(e)}",
            "test_session": True
        }

# =====================================================
# CHAT STREAMING FUNCTIONS
# =====================================================

async def generate_chat_dual_stream(session_id: str, llm_response: str, mapping: Dict[str, str]) -> AsyncGenerator[str, None]:
    """
    Generate dual stream from real chat data instead of dummy data.
    
    Args:
        session_id: Session ID for tracking
        llm_response: Real LLM response (with fake data)
        mapping: Anonymization mapping (original -> fake)
        
    Yields:
        str: SSE formatted data with both anonymous and deanonymized chunks
    """
    try:
        import asyncio
        
        # Create reverse map for deanonymization
        reverse_map = create_reverse_map(mapping)
        
        # Deanonymize the COMPLETE response to get the real data version
        deanonymized_response = deanonymize_text(llm_response, reverse_map)
        
        logger.info(f"LLM Response (falso): {llm_response[:100]}...")
        logger.info(f"Deanonymized (real): {deanonymized_response[:100]}...")
        
        # Send initial metadata
        metadata = {
            "type": "metadata",
            "session_id": session_id,
            "pii_detected": bool(mapping),
            "entity_count": len(mapping),
            "streaming": True
        }
        yield f"data: {json.dumps(metadata)}\n\n"
        
        # Split BOTH responses into words for streaming simulation
        anonymous_words = llm_response.split()
        deanonymized_words = deanonymized_response.split()
        
        # Stream both responses word by word in parallel
        max_words = max(len(anonymous_words), len(deanonymized_words))
        
        for i in range(max_words):
            # Get anonymous word (with fake data)
            anonymous_chunk = ""
            if i < len(anonymous_words):
                anonymous_chunk = f" {anonymous_words[i]}" if i > 0 else anonymous_words[i]
            
            # Get deanonymized word (with real data)  
            deanonymized_chunk = ""
            if i < len(deanonymized_words):
                deanonymized_chunk = f" {deanonymized_words[i]}" if i > 0 else deanonymized_words[i]
            
            # Send anonymous chunk (what LLM generated - with fake data)
            if anonymous_chunk:
                anonymous_data = {
                    "type": "anonymous",
                    "chunk": anonymous_chunk,
                    "session_id": session_id,
                    "word_index": i
                }
                yield f"data: {json.dumps(anonymous_data)}\n\n"
            
            # Send deanonymized chunk (what user sees - with real data)
            if deanonymized_chunk:
                deanonymized_data = {
                    "type": "deanonymized",
                    "chunk": deanonymized_chunk,
                    "session_id": session_id,
                    "word_index": i
                }
                yield f"data: {json.dumps(deanonymized_data)}\n\n"
            
            # Small delay to simulate real streaming
            await asyncio.sleep(0.1)
        
        # Send completion signal
        completion_data = {
            "type": "complete",
            "session_id": session_id,
            "total_words": max_words,
            "entities_replaced": len(reverse_map),
            "anonymous_text": llm_response,
            "deanonymized_text": deanonymized_response
        }
        yield f"data: {json.dumps(completion_data)}\n\n"
        
    except Exception as e:
        error_data = {
            "type": "error",
            "error": str(e),
            "session_id": session_id
        }
        yield f"data: {json.dumps(error_data)}\n\n"