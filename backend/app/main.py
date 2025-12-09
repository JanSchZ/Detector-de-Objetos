"""
Sistema de Detección de Objetos con YOLOv11
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import detection_websocket
from app.api.assistant import router as assistant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hooks para la aplicación"""
    print("🚀 Iniciando Detector de Objetos...")
    yield
    print("🛑 Deteniendo Detector de Objetos...")


app = FastAPI(
    title="Detector de Objetos",
    description="Sistema de detección de objetos en tiempo real con YOLOv11",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS para permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas REST
app.include_router(router)
app.include_router(assistant_router)


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
