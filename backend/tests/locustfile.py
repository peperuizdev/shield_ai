from locust import HttpUser, task, between, events
import time

# Variables globales para métricas personalizadas
max_response_time = 0
min_response_time = float("inf")
total_requests = 0
total_failures = 0
start_time = None

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global start_time
    start_time = time.time()

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    global max_response_time, min_response_time, total_requests, total_failures
    total_requests += 1
    if exception or (response is not None and not response.ok):
        total_failures += 1
    if response_time > max_response_time:
        max_response_time = response_time
    if response_time < min_response_time:
        min_response_time = response_time

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    duration = time.time() - start_time if start_time else 0
    report = (
        f"--- Stress Test Report ---\n"
        f"Total Requests: {total_requests}\n"
        f"Total Failures: {total_failures}\n"
        f"Max Response Time (ms): {max_response_time:.2f}\n"
        f"Min Response Time (ms): {min_response_time:.2f}\n"
        f"Test Duration (s): {duration:.2f}\n"
        f"Requests per Second: {total_requests/duration if duration > 0 else 0:.2f}\n"
        f"Failure Rate: {100*total_failures/total_requests if total_requests > 0 else 0:.2f}%\n"
        f"Estimated Max Concurrent Users Supported: {estimate_max_users()}\n"
    )
    with open(r"C:\Users\admin\Desktop\SHIELD-AI\proyecto_final\shield_ai\docs\stress_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print(report)

def estimate_max_users():
    # Heurística simple: si el 95% de las respuestas son < 1s y el error < 2%, se considera soportado
    if total_requests == 0:
        return 0
    if max_response_time < 1000 and (total_failures/total_requests) < 0.02:
        return "Tested concurrent users soportados correctamente"
    else:
        return "Límite alcanzado o degradación detectada"

class ShieldAIUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def test_anonymization(self):
        # --> Endpoint: /anonymize/ (POST)
        self.client.post("/anonymize/", json={
            "text": "Juan García, Ingeniero en TechCorp S.A., correo juan.garcia@techcorp.com, teléfono +34 612 345 678",
            "session_id": "stress_test"
        })

    @task
    def test_deanonymization(self):
        # --> Endpoint: /deanonymize/ (POST)
        self.client.post("/deanonymize/", json={
            "text": "[PERSON_1], [MISC_1]., correo juan.garcia@techcorp.com, teléfono +34 612 345 678",
            "session_id": "stress_test"
        })

    @task
    def test_chat_streaming(self):
        # --> Endpoint: /chat/streaming (POST)
        self.client.post("/chat/streaming", data={
            "message": "Hola, necesito ayuda con mi cuenta en TechCorp S.A.",
            "session_id": "stress_test",
            "save_mapping": "true",
            "use_realistic_fake": "false"
        })