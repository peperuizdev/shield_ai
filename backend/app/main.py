"""
Shield AI - Main Application Module

Main module for the Shield AI application.
Contains application setup and router mounting.
"""

# Import shared infrastructure
from core.app import app

# === MOUNT ROUTERS ===
from api.routes.health import router as health_router
from api.routes.sessions import router as sessions_router
from api.routes.deanonymization import router as deanonymization_router

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(deanonymization_router)


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
