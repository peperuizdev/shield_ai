import os
import requests
import json
from dotenv import load_dotenv

# Cargar .env
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

def test_groq_api_direct():
    """Test directo de la API de Groq para diagnosticar el problema"""
    
    print("🔧 TEST DIRECTO DE API GROQ")
    print("=" * 50)
    
    # Obtener API key
    api_key = os.getenv("GROK_API_KEY")
    
    if not api_key:
        print("❌ No se encontró GROK_API_KEY")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:15]}...{api_key[-4:]}")
    
    # Test 1: Listar modelos disponibles
    print("\n🔍 Test 1: Verificando modelos disponibles")
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        models_response = requests.get(
            "https://api.groq.com/openai/v1/models", 
            headers=headers,
            timeout=10
        )
        
        print(f"Status modelos: {models_response.status_code}")
        
        if models_response.status_code == 200:
            models = models_response.json()
            available_models = [model['id'] for model in models.get('data', [])]
            print(f"✅ Modelos disponibles: {available_models}")
        else:
            print(f"❌ Error obteniendo modelos: {models_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en request de modelos: {e}")
        return False
    
    # Test 2: Hacer una petición simple con diferentes modelos
    test_models = ["llama3-8b-8192", "mixtral-8x7b-32768", "gemma-7b-it"]
    
    for model in test_models:
        print(f"\n🧪 Test 2: Probando modelo {model}")
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Hola, responde solo con 'Test exitoso'"
                }
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"✅ Respuesta exitosa: {message}")
                return True
            else:
                print(f"❌ Error {response.status_code}:")
                try:
                    error_detail = response.json()
                    print(f"   Detalle: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"   Texto: {response.text}")
                    
        except Exception as e:
            print(f"❌ Excepción: {e}")
    
    print("\n❌ Todos los tests fallaron")
    return False

def test_api_key_format():
    """Verificar formato de la API key"""
    print("\n🔑 VERIFICACIÓN DE API KEY")
    print("-" * 30)
    
    api_key = os.getenv("GROK_API_KEY")
    
    if not api_key:
        print("❌ API key no encontrada")
        return False
    
    print(f"Longitud: {len(api_key)} caracteres")
    print(f"Primeros 10: {api_key[:10]}")
    print(f"Últimos 4: {api_key[-4:]}")
    
    # Verificar formato típico de Groq (suelen empezar con gsk_)
    if api_key.startswith('gsk_'):
        print("✅ Formato parece correcto (empieza con gsk_)")
    else:
        print("⚠️  Formato inusual (no empieza con gsk_)")
        print("   ¿Estás seguro que es una API key de Groq?")
    
    # Verificar caracteres válidos
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
    invalid_chars = set(api_key) - valid_chars
    
    if invalid_chars:
        print(f"⚠️  Caracteres inválidos encontrados: {invalid_chars}")
    else:
        print("✅ Caracteres válidos")
    
    return True

if __name__ == "__main__":
    print("🚀 DIAGNÓSTICO COMPLETO DE GROQ API")
    print("=" * 60)
    
    # Test 1: Verificar formato de API key
    test_api_key_format()
    
    # Test 2: Test directo de API
    success = test_groq_api_direct()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡API de Groq funciona correctamente!")
        print("El problema debe estar en el código del pipeline.")
    else:
        print("🔧 POSIBLES SOLUCIONES:")
        print("1. Verificar que la API key sea correcta y válida")
        print("2. Verificar que tengas créditos en tu cuenta Groq") 
        print("3. Verificar que la API key tenga permisos suficientes")
        print("4. Probar generar una nueva API key en https://console.groq.com")
        print("5. Verificar que no hay espacios extra en el .env")