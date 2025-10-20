# Shield AI - Sistema de Anonimización Inteligente de Datos

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.2-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2.0-blue.svg)](https://reactjs.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)](LICENSE)

*Sistema avanzado de detección, anonimización y desanonimización de datos personales (PII) desarrollado para Scalian*

</div>

## Descripción

Shield AI es una solución empresarial completa para el tratamiento seguro de datos personales que combina inteligencia artificial, técnicas de anonimización avanzadas y capacidades de procesamiento en tiempo real. Desarrollado específicamente para Scalian, permite el cumplimiento normativo GDPR mientras mantiene la utilidad de los datos para análisis y procesamiento.

### Propósito

En el contexto empresarial actual, las organizaciones necesitan procesar datos personales de manera segura y conforme a las regulaciones. Shield AI soluciona este desafío proporcionando:

- **Detección automática** de información personal (PII) en textos, documentos e imágenes
- **Anonimización inteligente** que preserva la estructura y utilidad de los datos
- **Desanonimización controlada** para restaurar datos originales cuando sea necesario
- **Procesamiento en tiempo real** con capacidades de streaming
- **Interfaz web moderna** para facilitar la interacción del usuario

## Características Principales

### Detección de PII Avanzada
- **Modelos de IA especializados**: Utiliza transformers de HuggingFace optimizados para español
- **Detección multi-modal**: Soporte para texto, documentos (PDF/Word/Excel) e imágenes
- **Patrones regex mejorados**: Detección precisa de DNI, NIE, IBAN, teléfonos, emails
- **Validación inteligente**: Verificación de integridad para números de identificación

### Anonimización Inteligente
- **Datos sintéticos realistas**: Generación usando Faker con preservación de formato
- **Mapeo consistente**: Mismas entidades generan mismos reemplazos
- **Preservación de contexto**: Mantiene dominios de email y formatos originales
- **Múltiples estrategias**: Pseudonimización, tokens o datos sintéticos

### Desanonimización Segura
- **Sesiones aisladas**: Cada proceso mantiene su propio contexto
- **Streaming en tiempo real**: Procesamiento chunk por chunk
- **Mapeo bidireccional**: Restauración precisa de datos originales
- **Control de TTL**: Expiración automática de mappings por seguridad

### Procesamiento de Documentos
- **Formatos múltiples**: PDF, Word (.docx), Excel (.xlsx)
- **Extracción robusta**: Manejo de tablas, formularios y texto libre
- **Preservación de estructura**: Mantiene formato y organización original

### Anonimización de Imágenes
- **Detección facial**: RetinaFace, MTCNN, Haar Cascades
- **Múltiples técnicas**: Blur, pixelado, ocultación
- **Desanonimización**: Restauración de regiones originales

### Frontend Moderno
- **Interfaz responsiva**: Diseñada con React 18 y Tailwind CSS
- **Streaming visual**: Visualización en tiempo real del proceso
- **Tres paneles sincronizados**: Datos anonimizados, respuesta IA, respuesta final
- **Drag & drop**: Carga intuitiva de archivos e imágenes
- **Descarga y copia**: Funciones para exportar resultados

## Arquitectura

### Estructura General del Proyecto
```
shield_ai/
├── README.md                 # Documentación principal
├── .env                      # Variables de entorno principales
├── .env.example             # Plantilla de variables de entorno
├── .gitignore               # Archivos ignorados por Git
├── docker-compose.yml       # Orquestación de servicios
├── dashboard_metricas.py    # Dashboard simplificado
├── requirements.txt         # Dependencias Python globales
├── package.json             # Dependencias Node.js globales
├── package-lock.json        # Lock file Node.js
├── backend/                 # Aplicación FastAPI
├── frontend/                # Aplicación React
├── monitoring/              # Sistema de monitoreo
├── docs/                    # Documentación técnica
└── scripts/                 # Scripts de configuración
```

### Backend - FastAPI
```
backend/
├── Dockerfile
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── pii_cache.pkl
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── routes/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── config.py
│   │   └── redis_client.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── metrics_middleware.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   └── responses.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_processing/
│   │   ├── session/
│   │   ├── chunk_deanonymizer.py
│   │   ├── deanonymization_service.py
│   │   ├── enhanced_phone_deanonymizer.py
│   │   ├── image_anonymizer.py
│   │   ├── llm_integration.py
│   │   ├── pii_detector.py
│   │   ├── revalidate_and_review.py
│   │   ├── run_cli_wrapper.py
│   │   ├── run_interactive.ps1
│   │   ├── synthetic_data_generator.py
│   │   └── word_by_word_deanonymizer.py
│   ├── utils/
│       ├── __init__.py
│       ├── helpers.py
│       ├── test.html
│       └── test_client.py
├── tests/
│   ├── __init__.py
│   ├── find_env.py
│   ├── locustfile.py
│   ├── test_document_processing.py
│   ├── test_excel_anonymization.py
│   ├── test_groq.py
│   ├── test_llm_integration.py
│   ├── test_pdf_anonymization.py
│   ├── test_word_anonymization.py
│   └── fixtures/
│       ├── excel_mixed.xlsx
│       ├── excel_narrative.xlsx
│       ├── excel_simple_form.xlsx
│       ├── excel_table.xlsx
│       ├── pdf_mixed.pdf
│       ├── pdf_narrative.pdf
│       ├── pdf_simple_form.pdf
│       ├── pdf_table.pdf
│       ├── word_mixed.docx
│       ├── word_narrative.docx
│       ├── word_simple_form.docx
│       └── word_table.docx
└── utils/
    ├── README.md
    ├── README_STRESS_TESTING.md
    ├── STRESS_TESTING_README.md
    ├── STRESS_TESTING_SUMMARY.md
    ├── monitor_stress_test.py
    ├── quick_stress_test.py
    ├── stress_test_backend.py
    └── test_metricas_sistema.py
```

### Frontend - React
```
frontend/
├── Dockerfile
├── README.md
├── README_STREAMING.md
├── .env.example
├── nginx.conf
├── package.json
├── package-lock.json
├── postcss.config.js
├── tailwind.config.js
├── public/
│   ├── favicon.ico
│   └── index.html
└── src/
    ├── App.js
    ├── App.css
    ├── index.js
    ├── index.css
    ├── components/
    │   ├── Common/
    │   │   ├── Button.js
    │   │   ├── TextArea.js
    │   │   ├── FileUpload.js
    │   │   ├── StreamingText.js
    │   │   └── ErrorBoundary.js
    │   ├── Layout/
    │   │   ├── Header.js
    │   │   ├── MainContainer.js
    │   │   └── Footer.js
    │   └── Panels/
    │       ├── InputPanel.js
    │       ├── ProcessingPanels.js
    │       └── ImageProcessingPanels.js
    ├── contexts/
    │   └── AppContext.js
    ├── services/
    │   ├── anonymizationService.js
    │   └── imageAnonymizationService.js
    └── utils/
        └── cn.js
```

### Servicios de Infraestructura
- **Redis**: Almacenamiento de mappings de anonimización con TTL
- **Prometheus**: Métricas y monitoreo de rendimiento
- **Grafana**: Dashboards y visualización de métricas
- **AlertManager**: Sistema de alertas automáticas
- **Nginx**: Servidor web de producción para frontend

## Instalación y Configuración

### Prerrequisitos
- Python 3.10+
- Node.js 18+
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

### 2. Configuración del Frontend

```bash
# Ir al directorio del frontend
cd frontend

# Instalar dependencias
npm install

# Configurar variables de entorno
cp .env.example .env
# Editar .env con la URL del backend
```

### 3. Configuración de Redis

```bash
# Opción 1: Docker (recomendado)
docker run -d -p 6379:6379 --name shield-redis redis:alpine

# Opción 2: Instalación local
# Seguir instrucciones de instalación de Redis para tu SO
```

### 4. Configuración de Variables de Entorno

#### Variables Principales (.env en raíz del proyecto)
```bash
# Groq API
GROK_API_KEY=your-groq-api-key

# Redis Configuration
SHIELD_AI_REDIS_HOST=localhost
SHIELD_AI_REDIS_PORT=6379
SHIELD_AI_REDIS_DB=0
SHIELD_AI_REDIS_PASSWORD= # De momento vacío, no hay password
SHIELD_AI_REDIS_DECODE_RESPONSES=true
SHIELD_AI_REDIS_CONNECTION_POOL_MAX_CONNECTIONS=500

# Session Settings
SHIELD_AI_SESSION_TTL=3600 # 1 hora
SHIELD_AI_SESSION_KEY_PREFIX=anon_map

# Otras claves API (opcional)
OPENAI_API_KEY=tu_clave_openai
ANTHROPIC_API_KEY=tu_clave_anthropic
```

#### Frontend (.env)
```bash
# API Configuration
REACT_APP_API_ENDPOINT=http://localhost:8000

# App Configuration
REACT_APP_APP_NAME=Shield AI
REACT_APP_VERSION=1.0.0

# Feature Flags
REACT_APP_ENABLE_FILE_UPLOAD=true
REACT_APP_ENABLE_IMAGE_UPLOAD=true
REACT_APP_ENABLE_STREAMING=true

# Development
REACT_APP_DEBUG_MODE=false
```

## Configuración Docker

### Estructura Docker

El proyecto incluye configuración Docker para facilitar el despliegue:

```
shield_ai/
├── backend/Dockerfile         # Imagen para API FastAPI
├── frontend/Dockerfile        # Imagen para aplicación React
├── docker-compose.yml         # Orquestación de servicios
└── monitoring/docker-compose.yml  # Stack de monitoreo
```

### Despliegue con Docker Compose

```bash
# Construir y ejecutar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar servicios
docker-compose down
```

### Servicios Incluidos

- **Backend API**: Puerto 8000
- **Frontend Web**: Puerto 3000 (desarrollo) / 80 (producción)
- **Redis**: Puerto 6379
- **Prometheus**: Puerto 9090 (monitoreo)
- **Grafana**: Puerto 3001 (dashboards)

### Variables de Entorno para Docker

```bash
# Para producción con Docker
SHIELD_AI_ENVIRONMENT=production
SHIELD_AI_DEBUG=false
SHIELD_AI_REDIS_HOST=redis
SHIELD_AI_CORS_ORIGINS=https://tu-dominio.com

# Frontend
REACT_APP_API_ENDPOINT=https://api.tu-dominio.com
REACT_APP_DEBUG_MODE=false
```

## Uso

### Iniciar el Sistema Completo

#### Opción 1: Desarrollo Local

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm start
```

#### Opción 2: Desarrollo con Scripts

```bash
# Usar script de configuración automática
chmod +x scripts/setup.sh
./scripts/setup.sh

# El script configura automáticamente:
# - Backend con uvicorn
# - Frontend con npm start
# - Redis si es necesario
```

### Acceso a los Servicios

- **Frontend (React)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Métricas**: http://localhost:8000/metrics

### Ejemplos de Uso

#### 1. Interfaz Web (Principal)

1. **Abrir la aplicación**: Ir a http://localhost:3000
2. **Introducir datos**: Escribir texto con información personal o subir archivos
3. **Procesar**: Hacer clic en "Iniciar Proceso"
4. **Visualizar resultados**: Ver los tres paneles con el proceso completo

#### 2. Streaming con Respuesta Visual

La aplicación muestra tres paneles sincronizados:
- **Panel Naranja**: Datos anonimizados enviados a la IA
- **Panel Azul**: Respuesta de la IA (con tokens anonimizados)
- **Panel Verde**: Respuesta final con datos restaurados

## Características del Frontend

### Paneles de Procesamiento

El frontend incluye **tres paneles sincronizados** que muestran el proceso completo:

1. **Panel de Datos Anonimizados** (Naranja)
   - Muestra el texto con PII reemplazada por tokens
   - Botones para copiar y descargar
   - Indicador de datos protegidos

2. **Panel de Respuesta del Modelo** (Azul)
   - Visualización en streaming de la respuesta de IA
   - Usa tokens anonimizados
   - Indicador de streaming activo

3. **Panel de Respuesta Final** (Verde)
   - Texto con datos originales restaurados
   - Desanonimización en tiempo real
   - Resultado final para el usuario

### Características de UX

- **Streaming visual**: Ver el texto aparecer palabra por palabra
- **Drag & Drop**: Arrastrar archivos directamente
- **Múltiples formatos**: PDF, Word, Excel, imágenes
- **Responsive design**: Funciona en desktop y móvil
- **Error boundaries**: Manejo robusto de errores
- **Loading states**: Indicadores de progreso claros

### Tecnologías Frontend

- **React 18**: Framework principal con hooks modernos
- **Tailwind CSS 3**: Estilos utilitarios y responsivos
- **Axios**: Cliente HTTP con interceptors
- **Lucide React**: Iconos consistentes
- **Context API**: Manejo de estados globales

## Monitoreo

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
- **Frontend**: Tiempo de carga, interacciones de usuario

## Testing

### Tests Backend
```bash
# Tests de procesamiento de documentos
pytest backend/tests/test_document_processing.py -v

# Tests extracción y anonimización archivos Word
pytest backend/tests/test_word_anonymization.py -v -s

# Tests extracción y anonimización archivos PDF
pytest backend/tests/test_pdf_anonymization.py -v -s

# Tests extracción y anonimización archivos Excel
pytest backend/tests/test_excel_anonymization.py -v

# Ejecutar todos los tests de documentos
pytest backend/tests/test_word_anonymization.py backend/tests/test_pdf_anonymization.py backend/tests/test_excel_anonymization.py -v

# Test de aislamiento de sesiones (verificar que no hay mezcla entre mapas de anonimización)
pytest backend/tests/test_session_isolation.py -v -s
```

### Tests Frontend
```bash
# Tests de componentes React
cd frontend
npm test

# Coverage
npm test -- --coverage

# E2E tests (opcional)
npm run test:e2e
```

### Tests de Documentos
```bash
# Tests específicos para diferentes formatos de documentos
pytest backend/tests/test_pdf_anonymization.py -v -s
pytest backend/tests/test_word_anonymization.py -v -s
pytest backend/tests/test_excel_anonymization.py -v
```

## Despliegue

### Desarrollo Local
```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (en otra terminal)
cd frontend
npm start
```

### Entorno de Producción

Para producción, se recomienda:
- **Backend**: Usar gunicorn con workers múltiples
- **Frontend**: Build optimizado servido por Nginx
- **Redis**: Instancia dedicada con persistencia
- **Monitoreo**: Stack completo Prometheus/Grafana

```bash
# Build de producción del frontend
cd frontend
npm run build

# Servir con nginx (configuración en nginx.conf)
```

## Seguridad y Cumplimiento

### Características de Seguridad
- **Aislamiento de sesiones**: Cada proceso es independiente
- **TTL automático**: Expiración de datos sensibles
- **Logs auditables**: Trazabilidad completa de operaciones
- **Validación de entrada**: Sanitización de todos los inputs
- **Headers de seguridad**: CSP, HSTS, X-Frame-Options en Nginx
- **CORS configurado**: Restricción de orígenes permitidos

### Cumplimiento GDPR
- **Anonimización reversible**: Cumple con el derecho al olvido
- **Minimización de datos**: Solo procesa datos necesarios
- **Transparencia**: Logs detallados de todas las operaciones
- **Seguridad por diseño**: Arquitectura orientada a la privacidad
- **Consentimiento claro**: Interface que informa sobre el procesamiento

## Sistema de Streaming Avanzado

### Características del Streaming

- **Dual streaming**: Respuestas anónimas y desanonimizadas simultáneas
- **Palabra por palabra**: Granularidad ultra-fina (150-250ms por palabra)
- **Timing natural**: Variabilidad que simula escritura humana
- **Sincronización en tiempo real**: Tres paneles actualizados simultáneamente
- **Manejo de estado robusto**: Referencias persistentes durante el streaming

### Flujo del Sistema
```
Usuario Input → Anonimización → LLM API → Streaming → Desanonimización → UI
     ↓              ↓              ↓           ↓            ↓            ↓
Panel Input   Panel 1 (PII)   Procesando  Panel 2    Panel 3     Usuario Final
```

## Rendimiento

### Benchmarks Típicos
- **Detección PII**: ~500 documentos/minuto
- **Anonimización**: ~50ms por documento promedio
- **Streaming**: <100ms latencia por chunk
- **Desanonimización**: ~10ms por operación
- **Frontend**: <2s tiempo de carga inicial
- **UI responsiva**: <16ms tiempo de frame

### Optimizaciones
- **Backend**: Cache de modelos HuggingFace, pooling Redis
- **Frontend**: Code splitting, lazy loading, memoización React
- **Networking**: Compresión gzip, CDN para assets estáticos
- **Database**: Índices Redis, TTL optimizado

## Documentación

- **[Cómo Ejecutar](docs/COMO_EJECUTAR.md)**: Guía detallada de instalación
- **[Sistema PII](docs/pii_detection_system.md)**: Arquitectura de detección
- **[Desanonimización](docs/desanonimizacion_explicacion.md)**: Proceso de restauración
- **[Frontend Streaming](frontend/README_STREAMING.md)**: Sistema de streaming detallado
- **[Configuración Grafana](monitoring/GRAFANA_SETUP.md)**: Setup de monitoreo

## Soporte

### Logs y Debugging
```bash
# Logs del backend
tail -f backend/app.log

# Logs del frontend (desarrollo)
# Ver consola del navegador

# Logs de Redis
docker logs shield-redis

# Métricas en tiempo real
curl http://localhost:8000/metrics/health
```

### Problemas Comunes

#### Backend
- **Redis desconectado**: Verificar Docker/servicio Redis
- **Modelos no descargan**: Verificar conexión a HuggingFace
- **Memory errors**: Aumentar límites Docker/sistema

#### Frontend
- **API no responde**: Verificar REACT_APP_API_ENDPOINT en .env
- **CORS errors**: Configurar SHIELD_AI_CORS_ORIGINS en backend
- **Build fails**: Limpiar node_modules y reinstalar

### Enlaces Útiles
- **Issues**: Reportar problemas en el repositorio
- **Documentación API**: http://localhost:8000/docs
- **Métricas**: http://localhost:8000/metrics
- **Status**: http://localhost:3000/health (frontend)

## Equipo de Desarrollo

Este proyecto ha sido desarrollado por un talentoso equipo de profesionales:

### Scrum Master
**Pepe Ruiz**  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/peperuiznieto/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/peperuizdev)

### Product Owner  
**Maximiliano Carlos Scarlatto**  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/maximiliano-scarlato-830a94284/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MaximilianoScarlato)

### Developers

**Polina Terekhova**  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/polina-terekhova-pavlova/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/fintihlupik)

**Mariela Adimari**  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mariela-adimari/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/marie-adi)

**Alejandro Rajado**  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/alejandro-rajado-mart%C3%ADn/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Alex-rajas)

### Metodología de Trabajo

El equipo sigue metodologías ágiles con:
- **Sprints de 1 semana** con retrospectivas y planificación
- **5 sprints totales** para el desarrollo completo del proyecto
- **Daily standups** para coordinación diaria
- **Code reviews** obligatorios con pull requests antes de merge

### Agradecimientos

Especial reconocimiento a **Scalian** por confiar en nuestro equipo para desarrollar esta solución innovadora de anonimización inteligente.

## Licencia

Este proyecto es propiedad de **Scalian** y está protegido por derechos de autor. Uso exclusivo para proyectos autorizados de Scalian.

---

<div align="center">

**Desarrollado por el equipo de SHIELD AI para Scalian**

*Sistema de anonimización inteligente - Protegiendo datos, preservando valor*

**Stack**: React 18 + FastAPI + Redis + Docker + Tailwind CSS

</div>
