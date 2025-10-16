"""
Test de aislamiento de sesiones para Shield AI

Verifica que los mapas de anonimización no se mezclen entre diferentes sesiones
usando el endpoint de streaming y Redis real del sistema.
"""

import pytest
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

BASE_URL = "http://localhost:8000"

class TestIsolation:
    """Test para verificar aislamiento de sesiones"""
    
    def test_session_isolation_with_streaming(self):
        """
        Test principal: Verifica que 3 sesiones simultáneas no mezclen sus mapas
        """
        print(f"\n🔐 TEST DE AISLAMIENTO DE SESIONES")
        print("=" * 50)
        
        # Datos únicos para cada sesión
        sessions_data = [
            {
                "session_id": "test_alice_001",
                "message": "Soy Alice Smith de alice@company.com, teléfono +34 600 111 222",
                "expected_name": "Alice Smith",
                "expected_email": "alice@company.com", 
                "expected_phone": "+34 600 111 222"
            },
            {
                "session_id": "test_bob_002", 
                "message": "Soy Bob Johnson de bob@business.org, teléfono +34 600 333 444",
                "expected_name": "Bob Johnson",
                "expected_email": "bob@business.org",
                "expected_phone": "+34 600 333 444"
            },
            {
                "session_id": "test_carol_003",
                "message": "Soy Carol Davis de carol@startup.net, teléfono +34 600 555 666", 
                "expected_name": "Carol Davis",
                "expected_email": "carol@startup.net",
                "expected_phone": "+34 600 555 666"
            }
        ]
        
        print(f"✅ Configurados {len(sessions_data)} casos de prueba únicos")
        
        # Ejecutar sesiones simultáneamente
        results = self._run_concurrent_sessions(sessions_data)
        
        # Verificar que no hay contaminación cruzada
        violations = self._check_for_cross_contamination(results, sessions_data)
        
        # Verificar mapas individuales
        mapping_violations = self._verify_individual_mappings(sessions_data)
        
        # Resultados
        print(f"\n📊 RESULTADOS:")
        print(f"  ✅ Sesiones exitosas: {len([r for r in results if r['success']])}")
        print(f"  ❌ Sesiones fallidas: {len([r for r in results if not r['success']])}")
        print(f"  🔍 Violaciones de contenido: {len(violations)}")
        print(f"  🗺️ Violaciones de mapping: {len(mapping_violations)}")
        
        # Mostrar violaciones si las hay
        if violations:
            print(f"\n❌ VIOLACIONES DE AISLAMIENTO:")
            for violation in violations[:3]:
                print(f"  - {violation}")
        
        if mapping_violations:
            print(f"\n❌ PROBLEMAS EN MAPPINGS:")
            for violation in mapping_violations[:3]:
                print(f"  - {violation}")
        
        # Assertions
        assert len([r for r in results if r['success']]) >= 2, "Muy pocas sesiones exitosas"
        assert len(violations) == 0, f"Violaciones de aislamiento: {violations}"
        assert len(mapping_violations) == 0, f"Violaciones de mapping: {mapping_violations}"
        
        print(f"\n🎉 TEST EXITOSO: Aislamiento verificado correctamente")
    
    def _run_concurrent_sessions(self, sessions_data: List[Dict]) -> List[Dict]:
        """Ejecuta las sesiones de forma concurrente"""
        print(f"\n🚀 Ejecutando {len(sessions_data)} sesiones simultáneas...")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Enviar todas las sesiones al mismo tiempo
            future_to_session = {
                executor.submit(self._send_streaming_request, session): session['session_id']
                for session in sessions_data
            }
            
            # Recoger resultados
            for future in as_completed(future_to_session):
                session_id = future_to_session[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result['success'] else "❌"
                    print(f"  {status} {session_id}: {result.get('status', 'unknown')}")
                except Exception as e:
                    print(f"  ❌ {session_id}: Error - {e}")
                    results.append({'session_id': session_id, 'success': False, 'error': str(e)})
        
        return results
    
    def _send_streaming_request(self, session_data: Dict) -> Dict:
        """Envía una petición de streaming para una sesión"""
        try:
            payload = {
                'message': session_data['message'],
                'session_id': session_data['session_id'],
                'save_mapping': True,
                'use_realistic_fake': True
            }
            
            response = requests.post(
                f"{BASE_URL}/chat/streaming",
                data=payload,
                timeout=30,
                stream=True
            )
            
            if response.status_code != 200:
                return {
                    'session_id': session_data['session_id'],
                    'success': False,
                    'status': f"HTTP {response.status_code}",
                    'response_text': ""
                }
            
            # Procesar streaming y recoger texto completo
            deanonymized_text = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'deanonymized':
                                deanonymized_text += data.get('chunk', '')
                        except json.JSONDecodeError:
                            continue
            
            return {
                'session_id': session_data['session_id'],
                'success': True,
                'status': 'completed',
                'response_text': deanonymized_text,
                'original_data': session_data
            }
            
        except Exception as e:
            return {
                'session_id': session_data['session_id'],
                'success': False,
                'status': 'error',
                'error': str(e),
                'response_text': ""
            }
    
    def _check_for_cross_contamination(self, results: List[Dict], sessions_data: List[Dict]) -> List[str]:
        """Verifica que no hay contaminación cruzada entre respuestas"""
        violations = []
        
        # Crear mapping de datos esperados por sesión
        session_expected = {s['session_id']: s for s in sessions_data}
        
        for result_a in results:
            if not result_a['success']:
                continue
                
            session_a_id = result_a['session_id']
            response_a = result_a['response_text']
            
            # Verificar que esta respuesta no contiene datos de otras sesiones
            for result_b in results:
                if result_a['session_id'] == result_b['session_id'] or not result_b['success']:
                    continue
                
                session_b_id = result_b['session_id']
                expected_b = session_expected[session_b_id]
                
                # Buscar datos de sesión B en respuesta de sesión A
                if expected_b['expected_name'] in response_a:
                    violations.append(f"Nombre '{expected_b['expected_name']}' de {session_b_id} encontrado en {session_a_id}")
                
                if expected_b['expected_email'] in response_a:
                    violations.append(f"Email '{expected_b['expected_email']}' de {session_b_id} encontrado en {session_a_id}")
                
                if expected_b['expected_phone'] in response_a:
                    violations.append(f"Teléfono '{expected_b['expected_phone']}' de {session_b_id} encontrado en {session_a_id}")
        
        return violations
    
    def _verify_individual_mappings(self, sessions_data: List[Dict]) -> List[str]:
        """Verifica que cada sesión tiene su propio mapping aislado"""
        mapping_violations = []
        
        for session in sessions_data:
            session_id = session['session_id']
            
            try:
                # Obtener mapping de esta sesión
                response = requests.get(f"{BASE_URL}/debug/session/{session_id}/mapping", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    mapping = data.get('mapping', {})
                    
                    if not mapping:
                        mapping_violations.append(f"Sesión {session_id}: mapping vacío")
                        continue
                    
                    # Verificar que contiene datos esperados de ESTA sesión
                    session_data_found = False
                    for fake_value, real_value in mapping.items():
                        if (session['expected_name'] in real_value or 
                            session['expected_email'] in real_value or
                            session['expected_phone'] in real_value):
                            session_data_found = True
                            break
                    
                    if not session_data_found:
                        mapping_violations.append(f"Sesión {session_id}: no contiene sus datos esperados")
                    
                    # Verificar que NO contiene datos de otras sesiones  
                    for other_session in sessions_data:
                        if other_session['session_id'] == session_id:
                            continue
                        
                        for fake_value, real_value in mapping.items():
                            if (other_session['expected_name'] in real_value or
                                other_session['expected_email'] in real_value or  
                                other_session['expected_phone'] in real_value):
                                mapping_violations.append(
                                    f"Sesión {session_id}: contiene datos de {other_session['session_id']}"
                                )
                
                else:
                    mapping_violations.append(f"Sesión {session_id}: error obteniendo mapping (HTTP {response.status_code})")
                    
            except Exception as e:
                mapping_violations.append(f"Sesión {session_id}: error verificando mapping - {e}")
        
        return mapping_violations
    
    def test_health_check(self):
        """Verificar que el backend está funcionando"""
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200, "Backend no disponible"
        print("✅ Health check passed")


# Para ejecutar directamente
if __name__ == "__main__":
    test = SimpleIsolationTest()
    
    try:
        print("🏥 Verificando salud del backend...")
        test.test_health_check()
        
        print("\n🧪 Ejecutando test de aislamiento...")
        test.test_session_isolation_with_streaming()
        
        print("\n🎊 TODOS LOS TESTS EXITOSOS")
        
    except AssertionError as e:
        print(f"\n💥 TEST FALLÓ: {e}")
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")