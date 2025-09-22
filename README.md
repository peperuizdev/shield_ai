Estructura y Función de Archivos

## 1. Árbol de la estructura actual (con minidescripción)

```
PROYECTO_FINAL_SHIELD
└───backend
│         └app
│            ├───api
│            │     └───routes
│            │            └───anonymization.py   # Router FastAPI: endpoint /anonymize
│            │
│            ├───map
│            │     └───anonymized_map.json    # Mapeo de datos anonimizados (JSON)
│            │
│            └───services
│                       └───pii_detector.py        # Módulo principal de detección/anonimización PII
│                       └───revalidate_and_review.py # Script para revisar y validar mappings
│                       └───run_cli_wrapper.py     # Wrapper CLI para ejecutar el pipeline desde la nueva estructura
│                       └───run_interactive.ps1    # Script PowerShell para activar venv y lanzar el pipeline
│                        
│
│
│
│
└───   .env                  # Variables de entorno globales (credenciales, flags)
└───   README.md             # Documentación principal del proyecto
└───   requirements.txt      # Dependencias Python globales

```

---

## 2. Función de cada archivo / carpeta

| Archivo/Carpeta                | ¿Qué hace? / Para qué sirve / Cómo y cuándo usarlo |
|---------------------------------|---------------------------------------------------|
| .env (raíz y backend/app)     | Variables de entorno para configuración (credenciales, flags, rutas). Se cargan automáticamente por scripts y servicios. Útil para separar datos sensibles y parámetros de ejecución. |
| activar.txt                   | Notas rápidas, comandos útiles y recordatorios. Incluye la línea para lanzar el pipeline interactivo. Útil para onboarding y referencia rápida. |
| README.md (raíz y backend/app)| Documentación del proyecto y del submódulo backend/app. Explica cómo ejecutar, requisitos y estructura. Leer antes de empezar. |
| requirements.txt (raíz y backend/app) | Listado de dependencias Python. Instalar con `pip install -r requirements.txt` antes de ejecutar scripts. |
| anonymization.py | Router FastAPI que expone el endpoint `/anonymize` (POST). Recibe JSON con texto y parámetros, llama al servicio de detección/anonimización. Usar para integración API. |
| anonymized_map.json | Archivo JSON con el resultado de la anonimización (mapeo original → anonimizados). Útil para auditoría, revalidación y debugging. |
| pii_detector.py | Módulo principal de procesamiento PII . Incluye la función `run_pipeline` y helpers para detección, regex, pseudonimización y reporte. Usar como núcleo del sistema. |
| revalidate_and_review.py | Script para revisar y revalidar mappings guardados. Permite validar formatos y consistencia antes de aplicar cambios definitivos. Útil para control de calidad. |
| run_cli_wrapper.py | Wrapper Python para ejecutar el pipeline desde la nueva estructura. Permite lanzar la consola interactiva sin modificar el pipeline original. Usar para compatibilidad CLI. |
| run_interactive.ps1 | Script PowerShell para activar el virtualenv y lanzar el pipeline interactivo. Incluye rutinas para saltar políticas de ejecución si es necesario. Usar para ejecución rápida en Windows. |

---


3. Run the interactive pipeline:

```powershell
.\backend\app\services\run_interactive.ps1
```

