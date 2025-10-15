# 🛠️ Backend Utils - Herramientas de Testing y Monitoreo

Esta carpeta contiene utilidades para testing, monitoreo y verificación del backend Shield AI.

## 📁 Estructura de Archivos

```
backend/utils/
├── __init__.py                      # Inicialización del paquete
├── README.md                        # Esta documentación
├── stress_test_backend.py           # 🔥 Stress testing avanzado  
├── quick_stress_test.py            # 🏃‍♂️ Pruebas rápidas
├── monitor_stress_test.py          # 📊 Monitoreo en tiempo real
├── test_metricas_sistema.py        # 🧪 Verificación de métricas
├── STRESS_TESTING_README.md        # 📖 Documentación detallada
├── STRESS_TESTING_SUMMARY.md       # 📊 Resumen y resultados
└── stress_test_results_*.json      # 💾 Archivos de resultados
```

## 🚀 Scripts de Stress Testing

### 1. **🏃‍♂️ Quick Stress Test** (`quick_stress_test.py`)
**Prueba rápida y simple para verificación diaria**

```bash
# Prueba básica
python quick_stress_test.py

# Configuración ligera (recomendado para desarrollo)
python quick_stress_test.py --threads 3 --requests 5

# Configuración personalizada
python quick_stress_test.py --threads 10 --requests 20 --url http://localhost:8000
```

**Características:**
- ✅ Test rápido (1-2 minutos)
- ✅ Resultados inmediatos en consola
- ✅ Ideal para verificación post-desarrollo
- ✅ Bajo impacto en el sistema

### 2. **🔥 Advanced Stress Test** (`stress_test_backend.py`)
**Prueba completa y detallada con análisis estadístico**

```bash
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
- ✅ Análisis estadístico detallado (P95, mediana, etc.)
- ✅ Múltiples endpoints simultáneos
- ✅ Guardado automático de resultados JSON
- ✅ Control granular de concurrencia y timeouts

### 3. **📊 Monitor con Stress Test** (`monitor_stress_test.py`)
**Monitoreo en tiempo real durante las pruebas**

```bash
# Ejecutar con monitoreo automático
python monitor_stress_test.py
```

**Características:**
- ✅ Monitoreo de CPU, RAM, RPS en tiempo real
- ✅ Gráficos automáticos (requiere matplotlib)
- ✅ Reporte JSON con todas las métricas temporales
- ✅ Análisis de rendimiento temporal
- ✅ Integración con quick_stress_test.py

### 4. **🧪 Test de Métricas del Sistema** (`test_metricas_sistema.py`)
**Verificación de métricas Prometheus del backend**

```bash
# Verificar métricas disponibles
python test_metricas_sistema.py
```

**Características:**
- ✅ Verifica métricas de CPU y memoria del sistema
- ✅ Valida queries del dashboard Grafana
- ✅ Detecta problemas de configuración
- ✅ Confirma ausencia de métricas Node Exporter

## 🎯 Endpoints Testeados

Todos los scripts prueban estos endpoints principales:

| Endpoint | Método | Propósito | Datos Enviados |
|----------|--------|-----------|----------------|
| `/health` | GET | Health check básico | - |
| `/metrics` | GET | Métricas Prometheus | - |
| `/anonymize` | POST | Anonimización de texto | text, session_id |
| `/chat/streaming` | POST | Chat streaming con LLM | message, session_id |
| `/anonymize/session/{id}/anonymized-request` | GET | Deanonimización | session_id en URL |

## 📊 Métricas Monitoreadas

### 🖥️ **Sistema:**
- **system_cpu_usage_percent** - Porcentaje de uso del procesador
- **system_memory_usage_bytes** - Uso de memoria en bytes
- **redis_connection_status** - Estado de conexión Redis (1=conectado, 0=desconectado)

### 🌐 **Backend:**
- **http_requests_total** - Total de requests HTTP por endpoint
- **http_request_duration_seconds** - Tiempo de respuesta por request
- **pii_detection_errors_total** - Errores en detección PII
- **deanonymization_failures_total** - Fallos en deanonimización

### 📈 **Redis:**
- **redis_mapping_sessions_total** - Sesiones con mappings en Redis
- **redis_mapping_entries_total** - Total de entradas de mapping
- **redis_memory_usage_bytes** - Uso de memoria de Redis

## 🔧 Dependencias e Instalación

### Dependencias Básicas (incluidas en Python):
```python
import asyncio, threading, statistics
import json, time, datetime
import argparse, typing, uuid
```

### Dependencias Externas:
```bash
# Para stress tests básicos (requerido)
pip install requests aiohttp

# Para gráficos avanzados (opcional)
pip install matplotlib
```

## 📈 Casos de Uso Recomendados

### 👨‍💻 **Desarrollo Diario**
```bash
# Ir a la carpeta utils
cd backend/utils

# Verificación rápida después de cambios
python quick_stress_test.py --threads 3 --requests 5
```

### 🧪 **Testing de Features**
```bash
# Test moderado para nuevas funcionalidades
python stress_test_backend.py --preset medium

# Verificar que las métricas siguen funcionando
python test_metricas_sistema.py
```

### 🚀 **Pre-Producción**
```bash
# Test intensivo antes de despliegue
python stress_test_backend.py --preset heavy

# Con monitoreo completo para análisis detallado
python monitor_stress_test.py
```

### 🔍 **Troubleshooting**
```bash
# Verificar métricas del sistema están disponibles
python test_metricas_sistema.py

# Monitoreo detallado para debuggear problemas de performance
python monitor_stress_test.py
```

## 📋 Interpretación de Resultados

### ✅ **Excelentes Resultados:**
- Success Rate > 95%
- Response Time < 1s promedio
- CPU < 80% durante el test
- Sin timeouts ni errores de conexión
- P95 < 2s

### ⚠️ **Resultados Moderados:**
- Success Rate 90-95%
- Response Time 1-3s promedio
- CPU 80-90%
- Algunos timeouts ocasionales
- P95 < 5s

### ❌ **Problemas Detectados:**
- Success Rate < 90%
- Response Time > 3s promedio
- CPU > 90% sostenido
- Muchos errores de conexión/timeout
- P95 > 10s

## 🎨 Archivos Generados

Los scripts generan automáticamente:

### Advanced Stress Test:
- `stress_test_results_YYYYMMDD_HHMMSS.json` - Resultados detallados con estadísticas

### Monitor Stress Test:
- `metrics_report_YYYYMMDD_HHMMSS.json` - Métricas temporales del sistema
- `metrics_chart_YYYYMMDD_HHMMSS.png` - Gráfico de performance (requiere matplotlib)

### Quick Stress Test:
- Solo resultados en consola (sin archivos)

## 🔗 Integración con Grafana

Los tests generan actividad que puedes monitorear en tiempo real:

- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:8000/metrics

### Métricas a Observar Durante Tests:
1. **HTTP Requests Rate** - Debe incrementar durante el test
2. **Response Time** - Debe mantenerse estable
3. **CPU Usage** - Monitorear picos, evitar >90%
4. **Memory Usage** - Verificar no hay memory leaks
5. **PII Detection Errors** - Debe mantenerse en 0
6. **Redis Connection** - Debe mantenerse conectado (1)

## 💡 Tips y Best Practices

### 🎯 **Para Desarrollo:**
- Ejecuta `quick_stress_test.py` después de cambios importantes
- Usa preset `light` para no sobrecargar el sistema local
- Combina con monitoreo en Grafana para ver el impacto visual
- Guarda los archivos JSON de resultados para comparar

### 🔧 **Para CI/CD:**
- Integra `stress_test_backend.py --preset light` en pipeline
- Establece umbrales: success rate > 95%, response time < 2s
- Guarda artifacts de los resultados JSON para análisis histórico
- Falla el build si hay degradación significativa

### 🚀 **Para Producción:**
- Ejecuta tests en staging idéntico a producción
- Usa preset `heavy` o `extreme` para simular carga real
- Combina con monitoreo de métricas del sistema host
- Programa tests regulares para detectar regresiones

### ⚡ **Optimización basada en Resultados:**
- **Response Time alto**: Revisar queries LLM, operaciones Redis, caching
- **CPU alto**: Optimizar algoritmos, revisar loops infinitos
- **Memory leaks**: Verificar gestión de sesiones y cleanup
- **Timeouts**: Ajustar timeouts del LLM, optimizar I/O

## 🚨 Troubleshooting Común

### Error: "Connection refused"
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health

# O usando PowerShell
Invoke-WebRequest http://localhost:8000/health
```

### Error: "ModuleNotFoundError"
```bash
# Instalar dependencias requeridas
pip install requests aiohttp

# Para gráficos (opcional)
pip install matplotlib
```

### Error: "Too many open files" (Linux/Mac)
```bash
# Aumentar límite de archivos abiertos
ulimit -n 4096
```

### Resultados inconsistentes
- Ejecutar múltiples veces y promediar resultados
- Asegurar que no hay otros procesos consumiendo recursos
- Usar el monitoreo para identificar patrones temporales
- Verificar que Redis y otros servicios estén estables

### Performance degradado
- Verificar logs del backend para errores
- Revisar uso de memoria y CPU del host
- Comprobar latencia de red si hay servicios externos
- Analizar queries lentas en base de datos

## 🎉 Ejemplo de Workflow Completo

```bash
# 1. Ir a la carpeta utils del backend
cd backend/utils

# 2. Verificación rápida del sistema
python test_metricas_sistema.py

# 3. Test rápido básico
python quick_stress_test.py --threads 3 --requests 5

# 4. Si todo OK, test más intenso
python stress_test_backend.py --preset medium

# 5. Si hay problemas, monitoreo detallado
python monitor_stress_test.py

# 6. Revisar métricas en Grafana
# Abrir http://localhost:3000

# 7. Analizar resultados JSON generados
# Ver archivos stress_test_results_*.json

# 8. Optimizar código basado en resultados

# 9. Repetir hasta obtener resultados óptimos
```

## 📚 Documentación Adicional

- **`STRESS_TESTING_README.md`** - Guía detallada de uso y configuración
- **`STRESS_TESTING_SUMMARY.md`** - Resumen de implementación y resultados

---

## 🏆 Estado Actual del Backend

Basado en las últimas pruebas realizadas:

- ✅ **Tasa de Éxito**: 100% (Excelente)
- ✅ **Estabilidad**: Todos los endpoints funcionando
- ✅ **Métricas**: Sistema de monitoreo operativo
- ⚠️ **Performance**: Response time 15-20s (área de mejora)

**Próximos pasos**: Optimización de response times y implementación de caching.

¡Las herramientas están listas para mantener tu backend en óptimas condiciones! 🚀