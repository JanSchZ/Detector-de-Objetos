"""
WebSocket handler para streaming de detecciones en tiempo real.
Incluye tracking, zonas y alertas.
"""
import asyncio
import base64
import cv2
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any
import time

from app.detection import YOLODetector, ObjectTracker, TrackingResult, SKELETON_CONNECTIONS
from app.video import create_video_source, VideoSource
from app.config import VideoSourceType
from app.zones import ZoneManager, Zone, ZoneType, ZoneEvent
from app.alerts import AlertNotifier, AlertConfig, Alert
from app.api.routes import get_current_config, get_zone_manager, get_alert_notifier, get_mobile_frame


class DetectionStreamer:
    """
    Maneja el streaming de detecciones vía WebSocket.
    Incluye tracking, zonas y alertas.
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.detector: YOLODetector | None = None
        self.tracker: ObjectTracker | None = None
        self.video_source: VideoSource | None = None
        self.zone_manager: ZoneManager | None = None
        self.alert_notifier: AlertNotifier | None = None
        self.running = False
        self._last_frame_time: float = 0.0
        self._sent_waiting_notice = False
        
    async def initialize(self) -> bool:
        """Inicializa detector, tracker, zonas y fuente de video"""
        config = get_current_config()
        print(f"🎥 Config video_source={config.video_source} ip_url='{config.ip_camera_url}' webcam_index={config.webcam_index}")
        
        # Notificar al cliente que estamos inicializando
        await self.send_status("Inicializando detector YOLO...", level="info")
        
        try:
            # Crear detector
            self.detector = YOLODetector(config)
            self.detector.load_model()
            
            await self.send_status("Modelo cargado, iniciando tracker...", level="info")
            
            # Crear tracker
            self.tracker = ObjectTracker()
            
            # Obtener zone manager y alert notifier globales
            self.zone_manager = get_zone_manager()
            self.alert_notifier = get_alert_notifier()
            
            # Crear fuente de video (opcional - puede usar frames del móvil)
            try:
                self.video_source = create_video_source(config)
                if not self.video_source.start():
                    # No fallar, puede usar frames del móvil
                    print("⚠️ Video source no disponible, esperando frames del móvil...")
                    self.video_source = None
            except Exception as e:
                print(f"⚠️ No se pudo crear video source: {e}")
                self.video_source = None
            
            return True
            
        except Exception as e:
            await self.send_error(f"Error de inicialización: {str(e)}")
            return False
    
    async def send_message(self, data: dict[str, Any]) -> None:
        """Envía mensaje JSON por WebSocket"""
        await self.websocket.send_json(data)

    async def send_status(self, message: str, level: str = "info") -> None:
        """Envía mensaje de estado (info/warning) al cliente"""
        await self.send_message({"type": "status", "level": level, "message": message})

    async def send_error(self, message: str) -> None:
        """Envía mensaje de error"""
        await self.send_message({"type": "error", "message": message})
    
    async def send_tracking_result(
        self, 
        result: TrackingResult,
        zone_events: list[ZoneEvent],
        alerts: list[Alert],
        frame_base64: str | None = None
    ) -> None:
        """Envía resultado de tracking con zonas y alertas"""
        data = {
            "type": "detection",
            "data": result.to_dict(),
            "zone_events": [e.to_dict() for e in zone_events],
            "alerts": [a.to_dict() for a in alerts],
            "zones": [z.to_dict() for z in self.zone_manager.get_zones()] if self.zone_manager else [],
        }
        if frame_base64:
            data["frame"] = frame_base64
        await self.send_message(data)
    
    async def process_command(self, message: dict) -> bool:
        """
        Procesa comandos del cliente.
        Returns False si debe terminar el stream.
        """
        cmd = message.get("command")
        
        if cmd == "stop":
            return False
        
        elif cmd == "update_config":
            pass
        
        elif cmd == "add_zone":
            # Agregar zona
            zone_data = message.get("zone")
            if zone_data and self.zone_manager:
                zone = Zone.from_dict(zone_data)
                self.zone_manager.add_zone(zone)
                await self.send_message({
                    "type": "zone_added",
                    "zone": zone.to_dict()
                })
        
        elif cmd == "remove_zone":
            # Eliminar zona
            zone_id = message.get("zone_id")
            if zone_id and self.zone_manager:
                self.zone_manager.remove_zone(zone_id)
                await self.send_message({
                    "type": "zone_removed",
                    "zone_id": zone_id
                })
        
        elif cmd == "clear_zones":
            if self.zone_manager:
                self.zone_manager.clear_zones()
                await self.send_message({"type": "zones_cleared"})
        
        elif cmd == "reset_tracker":
            if self.tracker:
                self.tracker.reset()
                await self.send_message({"type": "tracker_reset"})
        
        return True
    
    def draw_frame_with_zones(
        self, 
        frame: np.ndarray, 
        result: TrackingResult,
        zone_events: list[ZoneEvent]
    ) -> np.ndarray:
        """Dibuja frame con bounding boxes, tracking IDs y zonas"""
        output = frame.copy()
        h, w = output.shape[:2]
        
        config = get_current_config()
        
        # Parsear color del config
        color_hex = config.box_color.lstrip('#')
        color_bgr = tuple(int(color_hex[i:i+2], 16) for i in (4, 2, 0))
        
        # NOTE: Zonas ahora se dibujan solo en el frontend para evitar:
        # 1. Duplicación (backend + frontend dibujaban ambos)
        # 2. Problemas de encoding con cv2.putText (no soporta unicode como ñ)
        # El código original está comentado abajo por referencia
        
        # if self.zone_manager:
        #     for zone in self.zone_manager.get_zones():
        #         points = np.array([
        #             [int(p[0] * w), int(p[1] * h)] 
        #             for p in zone.polygon
        #         ], np.int32)
        #         zone_color_hex = zone.color.lstrip('#')
        #         zone_color = tuple(int(zone_color_hex[i:i+2], 16) for i in (4, 2, 0))
        #         overlay = output.copy()
        #         cv2.fillPoly(overlay, [points], zone_color)
        #         cv2.addWeighted(overlay, 0.3, output, 0.7, 0, output)
        #         cv2.polylines(output, [points], True, zone_color, 2)
        #         cv2.putText(
        #             output, zone.name,
        #             (points[0][0] + 5, points[0][1] + 20),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2,
        #         )
        
        # Dibujar objetos trackeados
        font_scale = config.font_size / 32
        thickness = max(1, config.font_size // 8)
        
        # Determinar objetos en zonas peligrosas
        danger_ids = {
            e.tracker_id for e in zone_events 
            if e.zone_type == ZoneType.DANGER and e.event_type in ("enter", "inside")
        }
        warning_ids = {
            e.tracker_id for e in zone_events 
            if e.zone_type == ZoneType.WARNING and e.event_type in ("enter", "inside")
        }
        
        for obj in result.objects:
            x1, y1, x2, y2 = obj.bbox
            
            # Color según estado
            if obj.tracker_id in danger_ids:
                box_color = (0, 0, 255)  # Rojo
            elif obj.tracker_id in warning_ids:
                box_color = (0, 165, 255)  # Naranja
            else:
                box_color = color_bgr
            
            # Dibujar bounding box
            cv2.rectangle(output, (x1, y1), (x2, y2), box_color, thickness + 1)
            
            # Preparar label con ID
            if config.show_labels:
                label = f"#{obj.tracker_id} {obj.class_name_es}"
                if config.show_confidence:
                    label += f" {obj.confidence:.0%}"
                
                # Background del label
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
                )
                cv2.rectangle(
                    output, (x1, y1 - label_h - 10), (x1 + label_w + 5, y1),
                    box_color, -1
                )
                
                # Texto
                cv2.putText(
                    output, label, (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness,
                )
            
            # Dibujar punto de referencia (pies)
            cv2.circle(output, obj.bottom_center, 4, (0, 255, 255), -1)
            
            # Dibujar esqueleto si hay keypoints (pose estimation)
            if config.pose_enabled and hasattr(obj, 'keypoints') and obj.keypoints:
                # Crear diccionario de keypoints por índice para acceso rápido
                kp_dict = {}
                for kp in obj.keypoints:
                    # Buscar índice por nombre
                    from app.detection import KEYPOINT_NAMES
                    if kp.name in KEYPOINT_NAMES:
                        idx = KEYPOINT_NAMES.index(kp.name)
                        kp_dict[idx] = (kp.x, kp.y, kp.confidence)
                
                # Dibujar conexiones del esqueleto
                for start_idx, end_idx in SKELETON_CONNECTIONS:
                    if start_idx in kp_dict and end_idx in kp_dict:
                        start_kp = kp_dict[start_idx]
                        end_kp = kp_dict[end_idx]
                        if start_kp[2] > 0.3 and end_kp[2] > 0.3:  # Solo si ambos tienen buena confianza
                            cv2.line(
                                output,
                                (int(start_kp[0]), int(start_kp[1])),
                                (int(end_kp[0]), int(end_kp[1])),
                                (0, 255, 0),  # Verde para el esqueleto
                                2
                            )
                
                # Dibujar keypoints como círculos
                for kp in obj.keypoints:
                    if kp.confidence > 0.3:
                        cv2.circle(output, (kp.x, kp.y), 4, (0, 0, 255), -1)  # Rojo para keypoints
        
        return output
    
    async def run_detection_loop(self, include_frames: bool = True) -> None:
        """Loop principal de detección con tracking y zonas"""
        self.running = True
        config = get_current_config()
        loop_counter = 0
        
        frame_interval = 1.0 / config.max_fps
        last_frame_time = 0.0
        self._last_frame_time = time.time()
        
        await self.send_message({
            "type": "started",
            "config": config.model_dump(),
            "frame_size": {
                "width": self.video_source.frame_size[0] if self.video_source else 0,
                "height": self.video_source.frame_size[1] if self.video_source else 0,
            },
            "zones": [z.to_dict() for z in self.zone_manager.get_zones()] if self.zone_manager else [],
        })
        
        try:
            while self.running:
                # Control de FPS
                current_time = asyncio.get_event_loop().time()
                if current_time - last_frame_time < frame_interval:
                    await asyncio.sleep(0.001)
                    continue
                
                last_frame_time = current_time
                loop_counter += 1
                
                # Actualizar config si cambió
                new_config = get_current_config()
                if new_config != config:
                    # Detectar si cambió la configuración de video
                    video_changed = (
                        new_config.video_source != config.video_source or
                        new_config.ip_camera_url != config.ip_camera_url or
                        new_config.webcam_index != config.webcam_index
                    )
                    
                    if video_changed:
                        print(f"🔄 Cambio de configuración de video detectado: {config.video_source} -> {new_config.video_source}")
                    
                    config = new_config
                    if self.detector:
                        self.detector.update_config(config)
                    frame_interval = 1.0 / config.max_fps
                    print(f"⚙️ Config en uso: source={config.video_source} url='{config.ip_camera_url}' webcam_index={config.webcam_index}")
                    
                    # Si cambió el video, liberar source actual para recrearlo en el siguiente loop
                    if video_changed and self.video_source:
                        self.video_source.stop()
                        self.video_source = None
                
                # Leer frame (prioridad: móvil > video_source)
                frame = None
                
                # 1. Intentar frames del móvil (POST /api/frame)
                mobile_frame_bytes = get_mobile_frame()
                if mobile_frame_bytes:
                    nparr = np.frombuffer(mobile_frame_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    self._last_frame_time = time.time()
                
                # 2. Si no hay frame móvil, intentar video source (IP Cam / Webcam)
                if frame is None:
                    # Si no hay video source iniciado, intentar iniciarlo ahora
                    if not self.video_source:
                        try:
                            # Solo intentar iniciar si hay configuración válida
                            if config.video_source == VideoSourceType.IP_CAMERA and not config.ip_camera_url:
                                pass  # No intentar si no hay URL
                            else:
                                self.video_source = create_video_source(config)
                                print(f"🎥 Iniciando fuente {config.video_source}...")
                                if not self.video_source.start():
                                    print("⚠️ No se pudo iniciar fuente de video")
                                    self.video_source = None
                        except Exception as e:
                            print(f"❌ Error al crear video source: {e}")
                            self.video_source = None

                    # Leer del video source si existe
                    if self.video_source:
                        ret, frame = self.video_source.read()
                        if not ret:
                            frame = None
                        else:
                            self._last_frame_time = time.time()
                
                # Si fallaron ambos, esperar y continuar
                if frame is None:
                    # Avisar una sola vez que estamos esperando frames
                    if (time.time() - self._last_frame_time) > 3.0 and not self._sent_waiting_notice:
                        await self.send_status("Esperando frames de la cámara...", level="warning")
                        self._sent_waiting_notice = True
                    await asyncio.sleep(0.1)  # Esperar un poco más para no saturar CPU
                    continue

                if self._sent_waiting_notice:
                    await self.send_status("Frames recibidos, reanudando stream", level="info")
                    self._sent_waiting_notice = False
                    print("✅ Frames recibidos, saliendo de estado de espera")
                
                if not self.detector or not self.tracker:
                    print("❌ Detector o tracker no inicializados, saliendo del loop")
                    break
                
                # Detectar (usar pose o detección normal según config)
                if config.pose_enabled:
                    detection_result = self.detector.detect_pose(frame)
                else:
                    detection_result = self.detector.detect(frame)
                
                # Tracking
                tracking_result = self.tracker.update(detection_result)
                
                # Verificar zonas
                zone_events: list[ZoneEvent] = []
                if self.zone_manager and tracking_result.objects:
                    h, w = frame.shape[:2]
                    zone_events = self.zone_manager.check_objects(
                        [o.to_dict() for o in tracking_result.objects],
                        w, h,
                        time.time()
                    )
                
                # Procesar alertas
                alerts: list[Alert] = []
                if self.alert_notifier:
                    alerts = self.alert_notifier.process_zone_events(zone_events)
                    # Enviar alertas push (async)
                    if alerts:
                        asyncio.create_task(self.alert_notifier.send_alerts(alerts))
                
                # Enviar resultado
                if include_frames:
                    annotated = self.draw_frame_with_zones(frame, tracking_result, zone_events)
                    _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    await self.send_tracking_result(tracking_result, zone_events, alerts, frame_b64)
                else:
                    await self.send_tracking_result(tracking_result, zone_events, alerts)
                
                # Yield para manejar otros eventos
                await asyncio.sleep(0)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ CRASH en loop de detección: {str(e)}")
            await self.send_error(f"Error en loop de detección: {str(e)}")
        finally:
            print(f"ℹ️ Loop de detección terminado tras {loop_counter} iteraciones")
            self.running = False
    
    def stop(self) -> None:
        """Detiene el stream"""
        self.running = False
        if self.video_source:
            self.video_source.stop()


async def detection_websocket(websocket: WebSocket) -> None:
    """
    Endpoint WebSocket principal para detección en tiempo real.
    
    Protocol:
    - Cliente envía: {"command": "start", "include_frames": true/false}
    - Servidor responde: {"type": "started", "config": {...}, "zones": [...]}
    - Servidor envía continuamente: {"type": "detection", "data": {...}, "zone_events": [...], "alerts": [...]}
    - Cliente puede enviar: {"command": "stop"} para terminar
    - Cliente puede enviar: {"command": "add_zone", "zone": {...}}
    - Cliente puede enviar: {"command": "remove_zone", "zone_id": "..."}
    """
    await websocket.accept()
    print("🛰️ WebSocket /ws/detect aceptado")
    streamer = DetectionStreamer(websocket)
    
    try:
        # Esperar comando inicial
        initial_msg = await websocket.receive_json()
        print(f"🛰️ Mensaje inicial: {initial_msg}")
        
        if initial_msg.get("command") != "start":
            await streamer.send_error("Se esperaba comando 'start'")
            return
        
        # Inicializar
        if not await streamer.initialize():
            print("❌ Inicialización fallida en websocket")
            return
        
        include_frames = initial_msg.get("include_frames", True)
        print(f"🛰️ Iniciando loop de detección include_frames={include_frames}")
        
        # Set running flag BEFORE creating task to avoid race condition
        streamer.running = True
        
        # Crear task para el loop de detección
        detection_task = asyncio.create_task(
            streamer.run_detection_loop(include_frames)
        )
        
        # Escuchar comandos del cliente mientras corre detección
        try:
            while streamer.running:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=0.1
                    )
                    if not await streamer.process_command(message):
                        break
                except asyncio.TimeoutError:
                    continue
                    
        except WebSocketDisconnect:
            print("🔌 Cliente cerró WebSocket")
        finally:
            streamer.stop()
            detection_task.cancel()
            if detection_task.done():
                print(f"ℹ️ detection_task finalizado. cancelled={detection_task.cancelled()} exception={detection_task.exception() if detection_task.exception() else None}")
            try:
                await detection_task
            except asyncio.CancelledError:
                pass
            
    except WebSocketDisconnect:
        print("🔌 WebSocket desconectado antes de iniciar detección")
    except Exception as e:
        print(f"❌ Error en websocket: {e}")
        try:
            await streamer.send_error(f"Error: {str(e)}")
        except Exception:
            pass
    finally:
        streamer.stop()
