from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class AnonymizeRequest(BaseModel):
    text: str
    model: Optional[str] = 'es'
    use_regex: Optional[bool] = False
    pseudonymize: Optional[bool] = False

@router.post('/anonymize')
def anonymize(req: AnonymizeRequest):
    try:
        # Local import to avoid startup time for heavy deps
        from backend.app.services.pii_detector import run_pipeline
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PII service not available: {exc}")

    out = run_pipeline(req.model, req.text, use_regex=req.use_regex, pseudonymize=req.pseudonymize, save_mapping=False)
    return out
