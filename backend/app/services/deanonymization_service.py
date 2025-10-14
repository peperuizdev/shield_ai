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
from services.session.anonymization import get_anonymization_map, store_anonymization_map

# =====================================================
# CONFIGURACIÓN DE STREAMING
# =====================================================
# Ajusta estos valores para controlar la velocidad del streaming en el frontend
# Valores más altos = streaming más lento y mejor visualización
# Valores más bajos = streaming más rápido
STREAMING_DELAY_DUMMY = 0.8        # Delay para dummy LLM responses (segundos)
STREAMING_DELAY_DEANONYMIZED = 0.4 # Delay para streaming deanonymizado (segundos)  
STREAMING_DELAY_CHAT = 0.5         # Delay para chat dual stream (segundos)
STREAMING_DELAY_REALTIME = 0.3     # Delay para streaming real-time (segundos)

logger = logging.getLogger(__name__)

def set_streaming_speed(speed_level: str = "fast"):
    """
    Ajusta la velocidad del streaming dinámicamente.
    
    Args:
        speed_level: "fast", "normal", "slow", "very_slow"
    """
    global STREAMING_DELAY_DUMMY, STREAMING_DELAY_DEANONYMIZED, STREAMING_DELAY_CHAT, STREAMING_DELAY_REALTIME
    
    speed_configs = {
        "fast": {
            "dummy": 0.1,
            "deanonymized": 0.1, 
            "chat": 0.1,
            "realtime": 0.05
        },
        "normal": {
            "dummy": 0.3,
            "deanonymized": 0.2,
            "chat": 0.2, 
            "realtime": 0.1
        },
        "slow": {
            "dummy": 0.8,
            "deanonymized": 0.4,
            "chat": 0.5,
            "realtime": 0.3
        },
        "very_slow": {
            "dummy": 1.2,
            "deanonymized": 0.6,
            "chat": 0.8,
            "realtime": 0.5
        }
    }
    
    config = speed_configs.get(speed_level, speed_configs["normal"])
    
    STREAMING_DELAY_DUMMY = config["dummy"]
    STREAMING_DELAY_DEANONYMIZED = config["deanonymized"]
    STREAMING_DELAY_CHAT = config["chat"] 
    STREAMING_DELAY_REALTIME = config["realtime"]
    

    logger.info(f"🚀 Streaming speed set to '{speed_level}': {config}")

# Configurar velocidad inicial (puedes cambiar esto)
set_streaming_speed("fast")  # Actualmente configurado para "slow"


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
        await asyncio.sleep(STREAMING_DELAY_DUMMY)  # Configurable streaming speed
        yield word

# =====================================================
# CORE DEANONYMIZATION FUNCTIONS
# =====================================================

def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create reverse mapping for deanonymization.
    
    Args:
        anonymization_map: Dictionary mapping fake_data -> original_data (from PII pipeline)
        
    Returns:
        Dictionary mapping fake_data -> original_data (same as input, ready for deanonymization)
    """
    # El mapping del pipeline PII viene como fake_data -> original_data
    # Ejemplo: {'[PERSON_1]': 'Juan Pérez', '[LOCATION_1]': 'Madrid'}
    # Esto es exactamente lo que necesitamos para deanonymize_text()
    
    logger.debug(f"🔧 Create reverse map input: {anonymization_map}")
    logger.debug(f"🔧 Create reverse map output (sin cambios): {anonymization_map}")
    return anonymization_map

def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Replace fake data with original data in text.
    Enhanced to handle partial name matches.
    
    Args:
        text: Text containing fake data
        reverse_map: Dictionary mapping fake -> original data
        
    Returns:
        Text with original data restored
    """
    result = text
    # Sort by length (descending) to avoid partial replacements
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    logger.debug(f"🔄 Deanonymizing text: {repr(text[:100])}...")
    logger.debug(f"🔄 Using reverse_map: {reverse_map}")
    
    replacements_made = []
    
    # First pass: exact matches
    for fake_data, original_data in sorted_items:
        if fake_data in result:
            result = result.replace(fake_data, original_data)
            replacements_made.append(f"'{fake_data}' -> '{original_data}' (exact)")
    
    # Second pass: partial matches for names (if no exact matches found for this chunk)
    if not replacements_made:
        for fake_data, original_data in sorted_items:
            # Check if fake_data appears to be a person name (contains space)
            if ' ' in fake_data:
                # Split fake name into parts and check if any significant part is in the text
                fake_parts = fake_data.split()
                for i in range(len(fake_parts)):
                    for j in range(i + 1, len(fake_parts) + 1):
                        partial_name = ' '.join(fake_parts[i:j])
                        # Only consider partial matches if they're at least 2 words or a long single word
                        if len(partial_name) >= 6 and partial_name in result:
                            # Replace the partial name with corresponding part of original name
                            original_parts = original_data.split()
                            if len(original_parts) >= len(fake_parts[i:j]):
                                partial_original = ' '.join(original_parts[i:j])
                                result = result.replace(partial_name, partial_original)
                                replacements_made.append(f"'{partial_name}' -> '{partial_original}' (partial)")
                                break
                if replacements_made:
                    break
    
    if replacements_made:
        logger.debug(f"✅ Replacements made: {replacements_made}")
    else:
        logger.debug(f"⚠️ No replacements made in text: {repr(text[:50])}")
    
    logger.debug(f"🔄 Deanonymized result: {repr(result[:100])}...")
    
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
        
        await asyncio.sleep(STREAMING_DELAY_DEANONYMIZED)  # Configurable streaming speed
    
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
            
            # Configurable delay for frontend visualization
            await asyncio.sleep(STREAMING_DELAY_CHAT)
        
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


async def generate_real_time_dual_stream(
    session_id: str, 
    llm_prompt: str, 
    mapping: Dict[str, str], 
    llm_client
) -> AsyncGenerator[str, None]:
    """
    Generate dual stream from REAL-TIME LLM streaming with live deanonymization.
    
    Args:
        session_id: Session ID for tracking
        llm_prompt: Prompt to send to LLM (with anonymized data)
        mapping: Anonymization mapping (original -> fake)
        llm_client: LLMClientPropuesta instance with streaming capability
        
    Yields:
        str: SSE formatted data with both anonymous and deanonymized chunks in real-time
    """
    try:
        import asyncio
        
        # Create reverse map for deanonymization
        reverse_map = create_reverse_map(mapping)
        
        logger.info(f"🚀 INICIANDO STREAMING REAL-TIME para sesión: {session_id}")
        logger.info(f"📤 LLM Prompt (anonimizado): {llm_prompt[:100]}...")
        logger.info(f"🔄 Mapping entities: {len(mapping)} entidades")
        logger.info(f"🗺️ Original mapping: {mapping}")
        logger.info(f"🔄 Reverse map for deanonymization: {reverse_map}")
        
        # Send initial metadata
        metadata = {
            "type": "metadata",
            "session_id": session_id,
            "pii_detected": bool(mapping),
            "entity_count": len(mapping),
            "streaming": "real-time",
            "llm_prompt_preview": llm_prompt[:100] + "..." if len(llm_prompt) > 100 else llm_prompt
        }
        yield f"data: {json.dumps(metadata)}\n\n"
        
        # Variables para acumular texto completo para guardar en Redis después
        full_anonymous_response = ""
        full_deanonymized_response = ""
        chunk_count = 0
        
        # Inicializar el procesador de chunks OPTIMIZADO (versión balanceada para streaming)
        from services.chunk_deanonymizer import ChunkDeanonymizer
        chunk_processor = ChunkDeanonymizer(reverse_map)
        
        logger.info(f"🔧 ChunkDeanonymizer inicializado con {len(reverse_map)} entidades")
        
        # STREAMING REAL-TIME DEL LLM
        logger.info("🔥 Iniciando streaming real del LLM con buffer inteligente...")
        
        async for llm_chunk in llm_client.call_grok_stream(llm_prompt, temperature=0.1):
            chunk_count += 1
            
            # Verificar si es un mensaje de error
            if llm_chunk.startswith("[ERROR:"):
                error_data = {
                    "type": "error",
                    "error": llm_chunk,
                    "session_id": session_id,
                    "chunk_count": chunk_count
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return
            
            # Procesar chunk con buffer inteligente
            anonymous_output, deanonymized_output = chunk_processor.process_chunk(llm_chunk)
            
            # Debug logging cada 10 chunks para diagnóstico
            if chunk_count % 10 == 0:
                logger.debug(f"📊 Chunk {chunk_count}: in='{llm_chunk[:30]}...', anon_out='{anonymous_output[:30]}...', deanon_out='{deanonymized_output[:30]}...'")
            
            # Acumular para guardar después
            full_anonymous_response += llm_chunk
            full_deanonymized_response += deanonymized_output
            
            # Enviar chunk anonimizado (lo que vio el LLM - datos falsos)
            anonymous_data = {
                "type": "anonymous",
                "chunk": anonymous_output,
                "session_id": session_id,
                "chunk_index": chunk_count,
                "is_real_time": True
            }
            yield f"data: {json.dumps(anonymous_data)}\n\n"
            
            # Enviar chunk deanonymizado (lo que ve el usuario - datos reales)
            # Solo enviar si hay contenido para evitar chunks vacíos
            if deanonymized_output:
                deanonymized_data = {
                    "type": "deanonymized", 
                    "chunk": deanonymized_output,
                    "session_id": session_id,
                    "chunk_index": chunk_count,
                    "is_real_time": True
                }
                yield f"data: {json.dumps(deanonymized_data)}\n\n"
                logger.debug(f"📤 Enviado chunk deanonymizado #{chunk_count}: '{deanonymized_output[:30]}...'")
            else:
                logger.debug(f"⏳ Chunk #{chunk_count} sin output deanonymizado (esperando más contenido)")
            
            # Delay configurable para controlar la velocidad de streaming en el frontend
            await asyncio.sleep(STREAMING_DELAY_REALTIME)  # Configurable streaming speed
            
            # Log progreso cada 10 chunks
            if chunk_count % 10 == 0:
                logger.info(f"📊 Procesados {chunk_count} chunks en tiempo real")
        
        # Finalizar procesamiento y enviar cualquier texto pendiente
        _, final_deanonymized = chunk_processor.finalize()
        if final_deanonymized:
            full_deanonymized_response += final_deanonymized
            final_data = {
                "type": "deanonymized",
                "chunk": final_deanonymized,
                "session_id": session_id,
                "chunk_index": chunk_count + 1,
                "is_real_time": True,
                "is_final": True
            }
            yield f"data: {json.dumps(final_data)}\n\n"
        
        # Guardar respuesta completa en Redis para consultas posteriores
        logger.info(f"💾 Guardando respuesta completa en Redis ({len(full_anonymous_response)} chars)")
        try:
            from services.session.llm_data import store_llm_response
            store_llm_response(session_id, full_anonymous_response)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar respuesta LLM en Redis: {e}")
        
        # Send completion signal
        completion_data = {
            "type": "complete",
            "session_id": session_id,
            "total_chunks": chunk_count,
            "entities_replaced": len(reverse_map),
            "anonymous_response_length": len(full_anonymous_response),
            "deanonymized_response_length": len(full_deanonymized_response),
            "streaming_type": "real-time",
            "anonymous_text": full_anonymous_response,
            "deanonymized_text": full_deanonymized_response
        }
        yield f"data: {json.dumps(completion_data)}\n\n"
        
        logger.info(f"✅ STREAMING REAL-TIME COMPLETADO - {chunk_count} chunks procesados")
        
    except Exception as e:
        logger.error(f"❌ Error en streaming real-time: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        error_data = {
            "type": "error",
            "error": str(e),
            "session_id": session_id,
            "streaming_type": "real-time",
            "traceback": traceback.format_exc()
        }
        yield f"data: {json.dumps(error_data)}\n\n"

# =====================================================
# DEBUG FUNCTIONS FOR SPECIFIC ISSUES
# =====================================================

def create_test_mapping_for_debug() -> Dict[str, str]:
    """
    Crea un mapping de prueba con el problema específico reportado.
    
    Returns:
        Dict con el mapping problemático para debugging
    """
    return {
        "Angelina_80": "Heraclio Garcés-Lara",  # El mapping problemático reportado
        "Valencia": "Madrid", 
        "612 345 678": "666 777 888"
    }

def test_chunk_deanonymizer_fix():
    """
    Prueba específica para validar la corrección del ChunkDeanonymizer optimizado.
    """
    from services.chunk_deanonymizer import ChunkDeanonymizer
    
    # Mapping problemático
    mapping = create_test_mapping_for_debug()
    processor = ChunkDeanonymizer(mapping)
    
    # Simular chunks como los recibe del LLM
    chunks = ["Angel", "ina_", "80", ", para", " hacer", " una", " tortilla", " española."]
    
    results = []
    full_deanonymized = ""
    
    logger.info(f"🧪 Testing ChunkDeanonymizer con mapping: {mapping}")
    
    for i, chunk in enumerate(chunks):
        anon_out, deanon_out = processor.process_chunk(chunk)
        full_deanonymized += deanon_out
        results.append({
            "chunk_index": i,
            "chunk": chunk,
            "anonymous": anon_out, 
            "deanonymized": deanon_out,
            "deanon_length": len(deanon_out)
        })
        logger.info(f"📝 Chunk {i}: '{chunk}' -> anon: '{anon_out}', deanon: '{deanon_out}'")
    
    # Finalizar
    _, final_content = processor.finalize()
    full_deanonymized += final_content
    
    logger.info(f"🏁 Final content: '{final_content}'")
    logger.info(f"📋 Full deanonymized text: '{full_deanonymized}'")
    
    return {
        "mapping_used": mapping,
        "chunk_results": results,
        "final_content": final_content,
        "full_deanonymized_text": full_deanonymized,
        "total_chunks": len(chunks),
        "chunks_with_output": len([r for r in results if r["deanonymized"]]),
        "optimization_applied": True
    }