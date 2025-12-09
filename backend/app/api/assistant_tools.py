"""
Args AI Assistant Tools.
Defines the callable functions that the Gemini AI can use to control the system.
"""
import uuid
import asyncio
from typing import List, Dict, Any, Optional

from app.api.routes import get_current_config, update_config, ConfigUpdate, _current_config
from app.detection import get_pipeline_manager
from app.detection.fusion_engine import FusionStrategy
from app.zones.geometry import ZONE_MANAGER, Zone, ZoneType

# --- Pipeline Tools ---

def list_presets():
    """
    Lista todos los presets de detección disponibles con su descripción.
    Usa esto para saber qué modos puedes activar.
    """
    pm = get_pipeline_manager()
    presets = []
    for pid, p in pm.presets.items():
        presets.append({
            "id": pid,
            "name": p.name,
            "description": p.description,
            "backends": [b.backend_type.value for b in p.backends]
        })
    return {"presets": presets}

def apply_preset(preset_id: str):
    """
    Aplica un preset de configuración completo (cambia backends y estrategia).
    
    Args:
        preset_id: El ID del preset a aplicar (ej: 'home_security', 'pet_monitor')
    """
    pm = get_pipeline_manager()
    if preset_id not in pm.presets:
        return {"error": f"Preset '{preset_id}' no encontrado. Usa list_presets() para ver los disponibles."}
    
    # Trigger async operation from sync tool
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Fire and forget task since we can't await here easily in all contexts
        asyncio.create_task(pm.apply_preset(preset_id))
    else:
        loop.run_until_complete(pm.apply_preset(preset_id))
        
    return {"status": "applied", "preset_id": preset_id, "message": f"Preset {preset_id} activado correctamente."}

def get_pipeline_status():
    """
    Obtiene el estado actual del pipeline de detección.
    Muestra qué backends están activos y la estrategia de fusión.
    """
    pm = get_pipeline_manager()
    return pm.get_status()

def set_fusion_strategy(strategy: str):
    """
    Cambia la estrategia de fusión de resultados.
    
    Args:
        strategy: Una de ['parallel', 'consensus', 'cascade', 'weighted', 'first_wins']
    """
    try:
        strat_enum = FusionStrategy(strategy)
        pm = get_pipeline_manager()
        pm.fusion_engine.config.strategy = strat_enum
        return {"status": "updated", "strategy": strategy}
    except ValueError:
        return {"error": f"Estrategia inválida. Opciones: {[e.value for e in FusionStrategy]}"}

# --- Config Tools ---

def get_system_config():
    """Obtiene la configuración global actual (resolución, FPS, confianza)."""
    config = get_current_config()
    return {
        "video_source": config.video_source.value,
        "model_size": config.model_size.value,
        "confidence_threshold": config.confidence_threshold,
        "max_fps": config.max_fps,
        "recording_enabled": config.recording_enabled
    }

def set_system_config(
    confidence_threshold: float = None,
    max_fps: int = None,
    recording_enabled: bool = None,
    **kwargs
):
    """
    Ajusta parámetros globales del sistema.
    
    Args:
        confidence_threshold: Sensibilidad de detección (0.0 a 1.0)
        max_fps: Límite de FPS para ahorrar CPU
        recording_enabled: Activar/desactivar grabación automática
    """
    args = {}
    if confidence_threshold is not None: args["confidence_threshold"] = confidence_threshold
    if max_fps is not None: args["max_fps"] = max_fps
    if recording_enabled is not None: args["recording_enabled"] = recording_enabled
    
    # Sync update hack (same as before)
    # We update the global Pydantic model directly
    config_dict = _current_config.model_dump()
    config_dict.update(args)
    
    from app.api import routes
    routes._current_config = routes.DetectionConfig(**config_dict)
    
    return {"status": "updated", "changes": args}

# --- Zone Tools ---

def list_zones():
    """Lista las zonas de seguridad configuradas actualmente."""
    zones = ZONE_MANAGER.get_zones()
    return {"zones": [z.to_dict() for z in zones]}

def create_zone(name: str, points: List[List[float]], type: str = "warning"):
    """
    Crea una nueva zona de seguridad.
    
    Args:
        name: Nombre descriptivo (ej: 'Entrada', 'Piscina')
        points: Coordenadas [[x1,y1], [x2,y2], ...] normalizadas 0-1
        type: 'danger' (roja/crítica), 'warning' (amarilla), 'interest' (verde)
    """
    try:
        new_zone = Zone(
            id=str(uuid.uuid4()),
            name=name,
            points=points,
            type=ZoneType(type),
            enabled=True
        )
        ZONE_MANAGER.add_zone(new_zone)
        return {"status": "created", "zone": new_zone.to_dict()}
    except Exception as e:
        return {"error": str(e)}

def delete_zone(name: str):
    """
    Elimina una zona por su nombre.
    """
    normalized_name = name.lower().strip()
    all_zones = ZONE_MANAGER.get_zones()
    for z in all_zones:
        if z.name.lower().strip() == normalized_name:
            ZONE_MANAGER.remove_zone(z.id)
            return {"status": "deleted", "name": name}
    return {"error": f"No encontré ninguna zona llamada '{name}'"}
