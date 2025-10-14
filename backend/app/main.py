"""
Shield AI - Main Application Module

Main module for the Shield AI application.
Contains application setup and router mounting.
"""

# Import shared infrastructure
from core.app import app

# Mount routers for health, sessions, anonymization, deanonymization, chat and debug
from api.routes.health import router as health_router
from api.routes.sessions import router as sessions_router
from api.routes.anonymization import router as anonymization_router
from api.routes.deanonymization import router as deanonymization_router
from api.routes.chat import router as chat_router
from api.routes.document_processing import router as document_processing_router
from api.routes.debug_routes import router as debug_router

# Registrar rutas con sus prefijos
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(anonymization_router, prefix="/api/anonymization", tags=["Anonymization"])
app.include_router(deanonymization_router, prefix="/api/deanonymization", tags=["Deanonymization"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(document_processing_router, prefix="/api/document-processing", tags=["Document Processing"])
app.include_router(debug_router, prefix="/api/debug", tags=["Debug"])


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