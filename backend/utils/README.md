# 🛠️ Backend Utils - Herramientas de Testing y Monitoreo

Esta carpeta contiene utilidades para testing, monitoreo y verificación del backend Shield AI.

## 📁 Estructura de Archivos

```
backend/utils/
├── __init__.py                    # Inicialización del paquete
├── README.md                      # Esta documentación
├── stress_test_backend.py         # 🔥 Stress testing avanzado
├── quick_stress_test.py          # 🏃‍♂️ Pruebas rápidas
├── monitor_stress_test.py        # 📊 Monitoreo en tiempo real
└── test_metricas_sistema.py      # 🧪 Verificación de métricas
```

## 🚀 Scripts Disponibles

### 1. **Stress Test Avanzado** (`stress_test_backend.py`)
Pruebas exhaustivas con análisis estadístico detallado.

```bash
# Preset ligero (recomendado para desarrollo)
python stress_test_backend.py --preset light

# Preset medio (testing de features)
python stress_test_backend.py --preset medium

# Preset pesado (pre-producción)
python stress_test_backend.py --preset heavy

# Configuración personalizada
python stress_test_backend.py --concurrent 15 --total 200 --timeout 30
```

**Características:**
- ✅ Pruebas asíncronas con `asyncio` y `aiohttp`
- ✅ Análisis P95, mediana, promedio
- ✅ Resultados guardados en JSON
- ✅ Múltiples endpoints simultáneos

### 2. **Quick Stress Test** (`quick_stress_test.py`)
Pruebas rápidas para verificación diaria.

```bash
# Prueba básica
python quick_stress_test.py

# Configuración ligera para desarrollo
python quick_stress_test.py --threads 3 --requests 5

# Configuración moderada
python quick_stress_test.py --threads 10 --requests 20
```

**Características:**
- ✅ Ejecución rápida (1-2 minutos)
- ✅ Resultados inmediatos en consola
- ✅ Ideal para verificación post-desarrollo

### 3. **Monitor con Stress Test** (`monitor_stress_test.py`)
Monitoreo de métricas en tiempo real durante pruebas.

```bash
# Ejecutar con monitoreo automático
python monitor_stress_test.py
```

**Características:**
- ✅ Monitoreo CPU, RAM, RPS en tiempo real
- ✅ Gráficos automáticos (requiere matplotlib)
- ✅ Reporte JSON de métricas temporales
- ✅ Análisis de performance temporal

### 4. **Test de Métricas del Sistema** (`test_metricas_sistema.py`)
Verificación de métricas Prometheus del backend.

```bash
# Verificar métricas disponibles
python test_metricas_sistema.py
```

**Características:**
- ✅ Verifica métricas de CPU y memoria
- ✅ Valida queries del dashboard Grafana
- ✅ Detecta problemas de configuración

## 🎯 Endpoints Testeados

Todos los scripts prueban estos endpoints principales:

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/health` | GET | Health check básico |
| `/metrics` | GET | Métricas Prometheus |
| `/anonymize` | POST | Anonimización de texto |
| `/chat/streaming` | POST | Chat streaming con LLM |
| `/anonymize/session/{id}/anonymized-request` | GET | Deanonimización |

## 📊 Métricas Monitoreadas

- **System CPU Usage** - Porcentaje de uso del procesador
- **System Memory Usage** - Uso de memoria en bytes/GB
- **HTTP Requests Rate** - Requests por segundo
- **Response Time** - Tiempo de respuesta (avg, P95)
- **Success Rate** - Porcentaje de requests exitosos
- **PII Detection Errors** - Errores en detección PII
- **Redis Connection Status** - Estado de conexión Redis

## 🔧 Dependencias

### Básicas (incluidas en Python):
- `asyncio`, `threading`, `statistics`
- `json`, `time`, `datetime`
- `argparse`, `typing`

### Externas:
```bash
# Para stress tests básicos
pip install requests aiohttp

# Para gráficos (opcional)
pip install matplotlib
```

## 📈 Casos de Uso Recomendados

### 👨‍💻 **Desarrollo Diario**
```bash
# Verificación rápida después de cambios
cd backend/utils
python quick_stress_test.py --threads 3 --requests 5
```

### 🧪 **Testing de Features**
```bash
# Test moderado para nuevas funcionalidades
cd backend/utils
python stress_test_backend.py --preset medium
```

### 🚀 **Pre-Producción**
```bash
# Test intensivo antes de despliegue
cd backend/utils
python stress_test_backend.py --preset heavy

# Con monitoreo completo
python monitor_stress_test.py
```

### 🔍 **Troubleshooting**
```bash
# Verificar métricas del sistema
cd backend/utils
python test_metricas_sistema.py

# Monitoreo detallado para debuggear
python monitor_stress_test.py
```

## 📋 Interpretación de Resultados

### ✅ **Buenos Resultados:**
- Success Rate > 95%
- Response Time < 1s promedio
- CPU < 80% durante el test
- Sin timeouts ni errores de conexión

### ⚠️ **Resultados Moderados:**
- Success Rate 90-95%
- Response Time 1-3s promedio
- CPU 80-90%
- Algunos timeouts ocasionales

### ❌ **Problemas Detectados:**
- Success Rate < 90%
- Response Time > 3s promedio
- CPU > 90% sostenido
- Muchos errores de conexión/timeout

## 🎨 Archivos Generados

Los scripts generan automáticamente:

- `stress_test_results_YYYYMMDD_HHMMSS.json` - Resultados detallados (advanced)
- `metrics_report_YYYYMMDD_HHMMSS.json` - Métricas temporales (monitor)
- `metrics_chart_YYYYMMDD_HHMMSS.png` - Gráfico de performance (monitor)

## 🔗 Integración con Grafana

Los tests generan actividad que puedes monitorear en:

- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:8000/metrics

### Métricas a Observar:
1. **HTTP Requests Rate** - Debe incrementar durante el test
2. **Response Time** - Debe mantenerse estable
3. **CPU Usage** - Monitorear picos
4. **Memory Usage** - Verificar no hay memory leaks

## 💡 Tips y Best Practices

### 🎯 **Para Desarrollo:**
- Ejecuta `quick_stress_test.py` después de cambios importantes
- Usa preset `light` para no sobrecargar el sistema local
- Combina con monitoreo en Grafana

### 🔧 **Para CI/CD:**
- Integra `stress_test_backend.py --preset light` en pipeline
- Establece umbrales: success rate > 95%, response time < 2s
- Guarda artifacts de los resultados JSON

### 🚀 **Para Producción:**
- Ejecuta tests en staging idéntico a producción
- Usa preset `heavy` para simular carga real
- Combina con monitoreo de métricas del sistema host

## 🚨 Troubleshooting Común

### Error: "Connection refused"
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health
```

### Error: "Module not found"
```bash
# Instalar dependencias
pip install requests aiohttp matplotlib
```

### Resultados inconsistentes
- Ejecutar múltiples veces y promediar
- Asegurar que no hay otros procesos consumiendo recursos
- Usar monitoreo para identificar patrones

---

## 🎉 Ejemplo de Workflow Completo

```bash
# 1. Ir a la carpeta utils
cd backend/utils

# 2. Verificación rápida
python quick_stress_test.py --threads 3 --requests 5

# 3. Si todo OK, test más intenso  
python stress_test_backend.py --preset medium

# 4. Si hay problemas, monitoreo detallado
python monitor_stress_test.py

# 5. Verificar métricas del sistema
python test_metricas_sistema.py

# 6. Revisar resultados en Grafana
# http://localhost:3000
```

¡Las herramientas están listas para mantener tu backend en óptimas condiciones! 🚀