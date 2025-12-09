"""Package init for detection module - Argos Multi-Backend Support"""

# Base detector interface and types
from app.detection.base_detector import (
    BaseDetector,
    BackendType,
    TargetType,
    BackendRole,
    BackendCapabilities,
    Detection,
    DetectionResult,
    FusedDetectionResult,
    Keypoint,
)

# YOLO detector implementation
from app.detection.yolo_detector import (
    YOLODetector,
    SKELETON_CONNECTIONS,
    KEYPOINT_NAMES,
)

# Multi-backend fusion and pipeline management
from app.detection.fusion_engine import (
    FusionEngine,
    FusionStrategy,
    FusionConfig,
)

from app.detection.pipeline_manager import (
    PipelineManager,
    PipelinePreset,
    BackendInstance,
    PRESETS,
    get_pipeline_manager,
)

# Object tracking
from app.detection.tracker import ObjectTracker, TrackedObject, TrackingResult

__all__ = [
    # Base types
    "BaseDetector",
    "BackendType",
    "TargetType",
    "BackendRole",
    "BackendCapabilities",
    "Detection",
    "DetectionResult",
    "FusedDetectionResult",
    "Keypoint",
    # YOLO
    "YOLODetector",
    "SKELETON_CONNECTIONS",
    "KEYPOINT_NAMES",
    # Fusion
    "FusionEngine",
    "FusionStrategy",
    "FusionConfig",
    # Pipeline
    "PipelineManager",
    "PipelinePreset",
    "BackendInstance",
    "PRESETS",
    "get_pipeline_manager",
    # Tracking
    "ObjectTracker",
    "TrackedObject",
    "TrackingResult",
]
