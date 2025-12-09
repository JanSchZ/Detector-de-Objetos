"""
Argos - Multi-Backend Object Detection System
FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import detection_websocket
from app.api.assistant import router as assistant_router
from app.api.auth_routes import router as auth_router
from app.middleware import setup_middleware
from app.auth import AUTH_ENABLED
from app.database import init_db, close_db

# CORS configuration from environment
CORS_ORIGINS = os.getenv("VM_CORS_ORIGINS", "*").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hooks para la aplicación"""
    auth_status = "habilitada" if AUTH_ENABLED else "deshabilitada"
    print(f"🚀 Iniciando Argos... (autenticación {auth_status})")
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    await close_db()
    print("🛑 Deteniendo Argos...")


app = FastAPI(
    title="Argos",
    description="Sistema de detección de objetos multi-backend con IA",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup custom middleware (rate limiting, security headers)
setup_middleware(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(assistant_router)
app.include_router(auth_router)

# Import and include new feature routers
from app.recordings import router as recordings_router
from app.analytics import router as analytics_router
from app.api.pipeline_routes import router as pipeline_router

app.include_router(recordings_router)
app.include_router(analytics_router)
app.include_router(pipeline_router)


# WebSocket endpoint
@app.websocket("/ws/detect")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para detección en tiempo real"""
    await detection_websocket(websocket)


@app.get("/")
async def root():
    """Root endpoint con info del API"""
    return {
        "name": "Argos",
        "version": "1.0.0",
        "description": "El gigante de los 100 ojos - Sistema de detección multi-backend",
        "docs": "/docs",
        "websocket": "/ws/detect",
        "endpoints": {
            "config": "/api/config",
            "classes": "/api/classes",
            "models": "/api/models",
            "health": "/api/health",
            "pipeline": {
                "status": "/api/pipeline/status",
                "presets": "/api/pipeline/presets",
                "backends": "/api/pipeline/backends",
                "fusion": "/api/pipeline/fusion",
                "capabilities": "/api/pipeline/capabilities",
            },
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
