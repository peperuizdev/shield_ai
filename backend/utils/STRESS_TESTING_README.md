# 🚀 STRESS TESTING SUITE - Backend Shield AI

Conjunto de herramientas para realizar pruebas de carga y estrés al backend Shield AI.

## � **UBICACIÓN ACTUALIZADA**
Los scripts de stress testing han sido movidos a: **`backend/utils/`**

```bash
# Navegar a la carpeta de utilidades
cd backend/utils

# Ejecutar tests desde ahí
python quick_stress_test.py --threads 3 --requests 5
```

## �📋 Herramientas Disponibles

### 1. 🏃‍♂️ Quick Stress Test (`backend/utils/quick_stress_test.py`)
**Prueba rápida y simple**

```bash
# Navegar a utils
cd backend/utils

# Prueba básica
python quick_stress_test.py

# Configuración personalizada
python quick_stress_test.py --threads 10 --requests 20 --url http://localhost:8000

# Prueba ligera (recomendado para desarrollo)
python quick_stress_test.py --threads 3 --requests 5
```

**Características:**
- ✅ Test rápido (1-2 minutos)
- ✅ Resultados inmediatos
- ✅ Ideal para verificación rápida
- ✅ Bajo impacto en el sistema

### 2. 🔥 Advanced Stress Test (`backend/utils/stress_test_backend.py`)
**Prueba completa y detallada**

```bash
# Navegar a utils
cd backend/utils

# Prueba básica
python stress_test_backend.py

# Presets predefinidos
python stress_test_backend.py --preset light     # 5 hilos, 50 requests
python stress_test_backend.py --preset medium    # 15 hilos, 200 requests  
python stress_test_backend.py --preset heavy     # 25 hilos, 500 requests
python stress_test_backend.py --preset extreme   # 50 hilos, 1000 requests

# Configuración manual
python stress_test_backend.py --concurrent 20 --total 300 --timeout 60
```

**Características:**
- ✅ Prueba exhaustiva y asíncrona
- ✅ Análisis estadístico detallado
- ✅ Múltiples endpoints simultáneos
- ✅ Guardado automático de resultados JSON
- ✅ Métricas P95, mediana, etc.

### 3. 📊 Monitor con Stress Test (`monitor_stress_test.py`)
**Monitoreo en tiempo real durante las pruebas**

```bash
# Ejecutar con monitoreo
python monitor_stress_test.py
```

**Características:**
- ✅ Monitoreo de CPU, RAM, RPS en tiempo real
- ✅ Gráficos automáticos (requiere matplotlib)
- ✅ Reporte JSON con todas las métricas
- ✅ Análisis de rendimiento temporal

## 🎯 Endpoints Testeados

Todos los scripts prueban estos endpoints principales:

1. **`/health`** - Health check básico
2. **`/metrics`** - Métricas Prometheus 
3. **`/anonymize`** - Anonimización de texto
4. **`/chat/streaming`** - Chat streaming con LLM
5. **`/anonymize/session/{id}/anonymized-request`** - Deanonimización

## 📊 Métricas Monitoreadas

- **CPU Usage** - Porcentaje de uso del procesador
- **Memory Usage** - Uso de memoria en GB
- **Response Time** - Tiempo de respuesta promedio/P95
- **Requests per Second** - Throughput del sistema
- **Success Rate** - Porcentaje de requests exitosos
- **Error Count** - Número de errores por endpoint

## 🔧 Instalación de Dependencias

```bash
# Dependencias básicas (incluidas en Python)
# requests, threading, asyncio, aiohttp

# Para gráficos avanzados (opcional)
pip install matplotlib

# Para stress test completo
pip install aiohttp
```

## 🚀 Casos de Uso Recomendados

### 📈 Desarrollo Diario
```bash
# Verificación rápida durante desarrollo
python quick_stress_test.py --threads 3 --requests 5
```

### 🧪 Testing de Features
```bash
# Test moderado para nuevas funcionalidades  
python stress_test_backend.py --preset medium
```

### 🔥 Pre-Producción
```bash
# Test intensivo antes de despliegue
python stress_test_backend.py --preset heavy

# Con monitoreo completo
python monitor_stress_test.py
```

### 🚨 Troubleshooting
```bash
# Test con monitoreo para debuggear problemas
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

### Quick Test:
- Resultados en consola únicamente

### Advanced Test:
- `stress_test_results_YYYYMMDD_HHMMSS.json` - Resultados detallados

### Monitor Test:
- `metrics_report_YYYYMMDD_HHMMSS.json` - Métricas temporales
- `metrics_chart_YYYYMMDD_HHMMSS.png` - Gráfico de rendimiento

## 🔗 Integration con Grafana

Los stress tests generan actividad que puedes monitorear en:

- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:8000/metrics

### Métricas a Observar en Grafana:
1. **HTTP Requests Rate** - Debe incrementar durante el test
2. **Response Time** - Debe mantenerse estable
3. **CPU Usage** - Monitorear picos
4. **Memory Usage** - Verificar no hay memory leaks
5. **PII Detection Errors** - Debe mantenerse en 0

## 💡 Consejos y Best Practices

### 🎯 **Para Desarrollo:**
- Usa `quick_stress_test.py` con configuración ligera
- Ejecuta tests después de cambios importantes
- Monitorea las métricas en Grafana

### 🔧 **Para CI/CD:**
- Integra `stress_test_backend.py --preset light` en pipeline
- Establece umbrales de success rate > 95%
- Guarda artifacts de los resultados JSON

### 🚀 **Para Producción:**
- Ejecuta tests en entorno staging idéntico a prod
- Usa `--preset heavy` para simular carga real
- Combina con monitoreo de métricas del sistema

### ⚡ **Optimización:**
- Si el Response Time es alto, revisar queries SQL/Redis
- Si la CPU es alta, considerar optimizaciones de código
- Si hay timeouts, ajustar configuración de timeouts
- Si hay memory leaks, revisar gestión de sesiones

## 🚨 Troubleshooting

### Error: "Connection refused"
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health
```

### Error: "Timeout"  
```bash
# Usar menos hilos o mayor timeout
python stress_test_backend.py --concurrent 5 --timeout 60
```

### Error: "Too many open files"
```bash
# En Linux/Mac, aumentar límite
ulimit -n 4096
```

### Resultados inconsistentes
- Asegurar que no hay otros procesos consumiendo recursos
- Ejecutar múltiples veces y promediar resultados
- Usar el monitoreo para identificar patrones

---

## 🎉 Ejemplo de Workflow Completo

```bash
# 1. Verificación rápida
python quick_stress_test.py --threads 3 --requests 5

# 2. Si todo OK, test más intenso
python stress_test_backend.py --preset medium

# 3. Si hay problemas, monitoreo detallado
python monitor_stress_test.py

# 4. Revisar métricas en Grafana
# http://localhost:3000

# 5. Optimizar código basado en resultados

# 6. Repetir hasta obtener resultados óptimos
```

¡Happy stress testing! 🚀