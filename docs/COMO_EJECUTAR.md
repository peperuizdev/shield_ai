# Guía Paso a Paso - Shield AI Desanonimización

## 🚀 Instrucciones Completas de Instalación y Ejecución

### 1. Prerequisitos del Sistema

#### Windows:
```powershell
# Instalar Python 3.10+ (si no está instalado)
# Descargar de: https://www.python.org/downloads/

# Instalar Redis usando Chocolatey (opción recomendada)
choco install redis-64

# O instalar Redis usando WSL
wsl --install Ubuntu
# Luego en WSL: sudo apt install redis-server
```

#### Linux/macOS:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server python3 python3-pip

# macOS
brew install redis python3
```

### 2. Preparar el Entorno

```bash
# Navegar al directorio del proyecto
cd "C:\Users\Polina\Desktop\Factoria F5\shield_ai\backend"

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Iniciar Redis

#### Windows (instalación local):
```powershell
# Iniciar Redis server
redis-server

# En otra terminal, verificar que funciona:
redis-cli ping
# Debe responder: PONG
```

#### Windows (WSL):
```bash
# En WSL terminal:
sudo service redis-server start

# Verificar:
redis-cli ping
```

#### Docker (alternativa):
```bash
docker run -d -p 6380:6379 --name redis redis:alpine
```

### 4. Ejecutar el Servidor FastAPI

```bash
# IMPORTANTE: Asegúrate de estar en el directorio backend/
cd "C:\Users\Polina\Desktop\Factoria F5\shield_ai\backend"

# Ejecutar el servidor
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**El servidor estará disponible en:** http://localhost:8000

**Documentación automática en:** http://localhost:8000/docs

### 5. Probar el Sistema - Secuencia Completa

#### Paso 1: Configurar Sesión de Prueba
```bash
# PowerShell/Terminal:
curl -X POST "http://localhost:8000/setup-dummy-session/test123"
Invoke-RestMethod -Uri "http://localhost:8000/setup-dummy-session/test123" -Method Post
```

**Respuesta esperada:**
```json
{"message": "Sesión test123 configurada con datos dummy"}
```

#### Paso 2: Verificar Estado de Sesión
```bash
curl "http://localhost:8000/session/test123/status"
```

**Respuesta esperada:**
```json
{
  "session_id": "test123",
  "exists": true,
  "ttl_seconds": 3599,
  "expires_in": "59 minutos"
}
```

#### Paso 3: Probar Desanonimización Simple
```bash
curl -X POST "http://localhost:8000/deanonymize" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"test123\",
    \"model_response\": \"Hola María González de Barcelona, tu email maria.gonzalez@email.com ha sido registrado.\"
  }"
```

**Respuesta esperada:**
```json
{
  "session_id": "test123",
  "original_response": "Hola María González de Barcelona, tu email maria.gonzalez@email.com ha sido registrado.",
  "deanonymized_response": "Hola Juan Pérez de Madrid, tu email juan.perez@email.com ha sido registrado.",
  "replacements_made": 3
}
```

#### Paso 4: Probar Streaming Dual (Funcionalidad Principal)
```bash
curl "http://localhost:8000/dual-stream/test123"
```

**Respuesta esperada (Server-Sent Events):**
```
data: {"type": "anonymous", "chunk": "Hola "}
data: {"type": "deanonymized", "chunk": "Hola "}
data: {"type": "anonymous", "chunk": "María González"}
data: {"type": "deanonymized", "chunk": "Juan Pérez"}
data: {"type": "anonymous", "chunk": ", gracias "}
data: {"type": "deanonymized", "chunk": ", gracias "}
data: {"type": "anonymous", "chunk": "por contactar "}
data: {"type": "deanonymized", "chunk": "por contactar "}
... (continúa)
data: {"type": "status", "status": "complete"}
```

#### Paso 5: Proceso Completo de Ejemplo
```bash
curl "http://localhost:8000/test-full-process/test123"
```

### 6. Probar con Navegador Web

Abre: http://localhost:8000/docs

En la interfaz Swagger podrás:
1. Configurar sesiones
2. Probar todos los endpoints
3. Ver las respuestas en tiempo real

### 7. Probar Streaming en el Navegador

Crea un archivo HTML de prueba:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Shield AI - Test Streaming</title>
</head>
<body>
    <h1>Test Desanonimización Streaming</h1>
    
    <button onclick="startStreaming()">Iniciar Stream</button>
    <button onclick="setupSession()">Configurar Sesión</button>
    
    <div>
        <h3>Texto Anonimizado:</h3>
        <div id="anonymous" style="border: 1px solid blue; padding: 10px; min-height: 100px;"></div>
    </div>
    
    <div>
        <h3>Texto Desanonimizado:</h3>
        <div id="deanonymized" style="border: 1px solid green; padding: 10px; min-height: 100px;"></div>
    </div>

    <script>
        function setupSession() {
            fetch('http://localhost:8000/setup-dummy-session/test123', {method: 'POST'})
                .then(response => response.json())
                .then(data => console.log('Sesión configurada:', data));
        }

        function startStreaming() {
            const anonymous = document.getElementById('anonymous');
            const deanonymized = document.getElementById('deanonymized');
            
            anonymous.innerHTML = '';
            deanonymized.innerHTML = '';
            
            const eventSource = new EventSource('http://localhost:8000/dual-stream/test123');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'anonymous') {
                    anonymous.innerHTML += data.chunk;
                } else if (data.type === 'deanonymized') {
                    deanonymized.innerHTML += data.chunk;
                } else if (data.type === 'status' && data.status === 'complete') {
                    console.log('Stream completado');
                    eventSource.close();
                }
            };
        }
    </script>
</body>
</html>
```

### 8. Solución de Problemas Comunes

#### Error: "Connection refused" en Redis
```bash
# Verificar si Redis está ejecutándose:
redis-cli ping

# Si no responde, iniciar Redis:
redis-server

# O en WSL:
sudo service redis-server start
```

#### Error: "ModuleNotFoundError"
```bash
# Verificar que el entorno virtual esté activado
# Reinstalar dependencias:
pip install -r requirements.txt
```

#### Error: Puerto 8000 en uso
```bash
# Usar puerto diferente:
python -m uvicorn app.main:app --reload --port 8001
```

#### Error: FastAPI no encuentra módulos
```bash
# Asegurarse de estar en el directorio correcto:
cd backend
python -m uvicorn app.main:app --reload
```

### 9. Verificación de Funcionamiento

#### ✅ Checklist de Verificación:

1. **Redis funcionando**: `redis-cli ping` responde `PONG`
2. **Servidor FastAPI**: http://localhost:8000 accesible
3. **Documentación**: http://localhost:8000/docs carga correctamente
4. **Sesión creada**: `/setup-dummy-session/test123` devuelve mensaje de éxito
5. **Estado de sesión**: `/session/test123/status` muestra `exists: true`
6. **Desanonimización**: Reemplaza correctamente "María González" → "Juan Pérez"
7. **Streaming**: `/dual-stream/test123` envía eventos Server-Sent Events

### 10. Datos de Prueba Disponibles

El sistema incluye los siguientes mapeos de prueba:

| Dato Original | Dato Anonimizado |
|---------------|------------------|
| Juan Pérez | María González |
| juan.perez@email.com | maria.gonzalez@email.com |
| 612345678 | 687654321 |
| 12345678A | 87654321B |
| Calle Mayor 123 | Avenida Libertad 456 |
| Madrid | Barcelona |
| 28001 | 08001 |
| Banco Santander | Banco BBVA |
| ES91 2100 0418 4502 0005 1332 | ES76 0182 6473 8901 2345 6789 |

### 11. Parar el Sistema

```bash
# Parar FastAPI: Ctrl+C en la terminal del servidor

# Parar Redis:
redis-cli shutdown

# O en WSL:
sudo service redis-server stop

# Desactivar entorno virtual:
deactivate
```

## 🎯 Resultado Final

Si todo funciona correctamente, tendrás:
- ✅ Sistema de desanonimización en tiempo real funcionando
- ✅ API REST completa con documentación
- ✅ Streaming dual mostrando versión anonimizada y desanonimizada simultáneamente
- ✅ Gestión de sesiones con TTL automático
- ✅ Interfaz web para pruebas