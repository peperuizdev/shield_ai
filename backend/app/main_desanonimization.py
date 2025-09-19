import redis
import json
import re
import asyncio
from typing import Dict, AsyncGenerator, List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

# Configuración de Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

app = FastAPI(title="Shield AI - Desanonimización API")

class DeAnonymizationRequest(BaseModel):
    session_id: str
    model_response: str

class StreamingDeAnonymizationRequest(BaseModel):
    session_id: str

# === FUNCIONES DUMMY PARA SIMULAR EL PROCESO ===

def dummy_anonymization_map() -> Dict[str, str]:
    """
    Función dummy que simula un mapa de anonimización típico
    que se habría generado en el proceso previo de anonimización
    """
    return {
        # Nombres completos
        "Juan Pérez": "María González",
        # Emails
        "juan.perez@email.com": "maria.gonzalez@email.com", 
        # Teléfonos
        "612345678": "687654321",
        # DNIs
        "12345678A": "87654321B",
        # Direcciones - mantener la dirección base igual para evitar problemas
        "Calle Mayor 123": "Avenida Libertad 456",
        # Ciudades
        "Madrid": "Barcelona",
        # Códigos postales
        "28001": "08001",
        # Bancos
        "Banco Santander": "Banco BBVA",
        # IBANs
        "ES91 2100 0418 4502 0005 1332": "ES76 0182 6473 8901 2345 6789"
    }

def dummy_store_anonymization_map(session_id: str) -> None:
    """
    Función dummy que simula el almacenamiento del mapa en Redis
    """
    anonymization_map = dummy_anonymization_map()
    redis_key = f"anon_map:{session_id}"
    
    # Almacenamos el mapa con TTL de 1 hora
    redis_client.setex(
        redis_key, 
        3600,  # TTL de 1 hora
        json.dumps(anonymization_map)
    )
    print(f"Mapa de anonimización almacenado para sesión: {session_id}")

async def dummy_llm_response_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Función dummy que simula la respuesta streaming de un LLM
    con datos anonimizados
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
        await asyncio.sleep(0.1)  # Simula delay de streaming
        yield word + " "

# === FUNCIONES PRINCIPALES DE DESANONIMIZACIÓN ===

def get_anonymization_map(session_id: str) -> Dict[str, str]:
    """
    Recupera el mapa de anonimización desde Redis
    """
    redis_key = f"anon_map:{session_id}"
    map_data = redis_client.get(redis_key)
    
    if not map_data:
        raise HTTPException(status_code=404, detail=f"Mapa de anonimización no encontrado para sesión: {session_id}")
    
    try:
        return json.loads(map_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al decodificar el mapa de anonimización")

def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Crea un mapa inverso para la desanonimización
    (dato_falso -> dato_original)
    """
    return {fake_data: original_data for original_data, fake_data in anonymization_map.items()}

def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Reemplaza los datos anonimizados por los originales en un texto
    Mantiene exactamente la misma estructura (espacios, puntuación, etc.)
    """
    result = text
    
    # Ordenar por longitud descendente para evitar reemplazos parciales
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        # Reemplazo exacto manteniendo estructura
        result = result.replace(fake_data, original_data)
    
    return result

async def deanonymize_streaming_text(
    text_chunk: str, 
    reverse_map: Dict[str, str], 
    buffer: List[str]
) -> Tuple[str, List[str]]:
    """
    Desanonimiza texto en streaming, manejando palabras que pueden estar divididas
    entre chunks
    """
    # Añadir chunk actual al buffer
    buffer.append(text_chunk)
    
    # Unir el buffer para procesamiento
    full_text = ''.join(buffer)
    
    # Intentar desanonimizar el texto completo del buffer
    deanonymized = deanonymize_text(full_text, reverse_map)
    
    # Si hay cambios, significa que encontramos algo para reemplazar
    if deanonymized != full_text:
        # Limpiar buffer y devolver el texto desanonimizado
        return deanonymized, []
    else:
        # Si el buffer es muy largo y no hay coincidencias, liberar parte del buffer
        if len(buffer) > 10:  # Mantener solo los últimos elementos
            result = ''.join(buffer[:-5])  # Devolver parte del buffer
            return result, buffer[-5:]  # Mantener los últimos 5 chunks
        
        # No hay coincidencias aún, mantener buffer
        return "", buffer

# === ENDPOINTS DE LA API ===

@app.post("/setup-dummy-session/{session_id}")
async def setup_dummy_session(session_id: str):
    """
    Endpoint para configurar una sesión dummy con datos de prueba
    """
    dummy_store_anonymization_map(session_id)
    return {"message": f"Sesión {session_id} configurada con datos dummy"}

@app.post("/deanonymize")
async def deanonymize_response(request: DeAnonymizationRequest):
    """
    Desanonimiza una respuesta completa (sin streaming)
    """
    try:
        # Obtener el mapa de anonimización
        anonymization_map = get_anonymization_map(request.session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        # Desanonimizar el texto
        deanonymized_text = deanonymize_text(request.model_response, reverse_map)
        
        return {
            "session_id": request.session_id,
            "original_response": request.model_response,
            "deanonymized_response": deanonymized_text,
            "replacements_made": len([k for k, v in reverse_map.items() if k in request.model_response])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en desanonimización: {str(e)}")

@app.get("/dual-stream/{session_id}")
async def dual_streaming_response(session_id: str):
    """
    Endpoint de streaming que envía tanto respuesta anonimizada como desanonimizada simultáneamente
    """
    try:
        # Obtener el mapa de anonimización
        anonymization_map = get_anonymization_map(session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        async def generate_dual_stream():
            # Primero, recopilar toda la respuesta anonimizada
            anonymous_chunks = []
            async for chunk in dummy_llm_response_stream("dummy prompt"):
                anonymous_chunks.append(chunk)
            
            # Reconstruir el texto completo anonimizado
            full_anonymous_text = ''.join(anonymous_chunks)
            
            # Desanonimizar el texto completo preservando estructura
            full_deanonymized_text = deanonymize_text(full_anonymous_text, reverse_map)
            
            # Ahora enviar ambos textos chunk por chunk de manera sincronizada
            min_length = min(len(full_anonymous_text), len(full_deanonymized_text))
            max_length = max(len(full_anonymous_text), len(full_deanonymized_text))
            
            anonymous_pos = 0
            deanonymized_pos = 0
            chunk_size = 1  # Enviar carácter por carácter para máxima sincronización
            
            while anonymous_pos < len(full_anonymous_text) or deanonymized_pos < len(full_deanonymized_text):
                # Enviar chunk anonimizado
                if anonymous_pos < len(full_anonymous_text):
                    anon_end = min(anonymous_pos + chunk_size, len(full_anonymous_text))
                    anon_chunk = full_anonymous_text[anonymous_pos:anon_end]
                    yield f"data: {json.dumps({'type': 'anonymous', 'chunk': anon_chunk})}\n\n"
                    anonymous_pos = anon_end
                
                # Enviar chunk desanonimizado correspondiente
                if deanonymized_pos < len(full_deanonymized_text):
                    deanon_end = min(deanonymized_pos + chunk_size, len(full_deanonymized_text))
                    deanon_chunk = full_deanonymized_text[deanonymized_pos:deanon_end]
                    yield f"data: {json.dumps({'type': 'deanonymized', 'chunk': deanon_chunk})}\n\n"
                    deanonymized_pos = deanon_end
                
                # Pequeña pausa para efecto visual
                await asyncio.sleep(0.05)
            
            yield f"data: {json.dumps({'type': 'status', 'status': 'complete'})}\n\n"
        
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
        raise HTTPException(status_code=500, detail=f"Error en streaming: {str(e)}")

def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Reemplaza los datos anonimizados por los originales en un texto
    Mantiene exactamente la misma estructura (espacios, puntuación, etc.)
    """
    result = text
    
    # Ordenar por longitud descendente para evitar reemplazos parciales
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        # Reemplazo exacto manteniendo estructura
        result = result.replace(fake_data, original_data)
    
    return result

async def deanonymize_chunk_with_structure(
    chunk: str, 
    reverse_map: Dict[str, str], 
    buffer: List[str]
) -> str:
    """
    Desanonimiza un chunk manteniendo exactamente la estructura original
    """
    # Simplemente devolver el chunk aplicando desanonimización directa
    # pero solo si tenemos coincidencias completas
    
    # Construir texto acumulado hasta ahora
    buffer.append(chunk)
    accumulated_text = ''.join(buffer)
    
    # Buscar si alguna palabra falsa se completa en este chunk
    result_chunk = chunk
    
    # Ordenar por longitud descendente para evitar reemplazos parciales
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        # Verificar si la palabra falsa termina exactamente en este chunk
        if fake_data in accumulated_text:
            # Encontrar la posición de la coincidencia
            match_pos = accumulated_text.rfind(fake_data)
            if match_pos != -1:
                match_end = match_pos + len(fake_data)
                
                # Si la coincidencia termina en el chunk actual
                if match_end > len(accumulated_text) - len(chunk):
                    # Calcular qué parte del reemplazo va en este chunk
                    chunk_start_pos = len(accumulated_text) - len(chunk)
                    overlap_start = max(0, match_pos - chunk_start_pos)
                    overlap_in_original = overlap_start + (chunk_start_pos - match_pos) if chunk_start_pos > match_pos else 0
                    
                    if overlap_in_original < len(original_data):
                        # Reemplazar solo la parte que corresponde a este chunk
                        chars_in_chunk = min(len(chunk) - overlap_start, len(original_data) - overlap_in_original)
                        replacement = original_data[overlap_in_original:overlap_in_original + chars_in_chunk]
                        
                        # Reconstruir el chunk
                        result_chunk = chunk[:overlap_start] + replacement + chunk[overlap_start + len(fake_data[overlap_in_original:overlap_in_original + chars_in_chunk]):]
                        
                        break
    
    # Si el buffer se está volviendo muy grande sin coincidencias, liberarlo parcialmente
    if len(buffer) > 20:
        # Mantener solo los últimos elementos para palabras que puedan estar divididas
        buffer = buffer[-10:]
    
    return result_chunk

@app.get("/deanonymize-stream/{session_id}")
async def deanonymize_streaming_response(session_id: str):
    """
    Endpoint de streaming que simula recibir respuesta del LLM y desanonimizar en tiempo real
    (Mantenido para compatibilidad)
    """
    try:
        # Obtener el mapa de anonimización
        anonymization_map = get_anonymization_map(session_id)
        reverse_map = create_reverse_map(anonymization_map)
        
        async def generate_deanonymized_stream():
            buffer = []
            
            # Simular recepción de respuesta streaming del LLM
            async for chunk in dummy_llm_response_stream("dummy prompt"):
                # Procesar chunk con desanonimización
                deanonymized_chunk, buffer = await deanonymize_streaming_text(
                    chunk, reverse_map, buffer
                )
                
                if deanonymized_chunk:
                    yield f"data: {json.dumps({'chunk': deanonymized_chunk})}\n\n"
            
            # Procesar cualquier contenido restante en el buffer
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
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en streaming: {str(e)}")

@app.get("/test-full-process/{session_id}")
async def test_full_process(session_id: str):
    """
    Endpoint de prueba que ejecuta todo el proceso completo
    """
    # 1. Configurar sesión dummy
    dummy_store_anonymization_map(session_id)
    
    # 2. Simular respuesta del modelo con datos anonimizados
    anonymized_response = """Estimado usuario María González de Barcelona, 
    hemos procesado su solicitud. Sus datos registrados son:
    Email: maria.gonzalez@email.com
    Teléfono: 687654321
    Puede contactarnos en Avenida Libertad 456."""
    
    # 3. Desanonimizar
    anonymization_map = get_anonymization_map(session_id)
    reverse_map = create_reverse_map(anonymization_map)
    deanonymized_response = deanonymize_text(anonymized_response, reverse_map)
    
    return {
        "session_id": session_id,
        "step_1_anonymization_map": anonymization_map,
        "step_2_anonymized_response": anonymized_response,
        "step_3_deanonymized_response": deanonymized_response
    }

# === ENDPOINTS DE UTILIDAD ===

@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Verifica si existe una sesión y su estado
    """
    redis_key = f"anon_map:{session_id}"
    exists = redis_client.exists(redis_key)
    ttl = redis_client.ttl(redis_key) if exists else -1
    
    return {
        "session_id": session_id,
        "exists": bool(exists),
        "ttl_seconds": ttl,
        "expires_in": f"{ttl // 60} minutos" if ttl > 0 else "N/A"
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Elimina una sesión y su mapa de anonimización
    """
    redis_key = f"anon_map:{session_id}"
    deleted = redis_client.delete(redis_key)
    
    return {
        "session_id": session_id,
        "deleted": bool(deleted)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)