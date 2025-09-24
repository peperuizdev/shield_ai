import requests
import json
import asyncio
import aiohttp
from typing import Dict

class ShieldAITestClient:
    """
    Cliente de prueba para la API de desanonimización de Shield AI
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def setup_dummy_session(self, session_id: str) -> Dict:
        """
        Configura una sesión dummy con datos de prueba
        """
        response = requests.post(f"{self.base_url}/sessions/{session_id}/setup-dummy")
        return response.json()
    
    def deanonymize_text(self, session_id: str, model_response: str) -> Dict:
        """
        Desanonimiza un texto completo
        """
        payload = {
            "session_id": session_id,
            "model_response": model_response
        }
        response = requests.post(f"{self.base_url}/deanonymize/", json=payload)
        return response.json()
    
    async def test_streaming_deanonymization(self, session_id: str):
        """
        Prueba la desanonimización en streaming
        """
        url = f"{self.base_url}/deanonymize/stream"
        payload = {"session_id": session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print("=== RESPUESTA STREAMING ===")
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data = json.loads(line_str[6:])  # Remover 'data: '
                            if 'chunk' in data:
                                print(data['chunk'], end='', flush=True)
                            elif 'status' in data:
                                print(f"\n[{data['status']}]")
    
    async def test_dual_streaming(self, session_id: str):
        """
        Prueba el streaming dual (anonimizado y desanonimizado simultáneo)
        """
        url = f"{self.base_url}/deanonymize/stream-dual"
        payload = {"session_id": session_id}
        
        anonymous_text = ""
        deanonymized_text = ""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print("=== STREAMING DUAL ===")
                print("📊 Monitoreando streams...")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remover 'data: '
                                
                                if data.get('type') == 'anonymous':
                                    anonymous_text += data.get('chunk', '')
                                elif data.get('type') == 'deanonymized':
                                    deanonymized_text += data.get('chunk', '')
                                elif data.get('type') == 'status' and data.get('status') == 'complete':
                                    print("\n\n✅ Streaming completado!")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"❌ Error parsing JSON: {e}")
                
                print("\n📝 RESULTADO FINAL:")
                print("\n🎭 TEXTO ANONIMIZADO:")
                print(anonymous_text)
                print("\n🔓 TEXTO DESANONIMIZADO:")
                print(deanonymized_text)
    
    def test_full_process(self, session_id: str) -> Dict:
        """
        Prueba el proceso completo de desanonimización
        """
        response = requests.get(f"{self.base_url}/deanonymize/test/{session_id}")
        return response.json()
    
    def get_session_status(self, session_id: str) -> Dict:
        """
        Obtiene el estado de una sesión
        """
        response = requests.get(f"{self.base_url}/sessions/{session_id}/status")
        return response.json()
    
    def list_active_sessions(self) -> Dict:
        """
        Lista todas las sesiones activas
        """
        response = requests.get(f"{self.base_url}/sessions/")
        return response.json()
    
    def create_custom_session(self, session_id: str, anonymization_map: Dict[str, str], ttl: int = 3600) -> Dict:
        """
        Crea una sesión personalizada con un mapa de anonimización específico
        """
        payload = {
            "session_id": session_id,
            "anonymization_map": anonymization_map,
            "ttl": ttl
        }
        response = requests.post(f"{self.base_url}/sessions/", json=payload)
        return response.json()
    
    def delete_session(self, session_id: str) -> Dict:
        """
        Elimina una sesión
        """
        response = requests.delete(f"{self.base_url}/sessions/{session_id}")
        return response.json()

# === EJEMPLOS DE USO ===

async def main():
    client = ShieldAITestClient()
    session_id = "test_session_001"
    
    print("🛡️ SHIELD AI - TEST DE DESANONIMIZACIÓN")
    print("=" * 50)
    
    # 1. Configurar sesión dummy
    print("\n1. Configurando sesión dummy...")
    setup_result = client.setup_dummy_session(session_id)
    print(f"✅ {setup_result['message']}")
    
    # 2. Verificar estado de sesión
    print("\n2. Verificando estado de sesión...")
    status = client.get_session_status(session_id)
    print(f"📊 Sesión existe: {status['exists']}")
    print(f"⏰ Expira en: {status['expires_in']}")
    
    # 3. Probar desanonimización de texto completo
    print("\n3. Probando desanonimización de texto completo...")
    test_text = """Estimada María González, desde Barcelona le confirmamos que su solicitud ha sido procesada. 
    Datos registrados: email maria.gonzalez@email.com, teléfono 687654321, 
    dirección Avenida Libertad 456, Barcelona 08001."""
    
    result = client.deanonymize_text(session_id, test_text)
    print("\n📝 TEXTO ORIGINAL (anonimizado):")
    print(result['original_response'])
    print("\n🔓 TEXTO DESANONIMIZADO:")
    print(result['deanonymized_response'])
    print(f"\n📈 Reemplazos realizados: {result['replacements_made']}")
    
    # 4. Probar streaming simple
    print("\n4. Probando desanonimización en streaming...")
    await client.test_streaming_deanonymization(session_id)
    
    # 5. Probar streaming dual (¡NUEVO!)
    print("\n5. Probando streaming dual (anonimizado + desanonimizado)...")
    await client.test_dual_streaming(session_id)
    
    # 6. Probar proceso completo
    print("\n\n6. Probando proceso completo...")
    full_test = client.test_full_process(session_id)
    print("\n📋 MAPA DE ANONIMIZACIÓN:")
    for orig, fake in full_test['step_1_anonymization_map'].items():
        print(f"   {orig} → {fake}")
    
    print("\n📝 RESPUESTA DEL MODELO (anonimizada):")
    print(full_test['step_2_anonymized_response'])
    
    print("\n🔓 RESPUESTA FINAL (desanonimizada):")
    print(full_test['step_3_deanonymized_response'])

def test_synchronous_examples():
    """
    Ejemplos síncronos para pruebas rápidas
    """
    client = ShieldAITestClient()
    session_id = "sync_test_001"
    
    print("\n🔧 PRUEBAS SÍNCRONAS")
    print("=" * 30)
    
    # Listar sesiones activas antes
    print("\n📋 Sesiones activas antes:")
    sessions = client.list_active_sessions()
    print(f"Total: {sessions['total_sessions']}")
    
    # Configurar sesión
    client.setup_dummy_session(session_id)
    
    # Casos de prueba
    test_cases = [
        "Hola María González, tu email maria.gonzalez@email.com está registrado.",
        "El Sr. María González de Barcelona puede contactar al 687654321.",
        "Cuenta IBAN: ES76 0182 6473 8901 2345 6789 del Banco BBVA.",
        "Dirección: Avenida Libertad 456, Barcelona, CP: 08001"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- CASO {i} ---")
        result = client.deanonymize_text(session_id, test_case)
        print(f"Anonimizado: {result['original_response']}")
        print(f"Desanonimizado: {result['deanonymized_response']}")
        print(f"Reemplazos: {result['replacements_made']}")
    
    # Probar sesión personalizada
    print("\n🛠️ SESIÓN PERSONALIZADA")
    custom_map = {
        "Cliente Secreto": "Cliente VIP",
        "proyecto-ultra-secreto": "proyecto-alfa",
        "codigo123": "codigo999"
    }
    
    custom_session = "custom_test_001" 
    client.create_custom_session(custom_session, custom_map)
    
    custom_text = "Estimado Cliente Secreto, el proyecto-ultra-secreto con codigo123 está listo."
    result = client.deanonymize_text(custom_session, custom_text)
    print(f"Original: {result['original_response']}")
    print(f"Desanonimizado: {result['deanonymized_response']}")
    
    # Limpiar sesiones de prueba
    print(f"\n🧹 Limpiando sesiones...")
    client.delete_session(session_id)
    client.delete_session(custom_session)

if __name__ == "__main__":
    print("Selecciona el tipo de prueba:")
    print("1. Prueba completa (con streaming) - async")
    print("2. Pruebas síncronas rápidas")
    
    choice = input("Opción (1/2): ").strip()
    
    if choice == "1":
        asyncio.run(main())
    else:
        test_synchronous_examples()