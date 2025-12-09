"""
Configuración del sistema de detección de objetos.
Valores por defecto y esquemas de configuración.
"""
import os
from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


class ModelSize(str, Enum):
    NANO = "yolo11n.pt"
    SMALL = "yolo11s.pt"
    MEDIUM = "yolo11m.pt"
    LARGE = "yolo11l.pt"
    XLARGE = "yolo11x.pt"


class ModelType(str, Enum):
    """Tipo de modelo YOLO: detección de objetos o estimación de pose"""
    DETECTION = "detection"
    POSE = "pose"


class PoseModelSize(str, Enum):
    """Modelos de YOLO para pose estimation"""
    NANO = "yolo11n-pose.pt"
    SMALL = "yolo11s-pose.pt"
    MEDIUM = "yolo11m-pose.pt"
    LARGE = "yolo11l-pose.pt"
    XLARGE = "yolo11x-pose.pt"


class VideoSourceType(str, Enum):
    WEBCAM = "webcam"
    IP_CAMERA = "ip_camera"


class CountingRegion(BaseModel):
    """Región de interés para conteo selectivo"""
    x: int = Field(ge=0, description="Posición X del inicio de la región")
    y: int = Field(ge=0, description="Posición Y del inicio de la región")
    width: int = Field(gt=0, description="Ancho de la región")
    height: int = Field(gt=0, description="Alto de la región")


class DetectionConfig(BaseModel):
    """Configuración completa del sistema de detección"""
    
    # Fuente de video
    video_source: VideoSourceType = VideoSourceType.WEBCAM
    webcam_index: int = Field(default=0, ge=0, description="Índice de webcam (0, 1, 2...)")
    ip_camera_url: str = Field(default="", description="URL del stream IP (ej: http://192.168.1.100:8080/videofeed)")
    
    # Modelo YOLO
    model_type: ModelType = ModelType.DETECTION
    model_size: ModelSize = ModelSize.NANO
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Threshold para NMS")
    
    # Pose Estimation
    pose_enabled: bool = Field(default=False, description="Habilitar estimación de pose")
    pose_model_size: PoseModelSize = PoseModelSize.NANO
    
    # Clases a detectar (IDs del dataset COCO)
    # Por defecto detectamos objetos cotidianos comunes
    enabled_classes: list[int] = Field(
        default=[
            0,   # person
            39,  # bottle
            41,  # cup
            42,  # fork
            43,  # knife
            44,  # spoon
            45,  # bowl
            46,  # banana
            47,  # apple
            63,  # laptop
            64,  # mouse
            65,  # remote
            66,  # keyboard
            67,  # cell phone
            73,  # book
        ],
        description="IDs de clases COCO a detectar"
    )
    
    # Conteo
    counting_enabled: bool = True
    counting_region: CountingRegion | None = None
    
    # Visualización
    show_confidence: bool = True
    show_labels: bool = True
    box_color: str = Field(default="#00FF00", pattern=r"^#[0-9A-Fa-f]{6}$")
    font_size: int = Field(default=16, ge=8, le=32)
    
    # Performance
    max_fps: int = Field(default=30, ge=1, le=60)
    frame_skip: int = Field(default=0, ge=0, le=10, description="Frames a saltar entre inferencias")


# Mapeo de IDs COCO a nombres en español
COCO_CLASSES_ES: dict[int, str] = {
    0: "persona",
    1: "bicicleta",
    2: "auto",
    3: "moto",
    4: "avión",
    5: "bus",
    6: "tren",
    7: "camión",
    8: "bote",
    9: "semáforo",
    10: "hidrante",
    11: "señal de alto",
    12: "parquímetro",
    13: "banco",
    14: "pájaro",
    15: "gato",
    16: "perro",
    17: "caballo",
    18: "oveja",
    19: "vaca",
    20: "elefante",
    21: "oso",
    22: "cebra",
    23: "jirafa",
    24: "mochila",
    25: "paraguas",
    26: "bolso",
    27: "corbata",
    28: "maleta",
    29: "frisbee",
    30: "esquís",
    31: "snowboard",
    32: "pelota deportiva",
    33: "cometa",
    34: "bate de béisbol",
    35: "guante de béisbol",
    36: "patineta",
    37: "tabla de surf",
    38: "raqueta de tenis",
    39: "botella",
    40: "copa de vino",
    41: "taza",
    42: "tenedor",
    43: "cuchillo",
    44: "cuchara",
    45: "bowl",
    46: "banana",
    47: "manzana",
    48: "sándwich",
    49: "naranja",
    50: "brócoli",
    51: "zanahoria",
    52: "hot dog",
    53: "pizza",
    54: "dona",
    55: "pastel",
    56: "silla",
    57: "sofá",
    58: "planta en maceta",
    59: "cama",
    60: "mesa de comedor",
    61: "inodoro",
    62: "TV",
    63: "laptop",
    64: "mouse",
    65: "control remoto",
    66: "teclado",
    67: "celular",
    68: "microondas",
    69: "horno",
    70: "tostador",
    71: "fregadero",
    72: "refrigerador",
    73: "libro",
    74: "reloj",
    75: "florero",
    76: "tijeras",
    77: "oso de peluche",
    78: "secador de pelo",
    79: "cepillo de dientes",
}


def _env_video_source() -> VideoSourceType:
    """Obtiene fuente de video por defecto desde variables de entorno"""
    env_value = os.getenv("VM_VIDEO_SOURCE", "").lower()
    try:
        return VideoSourceType(env_value) if env_value else VideoSourceType.WEBCAM
    except ValueError:
        return VideoSourceType.WEBCAM


def _env_model_size() -> ModelSize:
    """Mapea nombre corto a modelo YOLO"""
    env_value = os.getenv("VM_MODEL_SIZE", "").lower()
    alias_map = {
        "nano": ModelSize.NANO,
        "small": ModelSize.SMALL,
        "medium": ModelSize.MEDIUM,
        "large": ModelSize.LARGE,
        "xlarge": ModelSize.XLARGE,
    }
    if env_value in alias_map:
        return alias_map[env_value]
    try:
        return ModelSize(env_value)
    except ValueError:
        return ModelSize.NANO


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


# Configuración por defecto global con soporte de variables de entorno
DEFAULT_CONFIG = DetectionConfig(
    video_source=_env_video_source(),
    webcam_index=_env_int("VM_WEBCAM_INDEX", 0),
    ip_camera_url=os.getenv("VM_IP_CAMERA_URL", ""),
    model_size=_env_model_size(),
)
