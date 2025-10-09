"""
Shield AI - Main Application Module

Main module for the Shield AI application.
Contains application setup and router mounting.
"""

# Import shared infrastructure
from core.app import app

# Mount routers for health, sessions, anonymization, deanonymization, chat, debug, metrics and alerts
from api.routes.health import router as health_router
from api.routes.sessions import router as sessions_router
from api.routes.anonymization import router as anonymization_router
from api.routes.deanonymization import router as deanonymization_router
from api.routes.chat import router as chat_router
from api.routes.document_processing import router as document_processing_router
from api.routes.debug_routes import router as debug_router
from api.routes.metrics import router as metrics_router
from api.routes.alerts import router as alerts_router

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(anonymization_router, tags=["Anonymization"])
app.include_router(deanonymization_router, tags=["Deanonymization"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(document_processing_router, tags=["Document Processing"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(metrics_router, tags=["Metrics"])
app.include_router(alerts_router, tags=["Alerts"])


# === MAIN APPLICATION ENTRY POINT ===

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )