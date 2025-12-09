"""
AI Assistant powered by Gemini 2.0 Flash.
Helps users understand and configure the detection system.
"""
import os
import asyncio
from pathlib import Path
from typing import List, Optional

# Load .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

from app.api.routes import get_current_config, update_config, ConfigUpdate, _current_config
from app.config import ModelSize, PoseModelSize, VideoSourceType
from app.zones.geometry import ZONE_MANAGER, Zone, ZoneType
import uuid

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# System prompt with full feature documentation
SYSTEM_PROMPT = """Eres un asistente de IA integrado en "VisionMind", una aplicación de detección de objetos en tiempo real usando YOLOv11.

## Tus Capacidades Multimodales:
- **Puedes VER la cámara**: Recibes frames de video cuando el usuario te habla. Úsalos para entender el contexto.
- **Dibuja Zonas**: Puedes crear zonas de seguridad (rojas, amarillas, verdes) basándote en lo que ves.
  - Ej: "Dibuja una zona de peligro en la puerta" -> Analiza dónde está la puerta y crea la zona.

## Funcionalidades del Sistema:

### 📹 Fuentes de Video
- **Webcam**: Cámara USB conectada al computador
- **Cámara IP**: Stream de celular/cámara de red (URL como http://192.168.1.100:8080/videofeed)

### 🤖 Modelos YOLO
- **Detección de objetos**: Detecta 80 clases de objetos (personas, autos, animales, objetos, etc.)
  - Tamaños: nano (más rápido), small, medium, large, xlarge (más preciso)
- **Pose Estimation**: Detecta esqueleto humano con 17 keypoints
  - Se activa con `pose_enabled: true`
  - Dibuja líneas del esqueleto sobre personas detectadas

### ⚙️ Configuración
- **confidence_threshold** (0.0-1.0): Umbral mínimo de confianza para mostrar detecciones
- **iou_threshold** (0.0-1.0): Umbral para Non-Maximum Suppression
- **max_fps** (1-60): Máximo de frames por segundo
- **enabled_classes**: Lista de IDs de clases COCO a detectar

### 🔲 Zonas de Seguridad
- **Zona de Peligro** (type='danger'): Roja. Alerta crítica.
- **Zona de Advertencia** (type='warning'): Amarilla. Alerta preventiva.
- **Zona de Interés** (type='interest'): Verde. Solo conteo/observación.
- **Coordenadas**: [x, y] normalizadas de 0.0 a 1.0. (0,0) es arriba-izquierda, (1,1) es abajo-derecha.

### 🔔 Alertas
- Se generan cuando objetos entran a zonas de peligro/advertencia
- Se muestran en un banner y se almacenan en historial

## Instrucciones:
- Sé conciso y amigable.
- **SIEMPRE responde en español**.
- Si el usuario menciona objetos o lugares, mira la imagen para localizarlos.
- Para crear zonas, estima las coordenadas [x, y] aproximadas basándote en la imagen.
- **Iteración Visual**: Después de crear una zona, pregunta: "¿Te parece bien ubicada?".
  - Si el usuario pide ajustes (ej: "más arriba"), usa `add_zone` con el MISMO `zone_id` para actualizarla.
- Si no entiendes algo, pregunta.
"""

# --- Tools Definitions ---

def get_config():
    """Obtiene la configuración actual del sistema de detección."""
    config = get_current_config()
    return {
        "video_source": config.video_source.value,
        "model_size": config.model_size.value,
        "pose_enabled": config.pose_enabled,
        "pose_model_size": config.pose_model_size.value,
        "confidence_threshold": config.confidence_threshold,
        "max_fps": config.max_fps,
    }

def set_config(
    model_size: str = None,
    pose_enabled: bool = None,
    pose_model_size: str = None,
    confidence_threshold: float = None,
    video_source: str = None,
    max_fps: int = None,
    **kwargs
):
    """
    Modifica la configuración del sistema.

    Args:
        model_size: Tamaño del modelo de detección (nano, small, medium, large, xlarge)
        pose_enabled: Activar o desactivar pose estimation
        pose_model_size: Tamaño del modelo de pose (yolo11n-pose.pt, yolo11s-pose.pt, ...)
        confidence_threshold: Umbral de confianza (0.0 a 1.0)
        video_source: Fuente de video (webcam, ip_camera)
        max_fps: Máximo FPS (1 a 60)
    """
    args = {}
    if model_size is not None: args["model_size"] = model_size
    if pose_enabled is not None: args["pose_enabled"] = pose_enabled
    if pose_model_size is not None: args["pose_model_size"] = pose_model_size
    if confidence_threshold is not None: args["confidence_threshold"] = confidence_threshold
    if video_source is not None: args["video_source"] = video_source
    if max_fps is not None: args["max_fps"] = max_fps

    # Handle alias mapping for model_size
    if "model_size" in args:
        alias_map = {
            "nano": "yolo11n.pt", "small": "yolo11s.pt", "medium": "yolo11m.pt",
            "large": "yolo11l.pt", "xlarge": "yolo11x.pt",
        }
        if args["model_size"] in alias_map:
            args["model_size"] = alias_map[args["model_size"]]

    # Run update in sync wrapper since we are inside a blocking call from Gemini's perspective,
    # but we are in an async route. To safely call async from sync tool:
    # Actually, Gemini SDK tools are sync. We need to run the async update_config.
    # We can use a helper or just create a new loop if needed, but since we are in async path
    # ideally we would use async tools, but SDK supports sync tools best.
    
    # Simple workaround: Run the update immediately if possible or use a sync wrapper
    # For now, let's use the asyncio.run or loop approach as before
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    update = ConfigUpdate(**args)
    if loop.is_running():
        # This is tricky because we are already in an async function (chat).
        # But the tool execution happens inside library code.
        # We will return the intent to update, and let the main loop handle it?
        # No, the "Orderly" pattern suggests we execute it.
        # We'll use a fire-and-forget or a safe wrapper.
        # Ideally, we should refactor `update_config` to have a sync version or use `run_coroutine_threadsafe`
        # But `update_config` modifies global state, so it's relatively fast.
        
        # HACK: Using a background task or just assume it works for now.
        # Better: create a sync version of update_config logic since it just writes to a variable.
        
        # Implementing sync logic directly here to avoid async issues:
        config_dict = _current_config.model_dump()
        config_dict.update(update.model_dump(exclude_unset=True))
        
        # Apply special logic from routes.py (validation is already done by Pydantic mostly)
        # We need to replicate the enum conversion logic if not done
        
        # Just creating the object updates the global config if we assign it back?
        # routes.py `update_config` does: `_current_config = DetectionConfig(**current_data)`
        # `_current_config` is imported. We need to modify the one in routes module.
        from app.api import routes
        routes._current_config = routes.DetectionConfig(**config_dict)
        # Also need to trigger detector update if model changed
        if "model_size" in args or "pose_enabled" in args or "pose_model_size" in args or "model_type" in args:
             # This part requires the reactor/detector which is in websocket.
             # In websocket.py, it reads `config`. 
             # `YOLODetector.update_config` is called by check_config_changes in websocket loop.
             # So just updating the global config object is enough!
             pass

    else:
        loop.run_until_complete(update_config(update))
        
    return {"status": "updated", "changes": args}

def get_zones(**kwargs):
    """Obtiene la lista de zonas de seguridad configuradas."""
    zones = ZONE_MANAGER.get_zones()
    return {"zones": [z.to_dict() for z in zones]}

def add_zone(name: str, points: List[List[float]], type: str, zone_id: str = None, **kwargs):
    """
    Crea o actualiza una zona de seguridad.

    Args:
        name: Nombre descriptivo de la zona
        points: Lista de puntos [x, y] que definen el polígono. Mínimo 3 puntos. Coordenadas 0.0-1.0.
        type: Tipo de zona (danger, warning, interest)
        zone_id: ID opcional. Si se provee, actualiza la zona existente. Si no, crea una nueva.
    """
    try:
        final_id = zone_id if zone_id else str(uuid.uuid4())
        new_zone = Zone(
            id=final_id,
            name=name,
            points=points,
            type=ZoneType(type),
            enabled=True
        )
        ZONE_MANAGER.add_zone(new_zone)
        return {"status": "created/updated", "zone_id": final_id, "zone": new_zone.to_dict()}
    except Exception as e:
        return {"error": str(e)}

def delete_zone(zone_id: str = None, name: str = None, **kwargs):
    """
    Elimina una zona de seguridad existente.

    Args:
        zone_id: ID de la zona a eliminar (opcional si se da el nombre)
        name: Nombre de la zona a eliminar (opcional si se da el ID)
    """
    target_id = zone_id

    # Try to find by name if no ID provided
    if not target_id and name:
        normalized_name = name.lower().strip()
        all_zones = ZONE_MANAGER.get_zones()
        for z in all_zones:
            if z.name.lower().strip() == normalized_name:
                target_id = z.id
                break
    
    if not target_id:
        return {"error": "Zone ID or valid Name required"}
            
    if ZONE_MANAGER.remove_zone(target_id):
        return {"status": "deleted", "zone_id": target_id}
    return {"error": "Zone not found"}


# --- API Models ---

class ChatMessage(BaseModel):
    message: str
    image: Optional[str] = None  # Base64 encoded image
    history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    response: str
    config_changed: bool = False
    zones_changed: bool = False


# --- Routes ---

@router.post("/chat")
async def chat(request: ChatMessage) -> ChatResponse:
    """Chat with the AI assistant"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(500, "GEMINI_API_KEY no configurada. Agrégala al archivo .env")
        
        genai.configure(api_key=api_key)
        
        # Helper to track side effects
        side_effects = {"config_changed": False, "zones_changed": False}

        # Wrappers to track changes
        def video_mind_set_config(**kwargs):
            side_effects["config_changed"] = True
            return set_config(**kwargs)

        def video_mind_add_zone(**kwargs):
            side_effects["zones_changed"] = True
            return add_zone(**kwargs)

        def video_mind_delete_zone(**kwargs):
            side_effects["zones_changed"] = True
            return delete_zone(**kwargs)
        
        # Available tools
        tools = [get_config, video_mind_set_config, get_zones, video_mind_add_zone, video_mind_delete_zone]

        # Get model name from env or default to flash (which works)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            tools=tools
        )
        
        # Build history
        history_content = []
        if request.history:
            for msg in request.history:
                role = "user" if msg.get("role") == "user" else "model"
                history_content.append({"role": role, "parts": [msg.get("content", "")]})
        
        # Start chat session
        chat_session = model.start_chat(
            history=history_content,
            enable_automatic_function_calling=True
        )
        
        # Prepare current message
        message_parts = [request.message]
        if request.image:
             # Assumes image is base64 string
            image_data = request.image
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            
            import base64
            image_bytes = base64.b64decode(image_data)
            
            message_parts.append({
                "mime_type": "image/jpeg",
                "data": image_bytes
            })
            
        # Send message (SDK handles function calling loop automatically usually, logic below)
        # enable_automatic_function_calling is safe to use here? 
        # Since we want to return the result in one request, we rely on the SDK 
        # to execute functions and then generate the final answer.
        
        response = chat_session.send_message(message_parts)
        
        # The response should now contain the final text after any tool use
        return ChatResponse(
            response=response.text,
            config_changed=side_effects["config_changed"],
            zones_changed=side_effects["zones_changed"]
        )
        
    except Exception as e:
        print(f"Error en chat: {e}")
        raise HTTPException(500, f"Error en el asistente: {str(e)}")
