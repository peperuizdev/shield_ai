#!/usr/bin/env python3
"""
Test Script para verificar el arreglo del bug de anonimización
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"
SESSION_ID = "test_bug_fix"

def test_anonymization_consistency():
    """
    Prueba que la anonimización sea consistente entre ejecuciones
    """
    print("🧪 Iniciando test de consistencia de anonimización...")
    
    # Test 1: Primera ejecución
    print("\n1️⃣ Primera ejecución - debería crear nuevo mapa")
    
    payload1 = {
        "message": "Hola Juan Pérez de Madrid, necesito información",
        "session_id": SESSION_ID,
        "save_mapping": True,
        "use_realistic_fake": True
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/chat/streaming", 
                                 json=payload1,
                                 headers={"Content-Type": "application/json"},
                                 stream=True)
        
        print(f"✅ Status: {response1.status_code}")
        
        # Leer los primeros eventos del stream
        count = 0
        llm_data = ""
        user_data = ""
        
        for line in response1.iter_lines():
            if line and count < 10:  # Leer solo los primeros eventos
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get('type') == 'anonymous':
                            llm_data += data.get('chunk', '')
                        elif data.get('type') == 'deanonymized':
                            user_data += data.get('chunk', '')
                    except json.JSONDecodeError:
                        pass
                count += 1
        
        print(f"📤 LLM recibió: '{llm_data[:50]}...'")
        print(f"👤 Usuario ve: '{user_data[:50]}...'")
        
        response1.close()
        
    except Exception as e:
        print(f"❌ Error en primera ejecución: {e}")
        return False
    
    # Esperar un momento
    time.sleep(2)
    
    # Test 2: Segunda ejecución - DEBE usar el mismo mapa
    print("\n2️⃣ Segunda ejecución - debería usar mapa existente")
    
    payload2 = {
        "message": "Juan Pérez quiere saber más detalles de Madrid",
        "session_id": SESSION_ID,  # MISMA SESIÓN
        "save_mapping": True,
        "use_realistic_fake": True
    }
    
    try:
        response2 = requests.post(f"{BASE_URL}/chat/streaming", 
                                 json=payload2,
                                 headers={"Content-Type": "application/json"},
                                 stream=True)
        
        print(f"✅ Status: {response2.status_code}")
        
        # Leer los primeros eventos del stream
        count = 0
        llm_data2 = ""
        user_data2 = ""
        
        for line in response2.iter_lines():
            if line and count < 10:  # Leer solo los primeros eventos
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get('type') == 'anonymous':
                            llm_data2 += data.get('chunk', '')
                        elif data.get('type') == 'deanonymized':
                            user_data2 += data.get('chunk', '')
                    except json.JSONDecodeError:
                        pass
                count += 1
        
        print(f"📤 LLM recibió: '{llm_data2[:50]}...'")
        print(f"👤 Usuario ve: '{user_data2[:50]}...'")
        
        response2.close()
        
    except Exception as e:
        print(f"❌ Error en segunda ejecución: {e}")
        return False
    
    # Verificación
    print("\n🔍 VERIFICACIÓN:")
    
    if "Juan Pérez" in llm_data2:
        print("❌ BUG DETECTADO: El LLM recibió datos REALES en la segunda ejecución")
        print(f"   LLM vio: '{llm_data2[:100]}'")
        return False
    else:
        print("✅ ARREGLADO: El LLM recibió datos ANONIMIZADOS en ambas ejecuciones")
        print(f"   Primera: '{llm_data[:50]}...'")
        print(f"   Segunda: '{llm_data2[:50]}...'")
        return True

def test_session_isolation():
    """
    Prueba que diferentes sesiones no se mezclen
    """
    print("\n🔐 Test de aislamiento de sesiones...")
    
    session1 = f"session_a_{int(time.time())}"
    session2 = f"session_b_{int(time.time())}"
    
    # Sesión A
    payload_a = {
        "message": "Hola Ana López",
        "session_id": session1,
        "save_mapping": True
    }
    
    # Sesión B  
    payload_b = {
        "message": "Hola Carlos Ruiz", 
        "session_id": session2,
        "save_mapping": True
    }
    
    try:
        # Test sesión A
        resp_a = requests.post(f"{BASE_URL}/chat/streaming", json=payload_a, stream=True)
        resp_a.close()
        
        # Test sesión B
        resp_b = requests.post(f"{BASE_URL}/chat/streaming", json=payload_b, stream=True)
        resp_b.close()
        
        print("✅ Sesiones aisladas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en test de aislamiento: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Shield AI - Test de Arreglo de Bug de Anonimización")
    print("=" * 60)
    
    # Verificar que el servidor esté funcionando
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Servidor funcionando")
        else:
            print("❌ Servidor no responde correctamente")
            exit(1)
    except:
        print("❌ No se puede conectar al servidor en localhost:8000")
        print("   Asegúrate de que el servidor esté ejecutándose")
        exit(1)
    
    # Ejecutar tests
    test1_passed = test_anonymization_consistency()
    test2_passed = test_session_isolation()
    
    print("\n" + "=" * 60)
    print("📋 RESULTADOS FINALES:")
    print(f"   Test Consistencia: {'✅ PASÓ' if test1_passed else '❌ FALLÓ'}")
    print(f"   Test Aislamiento: {'✅ PASÓ' if test2_passed else '❌ FALLÓ'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ¡TODOS LOS TESTS PASARON! El bug está arreglado.")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisar la implementación.")