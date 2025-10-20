# Shield AI - Sistema de Anonimización Inteligente de Datos

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.2-green.svg)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)](LICENSE)

*Sistema avanzado de detección, anonimización y desanonimización de datos personales (PII) desarrollado para Scalian*

</div>

## 📋 Descripción

Shield AI es una solución empresarial completa para el tratamiento seguro de datos personales que combina inteligencia artificial, técnicas de anonimización avanzadas y capacidades de procesamiento en tiempo real. Desarrollado específicamente para Scalian, permite el cumplimiento normativo GDPR mientras mantiene la utilidad de los datos para análisis y procesamiento.

### 🎯 Propósito

En el contexto empresarial actual, las organizaciones necesitan procesar datos personales de manera segura y conforme a las regulaciones. Shield AI soluciona este desafío proporcionando:

- **Detección automática** de información personal (PII) en textos, documentos e imágenes
- **Anonimización inteligente** que preserva la estructura y utilidad de los datos
- **Desanonimización controlada** para restaurar datos originales cuando sea necesario
- **Procesamiento en tiempo real** con capacidades de streaming

## ✨ Características Principales

### 🔍 Detección de PII Avanzada
- **Modelos de IA especializados**: Utiliza transformers de HuggingFace optimizados para español
- **Detección multi-modal**: Soporte para texto, documentos (PDF/Word/Excel) e imágenes
- **Patrones regex mejorados**: Detección precisa de DNI, NIE, IBAN, teléfonos, emails
- **Validación inteligente**: Verificación de integridad para números de identificación

### 🛡️ Anonimización Inteligente
- **Datos sintéticos realistas**: Generación usando Faker con preservación de formato
- **Mapeo consistente**: Mismas entidades generan mismos reemplazos
- **Preservación de contexto**: Mantiene dominios de email y formatos originales
- **Múltiples estrategias**: Pseudonimización, tokens o datos sintéticos

### 🔓 Desanonimización Segura
- **Sesiones aisladas**: Cada proceso mantiene su propio contexto
- **Streaming en tiempo real**: Procesamiento chunk por chunk
- **Mapeo bidireccional**: Restauración precisa de datos originales
- **Control de TTL**: Expiración automática de mappings por seguridad

### 📄 Procesamiento de Documentos
- **Formatos múltiples**: PDF, Word (.docx), Excel (.xlsx)
- **Extracción robusta**: Manejo de tablas, formularios y texto libre
- **Preservación de estructura**: Mantiene formato y organización original

### 🖼️ Anonimización de Imágenes
- **Detección facial**: RetinaFace, MTCNN, Haar Cascades
- **Múltiples técnicas**: Blur, pixelado, ocultación
- **Desanonimización**: Restauración de regiones originales

## 🏗️ Arquitectura

### Backend (FastAPI)
```
backend/app/
├── main.py                 # Punto de entrada de la aplicación
├── core/                   # Configuración y componentes centrales
│   ├── app.py             # Configuración de FastAPI
│   ├── config.py          # Variables de entorno y configuración
│   └── redis_client.py    # Cliente Redis con pooling
├── api/routes/            # Endpoints REST
│   ├── anonymization.py   # Anonimización de texto
│   ├── chat.py           # Integración con LLMs
│   ├── deanonymization.py # Desanonimización
│   ├── document_processing.py # Procesamiento de documentos
│   ├── image_anonymization.py # Anonimización de imágenes
│   └── sessions.py       # Gestión de sesiones
├── services/              # Lógica de negocio
│   ├── pii_detector.py   # Pipeline principal de detección
│   ├── deanonymization_service.py # Servicios de desanonimización
│   ├── synthetic_data_generator.py # Generación de datos sintéticos
│   └── session/          # Gestión de sesiones en Redis
└── models/               # Modelos Pydantic para requests/responses
```

### Servicios de Infraestructura
- **Redis**: Almacenamiento de mappings de anonimización con TTL
- **Prometheus**: Métricas y monitoreo de rendimiento
- **Grafana**: Dashboards y visualización de métricas
- **AlertManager**: Sistema de alertas automáticas

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.10+
- Redis 7.0+
- Docker y Docker Compose (opcional)

### 1. Configuración del Backend

```bash
# Clonar el repositorio
git clone <repository-url>
cd shield_ai

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r backend/requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones
```

### 2. Configuración de Redis

```bash
# Opción 1: Docker (recomendado)
docker run -d -p 6379:6379 --name shield-redis redis:alpine

# Opción 2: Instalación local
# Seguir instrucciones de instalación de Redis para tu SO
```

### 3. Configuración de Variables de Entorno

```bash
# .env
SHIELD_AI_ENVIRONMENT=development
SHIELD_AI_DEBUG=true
SHIELD_AI_REDIS_HOST=localhost
SHIELD_AI_REDIS_PORT=6379
SHIELD_AI_REDIS_DB=0

# Claves API para LLMs (opcional)
GROK_API_KEY=tu_clave_grok
OPENAI_API_KEY=tu_clave_openai
ANTHROPIC_API_KEY=tu_clave_anthropic
```

## 🎮 Uso

### Iniciar el Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Métricas**: http://localhost:8000/metrics

### Ejemplos de Uso

#### Anonimización de Texto
```bash
curl -X POST "http://localhost:8000/anonymize/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Mi nombre es Juan Pérez, DNI 12345678A, email juan@empresa.com",
    "session_id": "test_session",
    "use_regex": true,
    "use_realistic_fake": true
  }'
```

#### Procesamiento de Documentos
```bash
curl -X POST "http://localhost:8000/document/process" \
  -F "file=@documento.pdf" \
  -F "session_id=doc_session" \
  -F "use_realistic_fake=true"
```

#### Streaming con LLM
```bash
curl -X POST "http://localhost:8000/chat/streaming" \
  -F "message=Analiza los datos de Juan Pérez" \
  -F "session_id=chat_session"
```

## 📊 Monitoreo

### Sistema de Métricas

Shield AI incluye un sistema completo de monitoreo:

```bash
# Iniciar stack de monitoreo
cd monitoring
./setup.sh start

# Acceder a los servicios
# Grafana: http://localhost:3000 (admin/admin123)
# Prometheus: http://localhost:9090
# AlertManager: http://localhost:9093
```

### Dashboard Simple
```bash
# Dashboard en terminal
python dashboard_metricas.py
```

### Métricas Principales
- **Detecciones PII**: Total y por tipo
- **Rendimiento**: Tiempo de procesamiento, throughput
- **Errores**: Tasas de error y fallos
- **Recursos**: Uso de memoria y CPU
- **Redis**: Métricas de almacenamiento y conexiones

## 🧪 Testing

### Tests Automatizados
```bash
# Tests unitarios
cd backend
pytest tests/ -v

# Tests de aislamiento de sesiones
python tests/test_session_isolation.py

# Tests de stress
python utils/stress_test_backend.py
```

### Tests de Documentos
```bash
# Tests específicos para documentos
pytest tests/test_pdf_anonymization.py -v -s
pytest tests/test_word_anonymization.py -v -s
```

## 📚 Documentación

- **[Cómo Ejecutar](docs/COMO_EJECUTAR.md)**: Guía detallada de instalación
- **[Sistema PII](docs/pii_detection_system.md)**: Arquitectura de detección
- **[Desanonimización](docs/desanonimizacion_explicacion.md)**: Proceso de restauración
- **[Configuración Grafana](monitoring/GRAFANA_SETUP.md)**: Setup de monitoreo

## 🔒 Seguridad y Cumplimiento

### Características de Seguridad
- **Aislamiento de sesiones**: Cada proceso es independiente
- **TTL automático**: Expiración de datos sensibles
- **Logs auditables**: Trazabilidad completa de operaciones
- **Validación de entrada**: Sanitización de todos los inputs

### Cumplimiento GDPR
- **Anonimización reversible**: Cumple con el derecho al olvido
- **Minimización de datos**: Solo procesa datos necesarios
- **Transparencia**: Logs detallados de todas las operaciones
- **Seguridad por diseño**: Arquitectura orientada a la privacidad

## 🛠️ Desarrollo

### Estructura de Contribución
```bash
# Instalar dependencias de desarrollo
pip install -r backend/requirements.txt

# Ejecutar tests antes de commit
pytest tests/ -v --cov=app

# Verificar estilo de código
black backend/app/
flake8 backend/app/
```

### Agregar Nuevos Detectores
1. Implementar en `services/pii_detector.py`
2. Agregar patrones regex en `_regex_patterns()`
3. Añadir validación en `validate_mapping()`
4. Crear tests específicos

## 📈 Rendimiento

### Benchmarks Típicos
- **Detección PII**: ~500 documentos/minuto
- **Anonimización**: ~50ms por documento promedio
- **Streaming**: <100ms latencia por chunk
- **Desanonimización**: ~10ms por operación

### Optimizaciones
- Cache de modelos HuggingFace
- Pooling de conexiones Redis
- Procesamiento asíncrono
- Streaming chunked para documentos grandes

## 🆘 Soporte

### Logs y Debugging
```bash
# Logs del backend
tail -f backend/app.log

# Logs de Redis
docker logs shield-redis

# Métricas en tiempo real
curl http://localhost:8000/metrics/health
```

### Problemas Comunes
- **Redis desconectado**: Verificar Docker/servicio Redis
- **Modelos no descargan**: Verificar conexión a HuggingFace
- **Memory errors**: Aumentar límites Docker/sistema

## 📄 Licencia

Este proyecto es propiedad de **Scalian** y está protegido por derechos de autor. Uso exclusivo para proyectos autorizados de Scalian.

---

<div align="center">

**Desarrollado con ❤️ para Scalian**

*Sistema de anonimización inteligente - Protegiendo datos, preservando valor*

</div>