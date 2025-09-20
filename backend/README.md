(Minimal run notes)

Run backend from the repository root so the root `.env` file is picked up by the
application (Pydantic `env_file` is resolved relative to the working directory).

PowerShell (from repository root):

	# activate your venv first if you have one
	python -m venv .venv; .\.venv\Scripts\Activate.ps1
	pip install -r backend/requirements.txt
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

New API endpoints (mounted under /anonymization):
 - POST /anonymization/anonymize  (form field `text`)\n - POST /anonymization/anonymize_file (multipart file upload)\n - GET  /anonymization/sample\n - POST /anonymization/revalidate

Notes:
 - Place your HF token and model in the root `.env` (HF_TOKEN and SHIELD_AI_HUGGINGFACE_MODEL).
 - The SHIELD2 utilities used by the service live in the `SHIELD2/` folder included in the repo.

