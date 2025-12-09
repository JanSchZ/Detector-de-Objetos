"""
REST API routes para configuración del sistema.
Incluye endpoints para zonas y alertas.
"""
import base64
import time
import cv2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DetectionConfig, COCO_CLASSES_ES, ModelSize, ModelType, PoseModelSize, DEFAULT_CONFIG, VideoSourceType
from app.zones import Zone, ZoneType, ZoneManager, DEFAULT_POOL_ZONES
from app.alerts import AlertConfig, AlertNotifier

router = APIRouter(prefix="/api", tags=["config"])


# Estado global (clonado del default para evitar mutaciones compartidas)
_current_config = DetectionConfig(**DEFAULT_CONFIG.model_dump())
_zone_manager = ZoneManager()
_alert_notifier = AlertNotifier()

# Frame buffer para recibir frames del móvil
_mobile_frame_buffer = {
    "frame": None,  # bytes del frame
    "timestamp": 0,
    "active": False,
}

# Cargar zonas por defecto
for zone in DEFAULT_POOL_ZONES:
    _zone_manager.add_zone(zone)


class ConfigUpdate(BaseModel):
    """Schema para actualización parcial de configuración"""
    video_source: str | None = None
    webcam_index: int | None = None
    ip_camera_url: str | None = None
    model_type: str | None = None
    model_size: str | None = None
    confidence_threshold: float | None = None
    iou_threshold: float | None = None
    pose_enabled: bool | None = None
    pose_model_size: str | None = None
    enabled_classes: list[int] | None = None
    counting_enabled: bool | None = None
    show_confidence: bool | None = None
    show_labels: bool | None = None
    box_color: str | None = None
    max_fps: int | None = None


class ZoneCreate(BaseModel):
    """Schema para crear zona"""
    id: str
    name: str
    type: str  # "warning" | "danger"
    polygon: list[list[float]]  # [[x, y], [x, y], ...]
    color: str = "#f59e0b"
    enabled: bool = True


class AlertConfigUpdate(BaseModel):
    """Schema para configurar alertas"""
    enabled: bool | None = None
    ntfy_topic: str | None = None
    min_confidence: float | None = None
    min_frames_in_zone: int | None = None
    cooldown_seconds: float | None = None
    alert_classes: list[str] | None = None


class MobileFrame(BaseModel):
    """Frame enviado desde la app móvil"""
    frame: str  # base64 encoded JPEG


# ===== Mobile Frame =====

@router.post("/frame")
async def receive_mobile_frame(data: MobileFrame) -> dict:
    """Recibe un frame del celular para procesamiento"""
    global _mobile_frame_buffer
    try:
        frame_bytes = base64.b64decode(data.frame)
        _mobile_frame_buffer["frame"] = frame_bytes
        _mobile_frame_buffer["timestamp"] = time.time()
        _mobile_frame_buffer["active"] = True
        return {"status": "ok", "size": len(frame_bytes)}
    except Exception as e:
        raise HTTPException(400, f"Error decodificando frame: {str(e)}")


@router.get("/frame/status")
async def get_mobile_frame_status() -> dict:
    """Estado del frame buffer del móvil"""
    return {
        "active": _mobile_frame_buffer["active"],
        "has_frame": _mobile_frame_buffer["frame"] is not None,
        "last_timestamp": _mobile_frame_buffer["timestamp"],
        "age_ms": (time.time() - _mobile_frame_buffer["timestamp"]) * 1000 if _mobile_frame_buffer["timestamp"] else None,
    }


# ===== Health =====

@router.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "ok", "service": "argos"}


@router.get("/cameras")
async def list_available_cameras() -> dict:
    """
    Enumera las cámaras disponibles en el sistema.
    Prueba índices 0-4 para detectar webcams conectadas.
    """
    cameras = []
    
    for index in range(5):  # Probar índices 0-4
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                # Intentar leer un frame para confirmar que funciona
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    cameras.append({
                        "index": index,
                        "name": f"Cámara {index}",
                        "resolution": {"width": w, "height": h},
                        "available": True,
                    })
                cap.release()
        except Exception:
            pass
    
    # También incluir opción de cámara IP si está configurada
    cfg = get_current_config()
    has_ip_camera = bool(cfg.ip_camera_url)
    
    return {
        "cameras": cameras,
        "total": len(cameras),
        "has_ip_camera_configured": has_ip_camera,
        "ip_camera_url": cfg.ip_camera_url if has_ip_camera else None,
        "current_source": cfg.video_source.value,
        "current_webcam_index": cfg.webcam_index,
    }


@router.get("/camera/status")
async def camera_status() -> dict:
    """
    Verifica conectividad de la fuente de video actual.
    Intenta abrir y leer un frame rápido para reportar resolución.
    """
    cfg = get_current_config()

    if cfg.video_source == VideoSourceType.IP_CAMERA:
        if not cfg.ip_camera_url:
            raise HTTPException(400, "URL de cámara IP no configurada")

        try:
            cap = cv2.VideoCapture(cfg.ip_camera_url)
            opened = cap.isOpened()
            if opened:
                ret, frame = cap.read()
                cap.release()
            else:
                ret, frame = False, None
        except Exception:
             return {
                "status": "busy",
                "source": "ip_camera",
                "url": cfg.ip_camera_url,
                "message": "Cámara IP ocupada o inalcanzable"
            }

        if not opened or not ret or frame is None:
             return {
                "status": "error",
                "source": "ip_camera",
                "url": cfg.ip_camera_url,
                "message": "No se pudo conectar a la cámara IP"
            }

        h, w = frame.shape[:2]
        return {
            "status": "ok",
            "source": "ip_camera",
            "url": cfg.ip_camera_url,
            "resolution": {"width": int(w), "height": int(h)},
        }

    # Webcam
    try:
        cap = cv2.VideoCapture(cfg.webcam_index)
        opened = cap.isOpened()
        if opened:
            ret, frame = cap.read()
            cap.release()
        else:
            ret, frame = False, None
    except Exception:
        # Probablemente ocupada por el loop de detección
        # No fallamos, solo reportamos que no podemos obtener frame nuevo
        return {
            "status": "busy",
            "source": "webcam",
            "index": cfg.webcam_index,
            "message": "Cámara ocupada o no disponible (posiblemente en uso por detección)"
        }

    if not opened or not ret or frame is None:
        # No es error 500 necesariamente, puede estar ocupada
        return {
            "status": "error",
            "source": "webcam",
            "index": cfg.webcam_index,
            "message": "No se pudo leer frame (cámara ocupada o desconectada)"
        }

    h, w = frame.shape[:2]
    return {
        "status": "ok",
        "source": "webcam",
        "index": cfg.webcam_index,
        "resolution": {"width": int(w), "height": int(h)},
    }


# ===== Config =====

@router.get("/config")
async def get_config() -> dict:
    """Obtiene la configuración actual"""
    return _current_config.model_dump()


@router.put("/config")
async def update_config(update: ConfigUpdate) -> dict:
    """Actualiza la configuración"""
    global _current_config
    
    current_data = _current_config.model_dump()
    update_data = update.model_dump(exclude_none=True)
    
    if "video_source" in update_data:
        try:
            update_data["video_source"] = VideoSourceType(update_data["video_source"])
        except ValueError:
            raise HTTPException(400, f"Fuente de video inválida: {update_data['video_source']}")

    if "model_type" in update_data:
        try:
            update_data["model_type"] = ModelType(update_data["model_type"])
        except ValueError:
            raise HTTPException(400, f"Tipo de modelo inválido: {update_data['model_type']}")

    if "model_size" in update_data:
        # Mapear alias a valores de enum
        model_size_alias = {
            "nano": ModelSize.NANO,
            "small": ModelSize.SMALL,
            "medium": ModelSize.MEDIUM,
            "large": ModelSize.LARGE,
            "xlarge": ModelSize.XLARGE,
        }
        size_value = update_data["model_size"]
        if size_value in model_size_alias:
            update_data["model_size"] = model_size_alias[size_value]
        else:
            try:
                update_data["model_size"] = ModelSize(size_value)
            except ValueError:
                raise HTTPException(400, f"Tamaño de modelo inválido: {size_value}")
    
    if "pose_model_size" in update_data:
        try:
            update_data["pose_model_size"] = PoseModelSize(update_data["pose_model_size"])
        except ValueError:
            raise HTTPException(400, f"Tamaño de modelo de pose inválido: {update_data['pose_model_size']}")
    
    current_data.update(update_data)
    
    try:
        _current_config = DetectionConfig(**current_data)
    except Exception as e:
        raise HTTPException(400, f"Error en configuración: {str(e)}")
    
    return {"status": "updated", "config": _current_config.model_dump()}


@router.post("/config/reset")
async def reset_config() -> dict:
    """Resetea la configuración a valores por defecto"""
    global _current_config
    _current_config = DetectionConfig(**DEFAULT_CONFIG.model_dump())
    return {"status": "reset", "config": _current_config.model_dump()}


# ===== Classes & Models =====

@router.get("/classes")
async def get_available_classes() -> dict:
    """Obtiene todas las clases disponibles para detectar"""
    return {
        "classes": [
            {"id": id, "name": name}
            for id, name in sorted(COCO_CLASSES_ES.items())
        ],
        "total": len(COCO_CLASSES_ES),
    }


@router.get("/models")
async def get_available_models() -> dict:
    """Obtiene los modelos disponibles para detección y pose"""
    return {
        "detection_models": [
            {"id": "yolo11n.pt", "name": "YOLOv11 Nano", "description": "Más rápido"},
            {"id": "yolo11s.pt", "name": "YOLOv11 Small", "description": "Balance"},
            {"id": "yolo11m.pt", "name": "YOLOv11 Medium", "description": "Buena precisión"},
            {"id": "yolo11l.pt", "name": "YOLOv11 Large", "description": "Alta precisión"},
            {"id": "yolo11x.pt", "name": "YOLOv11 XLarge", "description": "Máxima precisión"},
        ],
        "pose_models": [
            {"id": "yolo11n-pose.pt", "name": "YOLOv11 Nano Pose", "description": "Más rápido"},
            {"id": "yolo11s-pose.pt", "name": "YOLOv11 Small Pose", "description": "Balance"},
            {"id": "yolo11m-pose.pt", "name": "YOLOv11 Medium Pose", "description": "Buena precisión"},
            {"id": "yolo11l-pose.pt", "name": "YOLOv11 Large Pose", "description": "Alta precisión"},
            {"id": "yolo11x-pose.pt", "name": "YOLOv11 XLarge Pose", "description": "Máxima precisión"},
        ],
        # Mantener 'models' para compatibilidad con frontend actual
        "models": [
            {"id": "nano", "name": "YOLOv11 Nano", "file": "yolo11n.pt", "description": "Más rápido"},
            {"id": "small", "name": "YOLOv11 Small", "file": "yolo11s.pt", "description": "Balance"},
            {"id": "medium", "name": "YOLOv11 Medium", "file": "yolo11m.pt", "description": "Buena precisión"},
            {"id": "large", "name": "YOLOv11 Large", "file": "yolo11l.pt", "description": "Alta precisión"},
            {"id": "xlarge", "name": "YOLOv11 XLarge", "file": "yolo11x.pt", "description": "Máxima precisión"},
        ]
    }


# ===== Zones =====

@router.get("/zones")
async def get_zones() -> dict:
    """Obtiene todas las zonas configuradas"""
    return {
        "zones": [z.to_dict() for z in _zone_manager.get_zones()],
        "total": len(_zone_manager.zones),
    }


@router.post("/zones")
async def create_zone(zone_data: ZoneCreate) -> dict:
    """Crea una nueva zona"""
    try:
        zone = Zone(
            id=zone_data.id,
            name=zone_data.name,
            zone_type=ZoneType(zone_data.type),
            polygon=[tuple(p) for p in zone_data.polygon],
            color=zone_data.color,
            enabled=zone_data.enabled,
        )
        _zone_manager.add_zone(zone)
        return {"status": "created", "zone": zone.to_dict()}
    except Exception as e:
        raise HTTPException(400, f"Error creando zona: {str(e)}")


@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str) -> dict:
    """Elimina una zona"""
    if _zone_manager.remove_zone(zone_id):
        return {"status": "deleted", "zone_id": zone_id}
    raise HTTPException(404, f"Zona no encontrada: {zone_id}")


@router.put("/zones/{zone_id}")
async def update_zone(zone_id: str, zone_data: ZoneCreate) -> dict:
    """Actualiza una zona existente"""
    if zone_id not in _zone_manager.zones:
        raise HTTPException(404, f"Zona no encontrada: {zone_id}")
    
    try:
        zone = Zone(
            id=zone_id,
            name=zone_data.name,
            zone_type=ZoneType(zone_data.type),
            polygon=[tuple(p) for p in zone_data.polygon],
            color=zone_data.color,
            enabled=zone_data.enabled,
        )
        _zone_manager.add_zone(zone)  # add_zone también actualiza si ya existe
        return {"status": "updated", "zone": zone.to_dict()}
    except Exception as e:
        raise HTTPException(400, f"Error actualizando zona: {str(e)}")


@router.patch("/zones/{zone_id}/toggle")
async def toggle_zone(zone_id: str) -> dict:
    """Activa/desactiva una zona"""
    if zone_id not in _zone_manager.zones:
        raise HTTPException(404, f"Zona no encontrada: {zone_id}")
    
    zone = _zone_manager.zones[zone_id]
    # Toggle enabled state
    new_zone = Zone(
        id=zone.id,
        name=zone.name,
        zone_type=zone.zone_type,
        polygon=zone.polygon,
        color=zone.color,
        enabled=not zone.enabled,
    )
    _zone_manager.add_zone(new_zone)
    return {"status": "toggled", "zone": new_zone.to_dict()}


@router.delete("/zones")
async def clear_zones() -> dict:
    """Elimina todas las zonas"""
    _zone_manager.clear_zones()
    return {"status": "cleared"}


@router.post("/zones/reset")
async def reset_zones() -> dict:
    """Restaura zonas por defecto (piscina)"""
    _zone_manager.clear_zones()
    for zone in DEFAULT_POOL_ZONES:
        _zone_manager.add_zone(zone)
    return {
        "status": "reset",
        "zones": [z.to_dict() for z in _zone_manager.get_zones()],
    }


# ===== Alerts =====

@router.get("/alerts/config")
async def get_alert_config() -> dict:
    """Obtiene configuración de alertas"""
    cfg = _alert_notifier.config
    return {
        "enabled": cfg.enabled,
        "ntfy_server": cfg.ntfy_server,
        "ntfy_topic": cfg.ntfy_topic,
        "min_confidence": cfg.min_confidence,
        "min_frames_in_zone": cfg.min_frames_in_zone,
        "cooldown_seconds": cfg.cooldown_seconds,
        "alert_classes": cfg.alert_classes,
    }


@router.put("/alerts/config")
async def update_alert_config(update: AlertConfigUpdate) -> dict:
    """Actualiza configuración de alertas"""
    cfg = _alert_notifier.config
    
    if update.enabled is not None:
        cfg.enabled = update.enabled
    if update.ntfy_topic is not None:
        cfg.ntfy_topic = update.ntfy_topic
    if update.min_confidence is not None:
        cfg.min_confidence = update.min_confidence
    if update.min_frames_in_zone is not None:
        cfg.min_frames_in_zone = update.min_frames_in_zone
    if update.cooldown_seconds is not None:
        cfg.cooldown_seconds = update.cooldown_seconds
    if update.alert_classes is not None:
        cfg.alert_classes = update.alert_classes
    
    return {"status": "updated", "config": await get_alert_config()}


@router.get("/alerts/history")
async def get_alert_history() -> dict:
    """Obtiene historial de alertas recientes"""
    return {
        "alerts": [a.to_dict() for a in _alert_notifier.get_recent_alerts(20)],
    }


@router.post("/alerts/test")
async def test_alert() -> dict:
    """Envía alerta de prueba"""
    from app.alerts import Alert, AlertPriority
    import time
    
    test_alert = Alert(
        id="test-alert",
        title="🧪 Alerta de Prueba",
        message="Esta es una alerta de prueba de Argos",
        priority=AlertPriority.NORMAL,
        zone_type=ZoneType.WARNING,
        tracker_id=0,
        class_name="test",
        timestamp=time.time(),
    )
    
    success = await _alert_notifier.send_alert(test_alert)
    return {"status": "sent" if success else "failed", "alert": test_alert.to_dict()}


# ===== Helpers =====

def get_current_config() -> DetectionConfig:
    return _current_config


def set_current_config(config: DetectionConfig) -> None:
    global _current_config
    _current_config = config


def get_zone_manager() -> ZoneManager:
    return _zone_manager


def get_alert_notifier() -> AlertNotifier:
    return _alert_notifier


def get_mobile_frame() -> bytes | None:
    """Obtiene el frame más reciente del móvil si está activo"""
    if _mobile_frame_buffer["active"] and _mobile_frame_buffer["frame"]:
        # Si el frame tiene más de 2 segundos, marcarlo como inactivo
        if time.time() - _mobile_frame_buffer["timestamp"] > 2:
            _mobile_frame_buffer["active"] = False
            return None
        return _mobile_frame_buffer["frame"]
    return None
