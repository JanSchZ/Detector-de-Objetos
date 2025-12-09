"""
ByteTrack Object Tracker using Supervision library.
Provides persistent IDs for detected objects across frames.
"""
import numpy as np
import supervision as sv
from dataclasses import dataclass
from typing import Any

from app.detection.yolo_detector import Detection, DetectionResult, Keypoint


@dataclass
class TrackedObject:
    """Representa un objeto con tracking persistente"""
    tracker_id: int
    class_id: int
    class_name: str
    class_name_es: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    center: tuple[int, int]  # Centro del bbox
    bottom_center: tuple[int, int]  # Punto inferior central (patas/pies)
    keypoints: list[Keypoint] | None = None  # Keypoints de pose (opcional)
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "tracker_id": self.tracker_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "class_name_es": self.class_name_es,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "center": list(self.center),
            "bottom_center": list(self.bottom_center),
        }
        if self.keypoints:
            result["keypoints"] = [kp.to_dict() for kp in self.keypoints]
        return result


@dataclass
class TrackingResult:
    """Resultado de detección con tracking"""
    objects: list[TrackedObject]
    inference_time_ms: float
    frame_width: int
    frame_height: int
    timestamp: float
    
    def to_dict(self) -> dict[str, Any]:
        # Contar objetos por clase
        counts: dict[str, int] = {}
        for obj in self.objects:
            key = obj.class_name_es
            counts[key] = counts.get(key, 0) + 1
        
        # Tracking IDs activos
        active_ids = [obj.tracker_id for obj in self.objects]
        
        return {
            "objects": [o.to_dict() for o in self.objects],
            "counts": counts,
            "total_objects": len(self.objects),
            "active_tracker_ids": active_ids,
            "inference_time_ms": round(self.inference_time_ms, 2),
            "frame_size": {"width": self.frame_width, "height": self.frame_height},
            "timestamp": self.timestamp,
        }


class ObjectTracker:
    """
    ByteTrack-based object tracker.
    Asigna IDs persistentes a objetos detectados.
    """
    
    def __init__(self):
        self.byte_tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,  # Frames antes de perder track
            minimum_matching_threshold=0.8,
            frame_rate=30,
        )
        self._id_history: dict[int, dict] = {}  # Historial de IDs
    
    def reset(self) -> None:
        """Resetea el tracker"""
        self.byte_tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=30,
        )
        self._id_history.clear()
    
    def update(self, detection_result: DetectionResult) -> TrackingResult:
        """
        Actualiza el tracker con nuevas detecciones.
        
        Args:
            detection_result: Resultado de YOLODetector.detect()
            
        Returns:
            TrackingResult con IDs persistentes
        """
        if not detection_result.detections:
            return TrackingResult(
                objects=[],
                inference_time_ms=detection_result.inference_time_ms,
                frame_width=detection_result.frame_width,
                frame_height=detection_result.frame_height,
                timestamp=detection_result.timestamp,
            )
        
        # Convertir detecciones a formato Supervision
        xyxy = np.array([d.bbox for d in detection_result.detections])
        confidence = np.array([d.confidence for d in detection_result.detections])
        class_id = np.array([d.class_id for d in detection_result.detections])
        
        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )
        
        # Aplicar ByteTrack
        tracked_detections = self.byte_tracker.update_with_detections(sv_detections)
        
        # Construir objetos trackeados
        tracked_objects: list[TrackedObject] = []
        
        for i in range(len(tracked_detections)):
            x1, y1, x2, y2 = map(int, tracked_detections.xyxy[i])
            tracker_id = int(tracked_detections.tracker_id[i]) if tracked_detections.tracker_id is not None else -1
            cls_id = int(tracked_detections.class_id[i]) if tracked_detections.class_id is not None else 0
            conf = float(tracked_detections.confidence[i]) if tracked_detections.confidence is not None else 0.0
            
            # Encontrar detección original para obtener nombres y keypoints
            original_det = next(
                (d for d in detection_result.detections if d.class_id == cls_id),
                detection_result.detections[0] if detection_result.detections else None
            )
            
            class_name = original_det.class_name if original_det else f"class_{cls_id}"
            class_name_es = original_det.class_name_es if original_det else class_name
            keypoints = original_det.keypoints if original_det else None
            
            # Calcular puntos de referencia
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            bottom_center = ((x1 + x2) // 2, y2)  # Punto inferior (pies/patas)
            
            tracked_objects.append(TrackedObject(
                tracker_id=tracker_id,
                class_id=cls_id,
                class_name=class_name,
                class_name_es=class_name_es,
                confidence=conf,
                bbox=(x1, y1, x2, y2),
                center=center,
                bottom_center=bottom_center,
                keypoints=keypoints,
            ))
            
            # Guardar en historial
            self._id_history[tracker_id] = {
                "class": class_name_es,
                "last_seen": detection_result.timestamp,
            }
        
        return TrackingResult(
            objects=tracked_objects,
            inference_time_ms=detection_result.inference_time_ms,
            frame_width=detection_result.frame_width,
            frame_height=detection_result.frame_height,
            timestamp=detection_result.timestamp,
        )
    
    def get_active_ids(self) -> list[int]:
        """Retorna lista de IDs activos"""
        return list(self._id_history.keys())
