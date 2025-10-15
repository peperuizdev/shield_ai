#!/usr/bin/env python3
"""
DASHBOARD SIMPLE DE MÉTRICAS - Monitor en tiempo real

Dashboard básico para ver las métricas de Redis mappings en tiempo real.
"""

import requests
import json
import time
import os
from datetime import datetime

def clear_screen():
    """Limpiar pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_metrics(base_url="http://localhost:8000"):
    """Obtener métricas del servidor"""
    try:
        response = requests.get(f"{base_url}/metrics/redis", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def format_bytes(bytes_value):
    """Formatear bytes en unidades legibles"""
    if bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    
    while bytes_value >= 1024 and unit_index < len(units) - 1:
        bytes_value /= 1024
        unit_index += 1
    
    return f"{bytes_value:.2f} {units[unit_index]}"

def display_dashboard(metrics_data):
    """Mostrar dashboard"""
    clear_screen()
    
    print("📊 " + "="*80 + " 📊")
    print("📊" + " "*25 + "SHIELD AI - REDIS METRICS" + " "*25 + "📊")
    print("📊 " + "="*80 + " 📊")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 Última actualización: {timestamp}")
    
    if "error" in metrics_data:
        print(f"\n❌ Error obteniendo métricas: {metrics_data['error']}")
        print(f"💡 Asegúrate de que el servidor esté ejecutándose:")
        print(f"   cd backend && uvicorn app.main:app --reload")
        return
    
    # Conexión Redis
    print(f"\n🔗 ESTADO DE REDIS")
    print("=" * 80)
    
    redis_conn = metrics_data.get('redis_connection', {})
    connection_status = redis_conn.get('status', 'unknown')
    
    if connection_status == 'connected':
        print(f"✅ Estado: Conectado")
        print(f"📡 Host: {redis_conn.get('host', 'N/A')}:{redis_conn.get('port', 'N/A')}")
        print(f"🗄️  Base de datos: {redis_conn.get('db', 'N/A')}")
    else:
        print(f"❌ Estado: Desconectado")
        print(f"⚠️  Error: {redis_conn.get('error', 'Error desconocido')}")
    
    # Métricas de mappings
    print(f"\n📊 MÉTRICAS DE MAPPINGS")
    print("=" * 80)
    
    mapping_sessions = metrics_data.get('mapping_sessions', {})
    total_sessions = mapping_sessions.get('total_sessions', 0)
    total_entries = mapping_sessions.get('total_mapping_entries', 0)
    avg_per_session = mapping_sessions.get('avg_mappings_per_session', 0)
    
    print(f"📦 Sesiones totales: {total_sessions:,}")
    print(f"🔢 Mappings totales: {total_entries:,}")
    print(f"📈 Promedio por sesión: {avg_per_session:.2f}")
    
    if total_sessions > 0:
        print(f"💡 Eficiencia: {(total_entries/total_sessions):.1f} mappings por sesión")
    
    # Memoria Redis
    print(f"\n💾 USO DE MEMORIA")
    print("=" * 80)
    
    redis_memory = metrics_data.get('redis_memory', {})
    used_memory = redis_memory.get('used_memory_bytes', 0)
    max_memory = redis_memory.get('max_memory_bytes', 0)
    
    print(f"📊 Memoria utilizada: {format_bytes(used_memory)}")
    
    if max_memory > 0:
        memory_percent = (used_memory / max_memory) * 100
        print(f"📈 Memoria máxima: {format_bytes(max_memory)}")
        print(f"🎯 Uso: {memory_percent:.1f}%")
        
        # Barra de progreso visual
        bar_length = 50
        filled_length = int(bar_length * memory_percent / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"📊 [{bar}] {memory_percent:.1f}%")
    else:
        print(f"♾️  Memoria máxima: Ilimitada")
    
    # Detalles de sesiones
    if 'session_details' in metrics_data:
        print(f"\n📋 DETALLES DE SESIONES")
        print("=" * 80)
        
        session_details = metrics_data['session_details']
        recent_sessions = session_details.get('recent_sessions', [])
        
        if recent_sessions:
            print(f"🕐 Sesiones recientes:")
            for i, session in enumerate(recent_sessions[:5]):  # Mostrar solo las 5 más recientes
                session_id = session.get('session_id', 'N/A')
                mapping_count = session.get('mapping_count', 0)
                # Truncar session_id si es muy largo
                if len(session_id) > 40:
                    session_id = session_id[:37] + "..."
                print(f"   {i+1}. {session_id} ({mapping_count} mappings)")
        else:
            print(f"📝 No hay sesiones disponibles")
    
    # Instrucciones
    print(f"\n💡 CONTROLES")
    print("=" * 80)
    print(f"🔄 Presiona Ctrl+C para salir")
    print(f"⏰ Actualización automática cada 5 segundos")

def main():
    """Función principal del dashboard"""
    print("🚀 Iniciando dashboard de métricas...")
    print("💡 Presiona Ctrl+C para salir")
    
    base_url = "http://localhost:8000"
    
    try:
        while True:
            metrics = get_metrics(base_url)
            display_dashboard(metrics)
            time.sleep(5)  # Actualizar cada 5 segundos
    
    except KeyboardInterrupt:
        clear_screen()
        print("👋 Dashboard cerrado")
        print("📊 Gracias por usar Shield AI Metrics Dashboard")

if __name__ == "__main__":
    main()