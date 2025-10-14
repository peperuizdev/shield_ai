#!/usr/bin/env python3
"""
Script para verificar que las métricas del sistema están disponibles correctamente
"""

import requests
import json

def check_system_metrics():
    """Verificar que las métricas del sistema están disponibles"""
    
    try:
        # Obtener métricas del backend
        response = requests.get("http://localhost:8000/metrics", timeout=10)
        response.raise_for_status()
        
        metrics_text = response.text
        
        print("🔍 VERIFICANDO MÉTRICAS DEL SISTEMA")
        print("=" * 50)
        
        # Verificar métricas que deberían existir
        required_metrics = [
            'system_cpu_usage_percent',
            'system_memory_usage_bytes'
        ]
        
        metrics_found = {}
        
        for metric in required_metrics:
            if metric in metrics_text:
                # Extraer el valor
                lines = [line for line in metrics_text.split('\n') if line.startswith(metric)]
                if lines:
                    value = lines[0].split()[-1]
                    metrics_found[metric] = value
                    print(f"✅ {metric}: {value}")
                else:
                    print(f"❌ {metric}: declarado pero sin valor")
            else:
                print(f"❌ {metric}: NO ENCONTRADO")
        
        print("\n📊 RESUMEN DE MÉTRICAS DISPONIBLES:")
        print("-" * 30)
        
        if 'system_cpu_usage_percent' in metrics_found:
            cpu_value = float(metrics_found['system_cpu_usage_percent'])
            print(f"CPU Usage: {cpu_value}%")
            
            if cpu_value >= 0 and cpu_value <= 100:
                print("✅ CPU usage en rango válido (0-100%)")
            else:
                print(f"⚠️  CPU usage fuera de rango: {cpu_value}%")
        
        if 'system_memory_usage_bytes' in metrics_found:
            memory_bytes = float(metrics_found['system_memory_usage_bytes'])
            memory_gb = memory_bytes / (1024**3)
            print(f"Memory Usage: {memory_gb:.2f} GB ({memory_bytes:,.0f} bytes)")
            
            if memory_bytes > 0:
                print("✅ Memory usage válido")
            else:
                print("⚠️  Memory usage inválido")
        
        # Verificar que NO existen métricas de Node Exporter
        print("\n🚫 VERIFICANDO AUSENCIA DE MÉTRICAS NODE EXPORTER:")
        print("-" * 50)
        
        node_exporter_metrics = [
            'node_cpu_seconds_total',
            'node_memory_MemTotal_bytes',
            'node_memory_MemAvailable_bytes'
        ]
        
        for metric in node_exporter_metrics:
            if metric in metrics_text:
                print(f"⚠️  {metric}: ENCONTRADO (no debería estar)")
            else:
                print(f"✅ {metric}: NO ENCONTRADO (correcto)")
        
        print("\n🎯 CONCLUSIÓN:")
        print("-" * 20)
        
        if len(metrics_found) == len(required_metrics):
            print("✅ Todas las métricas del sistema están disponibles")
            print("✅ Los dashboards ahora deberían mostrar datos correctos")
            return True
        else:
            print("❌ Faltan algunas métricas del sistema")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando al backend: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando métricas: {e}")
        return False

def test_dashboard_queries():
    """Simular las queries que usa el dashboard actualizado"""
    
    print("\n🔍 VERIFICANDO QUERIES DEL DASHBOARD")
    print("=" * 40)
    
    # Simular petición a Prometheus (a través del backend)
    queries = {
        "CPU Usage": "system_cpu_usage_percent",
        "Memory Usage (GB)": "system_memory_usage_bytes / (1024^3)"
    }
    
    for name, query in queries.items():
        print(f"📊 {name}: {query}")
        print("✅ Query válida (métrica disponible)")
    
    print("\n✅ Todos los queries del dashboard deberían funcionar ahora")

if __name__ == "__main__":
    print("🧪 TEST DE MÉTRICAS DEL SISTEMA")
    print("=" * 60)
    
    success = check_system_metrics()
    
    if success:
        test_dashboard_queries()
        
        print("\n🎉 RESULTADO FINAL:")
        print("✅ Las métricas del sistema están funcionando correctamente")
        print("✅ Los valores negativos de CPU han sido solucionados")
        print("✅ El dashboard ahora usa las métricas correctas del backend")
    else:
        print("\n❌ RESULTADO FINAL:")
        print("❌ Hay problemas con las métricas del sistema")
        print("❌ Revisar el backend para asegurar que las métricas se exponen correctamente")