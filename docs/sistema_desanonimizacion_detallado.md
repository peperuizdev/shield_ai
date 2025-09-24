# Sistema de Desanonimización Shield AI - Análisis Detallado

## 🔍 Resumen Ejecutivo

El proyecto **Shield AI** implementa un sistema de **desanonimización en tiempo real** usando FastAPI y Redis. Actualmente está configurado para recibir respuestas anonimizadas de un LLM y devolverlas con los datos originales restaurados en tiempo real mediante streaming.

## 📊 Estado Actual del Proyecto

### ✅ Implementado
- **FastAPI**: Servidor completo con 6 endpoints funcionales
- **Sistema de Desanonimización**: Completo con streaming en tiempo real
- **Redis**: Almacenamiento de mapas de anonimización con TTL
- **Datos Dummy**: Sistema completo de pruebas
- **Streaming Dual**: Envío simultáneo de versión anonimizada y desanonimizada

### ❌ No Implementado
- **Sistema PII Detection**: Existe pero NO se usa en el proceso actual
- **Redis Server**: Debe instalarse y ejecutarse por separado
- **Frontend**: Solo existe directorio vacío
- **Tests**: Existen pero no se ejecutan

## 🏗️ Arquitectura del Sistema

```
Cliente HTTP
    ↓
FastAPI (Puerto 8000)
    ↓
Sistema de Desanonimización
    ↓
Redis (Puerto 6379) - Almacena mapas de anonimización
    ↓
Respuesta Streaming (Datos originales)
```

## 📋 Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/setup-dummy-session/{session_id}` | POST | Configura sesión con datos de prueba |
| `/deanonymize` | POST | Desanonimización sin streaming |
| `/dual-stream/{session_id}` | GET | **Streaming dual** (anonimizado + desanonimizado) |
| `/deanonymize-stream/{session_id}` | GET | Streaming solo desanonimizado |
| `/test-full-process/{session_id}` | GET | Proceso completo de prueba |
| `/session/{session_id}/status` | GET | Estado de la sesión |
| `/session/{session_id}` | DELETE | Eliminar sesión |

## 🔄 Proceso de Desanonimización Detallado

### 1. Almacenamiento del Mapa de Anonimización

```python
def dummy_store_anonymization_map(session_id: str) -> None:
    """
    Almacena el mapa de anonimización en Redis con TTL de 1 hora
    """
    anonymization_map = {
        # Datos Originales -> Datos Falsos
        "Juan Pérez": "María González",
        "juan.perez@email.com": "maria.gonzalez@email.com",
        "612345678": "687654321",
        "12345678A": "87654321B",
        "Calle Mayor 123": "Avenida Libertad 456",
        "Madrid": "Barcelona",
        "28001": "08001",
        "Banco Santander": "Banco BBVA",
        "ES91 2100 0418 4502 0005 1332": "ES76 0182 6473 8901 2345 6789"
    }
    
    redis_key = f"anon_map:{session_id}"
    redis_client.setex(
        redis_key, 
        3600,  # TTL de 1 hora
        json.dumps(anonymization_map)
    )
```

**¿Qué se guarda en Redis?**
- **Clave**: `anon_map:{session_id}`
- **Valor**: JSON con mapeo dato_original → dato_falso
- **TTL**: 3600 segundos (1 hora)

### 2. Creación del Mapa Inverso

```python
def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    """
    Crea mapa inverso: dato_falso -> dato_original
    """
    return {fake_data: original_data for original_data, fake_data in anonymization_map.items()}
```

**Ejemplo de transformación:**
```
Original: {"Juan Pérez": "María González"}
Inverso:  {"María González": "Juan Pérez"}
```

### 3. Desanonimización de Texto

```python
def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    """
    Reemplaza datos anonimizados por originales manteniendo estructura exacta
    """
    result = text
    
    # Ordenar por longitud descendente para evitar reemplazos parciales
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        result = result.replace(fake_data, original_data)
    
    return result
```

**¿Por qué ordenar por longitud?**
Si tenemos:
- "María" → "Juan"
- "María González" → "Juan Pérez"

Sin ordenar, podríamos reemplazar "María" primero y obtener "Juan González" en lugar de "Juan Pérez".

### 4. Streaming en Tiempo Real

#### 4.1 Simulación de LLM Response Stream

```python
async def dummy_llm_response_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Simula respuesta streaming de LLM con datos anonimizados
    """
    response_text = """Hola María González, gracias por contactar con nosotros desde Barcelona. 
    Hemos recibido tu consulta sobre los servicios bancarios del Banco BBVA. 
    Confirmo que hemos registrado tu información:
    - Email: maria.gonzalez@email.com
    - Teléfono: 687654321
    - DNI: 87654321B
    - Dirección: Avenida Libertad 456, Barcelona, 08001
    """
    
    words = response_text.split()
    for word in words:
        await asyncio.sleep(0.1)  # Simula delay de streaming real
        yield word + " "
```

#### 4.2 Streaming Dual (Característica Principal)

```python
@app.get("/dual-stream/{session_id}")
async def dual_streaming_response(session_id: str):
    """
    Envía tanto respuesta anonimizada como desanonimizada simultáneamente
    """
    async def generate_dual_stream():
        # 1. Recopilar respuesta anonimizada completa
        anonymous_chunks = []
        async for chunk in dummy_llm_response_stream("dummy prompt"):
            anonymous_chunks.append(chunk)
        
        full_anonymous_text = ''.join(anonymous_chunks)
        
        # 2. Desanonimizar texto completo preservando estructura
        full_deanonymized_text = deanonymize_text(full_anonymous_text, reverse_map)
        
        # 3. Enviar ambos textos chunk por chunk sincronizado
        chunk_size = 1  # Carácter por carácter para máxima sincronización
        
        while anonymous_pos < len(full_anonymous_text) or deanonymized_pos < len(full_deanonymized_text):
            # Enviar chunk anonimizado
            if anonymous_pos < len(full_anonymous_text):
                anon_chunk = full_anonymous_text[anonymous_pos:anonymous_pos + chunk_size]
                yield f"data: {json.dumps({'type': 'anonymous', 'chunk': anon_chunk})}\n\n"
                anonymous_pos += chunk_size
            
            # Enviar chunk desanonimizado correspondiente
            if deanonymized_pos < len(full_deanonymized_text):
                deanon_chunk = full_deanonymized_text[deanonymized_pos:deanonymized_pos + chunk_size]
                yield f"data: {json.dumps({'type': 'deanonymized', 'chunk': deanon_chunk})}\n\n"
                deanonymized_pos += chunk_size
            
            await asyncio.sleep(0.05)  # Control de velocidad
        
        yield f"data: {json.dumps({'type': 'status', 'status': 'complete'})}\n\n"
```

**Formato de respuesta Server-Sent Events:**
```
data: {"type": "anonymous", "chunk": "H"}

data: {"type": "deanonymized", "chunk": "H"}

data: {"type": "anonymous", "chunk": "o"}

data: {"type": "deanonymized", "chunk": "o"}

...

data: {"type": "status", "status": "complete"}
```

#### 4.3 Streaming con Buffer (Versión Alternativa)

```python
async def deanonymize_streaming_text(
    text_chunk: str, 
    reverse_map: Dict[str, str], 
    buffer: List[str]
) -> Tuple[str, List[str]]:
    """
    Desanonimiza texto en streaming manejando palabras divididas entre chunks
    """
    # Añadir chunk actual al buffer
    buffer.append(text_chunk)
    full_text = ''.join(buffer)
    
    # Intentar desanonimizar el buffer completo
    deanonymized = deanonymize_text(full_text, reverse_map)
    
    if deanonymized != full_text:
        # Encontramos algo para reemplazar - liberar buffer
        return deanonymized, []
    else:
        # Buffer management: liberar si es muy largo
        if len(buffer) > 10:
            result = ''.join(buffer[:-5])
            return result, buffer[-5:]  # Mantener últimos 5 chunks
        
        return "", buffer  # Mantener buffer
```

**¿Por qué usar buffer?**
- Las palabras pueden dividirse entre chunks
- "María Gonz" + "ález" debe reconocerse como "María González"
- El buffer acumula text hasta encontrar coincidencias completas

### 5. Gestión de Sesiones Redis

```python
@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Verifica estado de sesión en Redis
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
```

## 🧪 Cómo Probar el Sistema

### Requisitos Previos

1. **Instalar Redis** (si no está instalado):
   ```bash
   # Windows (usando Chocolatey)
   choco install redis-64
   
   # O descargar desde: https://redis.io/download
   ```

2. **Ejecutar Redis**:
   ```bash
   redis-server
   ```

3. **Instalar dependencias Python**:
   ```bash
   cd backend
   pip install fastapi uvicorn redis
   ```

### Ejecutar el Servidor

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Secuencia de Pruebas

#### 1. Configurar Sesión de Prueba
```bash
curl -X POST "http://localhost:8000/setup-dummy-session/test123"
```

#### 2. Verificar Estado de Sesión
```bash
curl "http://localhost:8000/session/test123/status"
```

#### 3. Probar Desanonimización Simple
```bash
curl -X POST "http://localhost:8000/deanonymize" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test123",
    "model_response": "Hola María González de Barcelona"
  }'
```

#### 4. Probar Streaming Dual (Principal)
```bash
curl "http://localhost:8000/dual-stream/test123"
```

#### 5. Probar Proceso Completo
```bash
curl "http://localhost:8000/test-full-process/test123"
```

### Respuesta Esperada del Streaming

```
data: {"type": "anonymous", "chunk": "Hola "}
data: {"type": "deanonymized", "chunk": "Hola "}
data: {"type": "anonymous", "chunk": "María González"}
data: {"type": "deanonymized", "chunk": "Juan Pérez"}
data: {"type": "anonymous", "chunk": " de "}
data: {"type": "deanonymized", "chunk": " de "}
data: {"type": "anonymous", "chunk": "Barcelona"}
data: {"type": "deanonymized", "chunk": "Madrid"}
data: {"type": "status", "status": "complete"}
```

## 🗂️ Archivos que NO se Usan

La carpeta `pii_detection/` contiene un sistema completo de detección PII pero **NO se usa** en el proceso actual de desanonimización:

### Archivos NO Utilizados:
- `pii_detection/detector.py` - Detector principal PII
- `pii_detection/ner_model.py` - Modelo NER
- `pii_detection/pipeline.py` - Pipeline unificado
- `pii_detection/regex_patterns.py` - Patrones regex
- `tests/test_pii_detection.py` - Tests PII
- `main_desanonimization.py` - Duplicado exacto de main.py

### ¿Por qué no se usan?
El sistema actual asume que:
1. Ya se tiene un mapa de anonimización previo
2. Los datos llegan ya anonimizados
3. Solo se necesita **revertir** la anonimización

## 🔧 Problemas Detectados

1. **Redis no incluido en requirements.txt**
2. **Docker Compose vacío**
3. **main_desanonimization.py es duplicado**
4. **Sistema PII detection no integrado**
5. **Frontend vacío**
6. **Tests no integrados en el flujo**

## 🎯 Conclusiones

El proyecto tiene un **sistema de desanonimización completo y funcional** con:
- ✅ API FastAPI robusta
- ✅ Streaming en tiempo real
- ✅ Gestión de sesiones Redis
- ✅ Datos de prueba completos

**Fortalezas:**
- Arquitectura clara y funcional
- Streaming dual innovador
- Gestión adecuada de buffers
- TTL automático en Redis

**Áreas de mejora:**
- Integrar sistema PII detection
- Completar configuración Docker
- Eliminar duplicados
- Añadir frontend funcional