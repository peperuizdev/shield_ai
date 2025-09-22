import os
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env.example"))

API_KEY = os.getenv("GROK_API_KEY")
print(f"API Key cargada: {bool(API_KEY)}")

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
payload = {"model": "grok-3.1", "prompt": "Hola, escribe algo breve.", "max_output_tokens": 50}

response = requests.post("https://api.grok.ai/v1/generate", headers=headers, json=payload)
print(response.status_code, response.text)
