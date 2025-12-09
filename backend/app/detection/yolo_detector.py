"""
YOLOv11 Detector wrapper.
Maneja carga del modelo, inferencia y postprocesamiento de detecciones.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from dataclasses import dataclass, field
from typing import Any
import time

from app.config import DetectionConfig, COCO_CLASSES_ES, ModelSize, ModelType, PoseModelSize


# Conexiones del esqueleto COCO para pose estimation (17 keypoints)
# Índices: 0=nariz, 1=ojo_izq, 2=ojo_der, 3=oreja_izq, 4=oreja_der,
#          5=hombro_izq, 6=hombro_der, 7=codo_izq, 8=codo_der,
#          9=muñeca_izq, 10=muñeca_der, 11=cadera_izq, 12=cadera_der,
#          13=rodilla_izq, 14=rodilla_der, 15=tobillo_izq, 16=tobillo_der
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # Cara
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Brazos
    (5, 11), (6, 12), (11, 12),  # Torso
    (11, 13), (13, 15), (12, 14), (14, 16),  # Piernas
]

KEYPOINT_NAMES = [
    "nariz", "ojo_izq", "ojo_der", "oreja_izq", "oreja_der",
    "hombro_izq", "hombro_der", "codo_izq", "codo_der",
    "muñeca_izq", "muñeca_der", "cadera_izq", "cadera_der",
    "rodilla_izq", "rodilla_der", "tobillo_izq", "tobillo_der"
]


@dataclass
class Keypoint:
    """Representa un keypoint de pose estimation"""
    x: int
    y: int
    confidence: float
    name: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "confidence": round(self.confidence, 3),
            "name": self.name,
        }


@dataclass
class Detection:
    """Representa una detección individual"""
    class_id: int
    class_name: str
    class_name_es: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    keypoints: list[Keypoint] = field(default_factory=list)  # Para pose estimation
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "class_name_es": self.class_name_es,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
        }
        if self.keypoints:
            result["keypoints"] = [kp.to_dict() for kp in self.keypoints]
        return result


@dataclass
class DetectionResult:
    """Resultado completo de una inferencia"""
    detections: list[Detection]
    inference_time_ms: float
    frame_width: int
    frame_height: int
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict[str, Any]:
        # Contar objetos por clase
        counts: dict[str, int] = {}
        for det in self.detections:
            key = det.class_name_es
            counts[key] = counts.get(key, 0) + 1
        
        return {
            "detections": [d.to_dict() for d in self.detections],
            "counts": counts,
            "total_objects": len(self.detections),
            "inference_time_ms": round(self.inference_time_ms, 2),
            "frame_size": {"width": self.frame_width, "height": self.frame_height},
            "timestamp": self.timestamp,
        }


class YOLODetector:
    """
    Wrapper para YOLOv11 de Ultralytics.
    Maneja carga de modelo, configuración y detección.
    Soporta tanto detección de objetos como estimación de pose.
    """
    
    def __init__(self, config: DetectionConfig | None = None):
        self.config = config or DetectionConfig()
        self.model: YOLO | None = None
        self.pose_model: YOLO | None = None
        self._model_loaded: str | None = None
        self._pose_model_loaded: str | None = None
        
    def load_model(self, model_size: ModelSize | None = None) -> None:
        """Carga el modelo YOLO de detección especificado"""
        model_name = model_size.value if model_size else self.config.model_size.value
        
        # No recargar si ya está cargado el mismo modelo
        if self._model_loaded == model_name and self.model is not None:
            return
            
        print(f"🔄 Cargando modelo de detección {model_name}...")
        self.model = YOLO(model_name)
        self._model_loaded = model_name
        print(f"✅ Modelo de detección {model_name} cargado correctamente")
    
    def load_pose_model(self, pose_model_size: PoseModelSize | None = None) -> None:
        """Carga el modelo YOLO de pose estimation"""
        model_name = pose_model_size.value if pose_model_size else self.config.pose_model_size.value
        
        # No recargar si ya está cargado el mismo modelo
        if self._pose_model_loaded == model_name and self.pose_model is not None:
            return
            
        print(f"🔄 Cargando modelo de pose {model_name}...")
        self.pose_model = YOLO(model_name)
        self._pose_model_loaded = model_name
        print(f"✅ Modelo de pose {model_name} cargado correctamente")
        
    def update_config(self, config: DetectionConfig) -> None:
        """Actualiza la configuración del detector"""
        old_model = self.config.model_size
        old_pose_model = self.config.pose_model_size
        old_pose_enabled = self.config.pose_enabled
        self.config = config
        
        # Recargar modelo de detección si cambió el tamaño
        if old_model != config.model_size:
            self.load_model(config.model_size)
        
        # Cargar/recargar modelo de pose si está habilitado y cambió
        if config.pose_enabled:
            if not old_pose_enabled or old_pose_model != config.pose_model_size:
                self.load_pose_model(config.pose_model_size)
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Ejecuta detección en un frame.
        
        Args:
            frame: Imagen BGR de OpenCV
            
        Returns:
            DetectionResult con todas las detecciones
        """
        if self.model is None:
            self.load_model()
        
        start_time = time.perf_counter()
        
        # Ejecutar inferencia
        results = self.model(
            frame,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            classes=self.config.enabled_classes if self.config.enabled_classes else None,
            verbose=False,
        )
        
        inference_time = (time.perf_counter() - start_time) * 1000
        
        # Procesar resultados
        detections: list[Detection] = []
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
                
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Obtener nombres de clase
                class_name = result.names.get(class_id, f"class_{class_id}")
                class_name_es = COCO_CLASSES_ES.get(class_id, class_name)
                
                # Filtrar por región de conteo si está configurada
                if self.config.counting_region:
                    region = self.config.counting_region
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    if not (region.x <= center_x <= region.x + region.width and
                            region.y <= center_y <= region.y + region.height):
                        continue
                
                detections.append(Detection(
                    class_id=class_id,
                    class_name=class_name,
                    class_name_es=class_name_es,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                ))
        
        h, w = frame.shape[:2]
        return DetectionResult(
            detections=detections,
            inference_time_ms=inference_time,
            frame_width=w,
            frame_height=h,
        )
    
    def detect_pose(self, frame: np.ndarray) -> DetectionResult:
        """
        Ejecuta detección de pose en un frame.
        Solo detecta personas y extrae keypoints del esqueleto.
        
        Args:
            frame: Imagen BGR de OpenCV
            
        Returns:
            DetectionResult con detecciones que incluyen keypoints
        """
        if self.pose_model is None:
            self.load_pose_model()
        
        start_time = time.perf_counter()
        
        # Ejecutar inferencia con modelo de pose
        results = self.pose_model(
            frame,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            verbose=False,
        )
        
        inference_time = (time.perf_counter() - start_time) * 1000
        
        # Procesar resultados
        detections: list[Detection] = []
        
        for result in results:
            boxes = result.boxes
            keypoints_data = result.keypoints
            
            if boxes is None:
                continue
            
            for i, box in enumerate(boxes):
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Nota: Pose models solo detectan personas (class_id=0)
                class_name = "person"
                class_name_es = "persona"
                
                # Extraer keypoints si están disponibles
                keypoints: list[Keypoint] = []
                if keypoints_data is not None and i < len(keypoints_data):
                    kp_array = keypoints_data[i]
                    if hasattr(kp_array, 'data') and kp_array.data is not None:
                        kp_coords = kp_array.data[0]  # Shape: (17, 3) - x, y, conf
                        for kp_idx, kp in enumerate(kp_coords):
                            kp_x, kp_y, kp_conf = float(kp[0]), float(kp[1]), float(kp[2])
                            if kp_conf > 0.3:  # Solo keypoints con confianza mínima
                                keypoints.append(Keypoint(
                                    x=int(kp_x),
                                    y=int(kp_y),
                                    confidence=kp_conf,
                                    name=KEYPOINT_NAMES[kp_idx] if kp_idx < len(KEYPOINT_NAMES) else f"kp_{kp_idx}"
                                ))
                
                detections.append(Detection(
                    class_id=class_id,
                    class_name=class_name,
                    class_name_es=class_name_es,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    keypoints=keypoints,
                ))
        
        h, w = frame.shape[:2]
        return DetectionResult(
            detections=detections,
            inference_time_ms=inference_time,
            frame_width=w,
            frame_height=h,
        )
    
    def draw_detections(
        self, 
        frame: np.ndarray, 
        result: DetectionResult
    ) -> np.ndarray:
        """
        Dibuja bounding boxes y labels en el frame.
        
        Args:
            frame: Imagen BGR original
            result: Resultado de detección
            
        Returns:
            Frame con anotaciones dibujadas
        """
        output = frame.copy()
        
        # Parsear color del config
        color_hex = self.config.box_color.lstrip('#')
        color_bgr = tuple(int(color_hex[i:i+2], 16) for i in (4, 2, 0))
        
        font_scale = self.config.font_size / 32
        thickness = max(1, self.config.font_size // 8)
        
        for det in result.detections:
            x1, y1, x2, y2 = det.bbox
            
            # Dibujar bounding box
            cv2.rectangle(output, (x1, y1), (x2, y2), color_bgr, thickness)
            
            # Preparar label
            if self.config.show_labels:
                label = det.class_name_es
                if self.config.show_confidence:
                    label += f" {det.confidence:.0%}"
                
                # Background del label
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
                )
                cv2.rectangle(
                    output,
                    (x1, y1 - label_h - 10),
                    (x1 + label_w + 5, y1),
                    color_bgr,
                    -1  # Relleno
                )
                
                # Texto
                cv2.putText(
                    output,
                    label,
                    (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 255, 255),  # Blanco
                    thickness,
                )
        
        # Dibujar región de conteo si existe
        if self.config.counting_region:
            r = self.config.counting_region
            cv2.rectangle(
                output,
                (r.x, r.y),
                (r.x + r.width, r.y + r.height),
                (0, 255, 255),  # Amarillo
                2,
            )
            cv2.putText(
                output,
                "Zona de conteo",
                (r.x + 5, r.y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
            )
        
        return output
