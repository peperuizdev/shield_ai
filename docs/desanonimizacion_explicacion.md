# Cómo Funciona la Desanonimización en Shield AI

## Introducción

El código implementa un sistema de desanonimización para respuestas de un modelo de lenguaje (LLM) en una API FastAPI. El proceso principal se basa en un **mapa de anonimización** que mapea datos sensibles originales a versiones falsas, almacenado en Redis. Este documento explica paso a paso cómo funciona el sistema y cómo utiliza Redis para recuperar los datos sensibles.

## 1. Almacenamiento del Mapa en Redis

- Se utiliza una función dummy (`dummy_store_anonymization_map`) para simular el almacenamiento de un mapa de anonimización en Redis.
- El mapa es un diccionario que asocia datos sensibles (ej. nombres, emails, teléfonos) a versiones anonimizadas.
- Se almacena con una clave Redis: `f"anon_map:{session_id}"` y un TTL (tiempo de vida) de 1 hora (3600 segundos).

**Ejemplo de mapa dummy:**
```python
{
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
```

## 2. Recuperación de Datos Sensibles desde Redis

- La función `get_anonymization_map(session_id)` recupera el mapa desde Redis usando la clave `f"anon_map:{session_id}"`.
- Si no existe la clave, lanza un error HTTP 404.
- El mapa se decodifica desde JSON almacenado en Redis.
- Esto permite acceder a los datos sensibles originales de manera segura, ya que Redis actúa como caché temporal.

**Código relevante:**
```python
def get_anonymization_map(session_id: str) -> Dict[str, str]:
    redis_key = f"anon_map:{session_id}"
    map_data = redis_client.get(redis_key)
    
    if not map_data:
        raise HTTPException(status_code=404, detail=f"Mapa de anonimización no encontrado para sesión: {session_id}")
    
    try:
        return json.loads(map_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al decodificar el mapa de anonimización")
```

## 3. Creación del Mapa Inverso

- `create_reverse_map(anonymization_map)` invierte el mapa: las claves pasan a ser los datos falsos, y los valores los originales.
- Ejemplo: `"María González": "Juan Pérez"`.
- Esto facilita el reemplazo en el texto.

**Código relevante:**
```python
def create_reverse_map(anonymization_map: Dict[str, str]) -> Dict[str, str]:
    return {fake_data: original_data for original_data, fake_data in anonymization_map.items()}
```

## 4. Desanonimización del Texto

- `deanonymize_text(text, reverse_map)` reemplaza los datos falsos por los originales en el texto.
- Ordena los reemplazos por longitud descendente para evitar conflictos (ej. reemplazar "Juan Pérez" antes de "Juan").
- Mantiene la estructura exacta del texto (espacios, puntuación).

**Código relevante:**
```python
def deanonymize_text(text: str, reverse_map: Dict[str, str]) -> str:
    result = text
    
    # Ordenar por longitud descendente para evitar reemplazos parciales
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_data, original_data in sorted_items:
        # Reemplazo exacto manteniendo estructura
        result = result.replace(fake_data, original_data)
    
    return result
```

- Para streaming, funciones como `deanonymize_streaming_text` manejan chunks de texto, acumulando en un buffer para reemplazos que cruzan chunks.

## 5. Endpoints de la API

- `/deanonymize`: Desanonimiza una respuesta completa.
- `/dual-stream/{session_id}` y `/deanonymize-stream/{session_id}`: Manejan streaming, enviando chunks desanonimizados en tiempo real.
- `/setup-dummy-session/{session_id}`: Configura una sesión dummy con datos de prueba.
- `/test-full-process/{session_id}`: Prueba el flujo completo.

## Conclusión

Redis se usa como almacenamiento temporal y rápido para los mapas, permitiendo recuperación eficiente de datos sensibles por sesión. El sistema es dummy para simulación, pero en producción se integraría con un proceso real de anonimización. Este enfoque asegura que los datos sensibles se manejen de manera segura y eficiente, manteniendo la privacidad del usuario mientras se procesan respuestas de LLM.