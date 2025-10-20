import requests
import time

BASE_URL = "http://localhost:8000"

def test_session_isolation():
    session_a = f"session_a_{int(time.time())}"
    session_b = f"session_b_{int(time.time())}"

    payload_a = {
        "message": "Hola Ana López, vivo en Madrid.",
        "session_id": session_a,
        "save_mapping": True
    }
    payload_b = {
        "message": "Hola Carlos Ruiz, trabajo en Barcelona.",
        "session_id": session_b,
        "save_mapping": True
    }

    resp_a = requests.post(f"{BASE_URL}/chat/streaming", data=payload_a, stream=True)
    resp_b = requests.post(f"{BASE_URL}/chat/streaming", data=payload_b, stream=True)

    if resp_a.status_code != 200:
        print(f"❌ ERROR: Respuesta inesperada para sesión A: {resp_a.status_code}")
        return False
    if resp_b.status_code != 200:
        print(f"❌ ERROR: Respuesta inesperada para sesión B: {resp_b.status_code}")
        return False

    data_a = resp_a.text
    data_b = resp_b.text
    resp_a.close()
    resp_b.close()

    if "Ana López" in data_b or "Carlos Ruiz" in data_a:
        print("❌ ERROR: Los mapas de anonimización se mezclaron entre sesiones.")
        return False
    else:
        print("✅ OK: Los mapas de anonimización están aislados por sesión.")
        return True

if __name__ == "__main__":
    print("🔐 Test de aislamiento de sesiones y mapas de anonimización")
    result = test_session_isolation()
    if result:
        print("🎉 Test PASÓ")
    else:
        print("⚠️  Test FALLÓ")