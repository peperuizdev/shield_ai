# Guía Rápida: Importar Dashboard de Shield AI en Grafana

## 🚀 Pasos para Importar el Dashboard

### 1. Acceder a Grafana
- URL: http://localhost:3000
- Usuario: `admin`
- Contraseña: `admin123`

### 2. Importar Dashboard Manualmente

1. **Ir a Dashboards**
   - Click en el menú hamburguesa (☰) en la esquina superior izquierda
   - Seleccionar "Dashboards"

2. **Crear Nuevo Dashboard**
   - Click en "New" → "Import"
   - O ir directamente a: http://localhost:3000/dashboard/import

3. **Importar JSON**
   - Copiar el contenido del archivo `dashboards/shield-ai-dashboard.json`
   - Pegarlo en el campo "Import via panel json"
   - Click en "Load"

4. **Configurar Dashboard**
   - Asegurarse de que el datasource sea "Prometheus"
   - Click en "Import"

### 3. Configurar Datasource (si no está configurado)

1. **Ir a Configuration**
   - Click en el ícono de engranaje (⚙️) en el menú lateral
   - Seleccionar "Data Sources"

2. **Añadir Prometheus**
   - Click en "Add data source"
   - Seleccionar "Prometheus"
   - URL: `http://prometheus:9090`
   - Click en "Save & Test"

### 4. Verificar Métricas

Puedes probar estas queries en Explore (http://localhost:3000/explore):

```promql
# Métricas del sistema
up
node_cpu_seconds_total
node_memory_MemTotal_bytes

# Métricas de la aplicación (si el backend está ejecutándose)
http_requests_total
pii_detection_total
```

### 5. Dashboard Automático (Alternativa)

Si prefieres un dashboard con visualizaciones más avanzadas, puedes importar dashboards de la comunidad:

1. **Dashboard de Node Exporter**
   - ID: `1860` (Node Exporter Full)
   - URL: https://grafana.com/grafana/dashboards/1860

2. **Dashboard de Prometheus**
   - ID: `3662` (Prometheus 2.0 Overview)

## 🔧 Solución de Problemas

### Dashboard no muestra datos
1. Verificar que Prometheus esté funcionando: http://localhost:9090
2. Verificar targets en Prometheus: http://localhost:9090/targets
3. Comprobar que el datasource esté configurado correctamente

### Métricas del backend no aparecen
1. Verificar que el backend esté ejecutándose en puerto 8000
2. Verificar métricas del backend: http://localhost:8000/metrics
3. Comprobar configuración de Prometheus en `config/prometheus.yml`

### Errores de conexión
```bash
# Verificar que todos los servicios estén funcionando
docker-compose ps

# Ver logs de Grafana
docker-compose logs grafana

# Reiniciar servicios si es necesario
docker-compose restart grafana
```

## 📊 Métricas Principales

Una vez importado, el dashboard mostrará:

- **CPU Usage**: Uso de CPU del sistema
- **Memory Usage**: Uso de memoria del sistema  
- **HTTP Requests Rate**: Tasa de requests HTTP por minuto
- **Response Time**: Tiempo promedio de respuesta

## 🔄 Próximos Pasos

1. Personalizar el dashboard según tus necesidades
2. Añadir más paneles para métricas específicas de PII
3. Configurar alertas directamente en Grafana
4. Explorar métricas en la sección "Explore"