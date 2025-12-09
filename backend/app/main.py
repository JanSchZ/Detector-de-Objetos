"""
Sistema de Detección de Objetos con YOLOv11
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
    print(f"🚀 Iniciando Detector de Objetos... (autenticación {auth_status})")
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    await close_db()
    print("🛑 Deteniendo Detector de Objetos...")


app = FastAPI(
    title="Detector de Objetos",
    description="Sistema de detección de objetos en tiempo real con YOLOv11",
    version="0.2.0",
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
app.include_router(recordings_router)
app.include_router(analytics_router)


# WebSocket endpoint
@app.websocket("/ws/detect")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para detección en tiempo real"""
    await detection_websocket(websocket)


@app.get("/")
async def root():
    """Root endpoint con info del API"""
    return {
        "name": "Detector de Objetos",
        "version": "0.1.0",
        "docs": "/docs",
        "websocket": "/ws/detect",
        "endpoints": {
            "config": "/api/config",
            "classes": "/api/classes",
            "models": "/api/models",
            "health": "/api/health",
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
