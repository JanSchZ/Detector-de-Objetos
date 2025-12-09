"""
Base Detector Interface for Argos.
Defines abstract base class that all detection backends must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import numpy as np
import time


class BackendType(str, Enum):
    """Available detection backend types"""
    YOLO = "yolo"
    DEEPLABCUT = "deeplabcut"
    SLEAP = "sleap"


class TargetType(str, Enum):
    """Types of subjects the detector can track"""
    HUMAN = "human"
    QUADRUPED = "quadruped"  # Dogs, cats, horses, etc.
    BIRD = "bird"
    RODENT = "rodent"  # Mice, rats (lab animals)
    CUSTOM = "custom"


class BackendRole(str, Enum):
    """Role of a backend in a multi-backend pipeline"""
    PRIMARY = "primary"  # Main detector
    POSE_REFINER = "pose_refiner"  # Refines pose from primary detector
    VALIDATOR = "validator"  # Validates detections from other backends


@dataclass
class BackendCapabilities:
    """Describes what a detection backend can do"""
    backend_type: BackendType
    supports_pose: bool
    supports_tracking: bool
    supports_3d: bool
    supports_multi_animal: bool
    max_fps: int
    supported_targets: list[TargetType]
    requires_gpu: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_type": self.backend_type.value,
            "supports_pose": self.supports_pose,
            "supports_tracking": self.supports_tracking,
            "supports_3d": self.supports_3d,
            "supports_multi_animal": self.supports_multi_animal,
            "max_fps": self.max_fps,
            "supported_targets": [t.value for t in self.supported_targets],
            "requires_gpu": self.requires_gpu,
        }


@dataclass
class Keypoint:
    """Represents a single keypoint in pose estimation"""
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
    """Represents a single detection from any backend"""
    class_id: int
    class_name: str
    class_name_es: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    keypoints: list[Keypoint] = field(default_factory=list)
    tracker_id: int | None = None  # For multi-object tracking
    backend_source: BackendType | None = None  # Which backend produced this
    
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
        if self.tracker_id is not None:
            result["tracker_id"] = self.tracker_id
        if self.backend_source:
            result["backend_source"] = self.backend_source.value
        return result


@dataclass
class DetectionResult:
    """Result from a single backend's inference"""
    detections: list[Detection]
    inference_time_ms: float
    frame_width: int
    frame_height: int
    backend_type: BackendType
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict[str, Any]:
        # Count objects by class
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
            "backend": self.backend_type.value,
            "timestamp": self.timestamp,
        }


@dataclass
class FusedDetectionResult:
    """
    Result from multiple backends merged together.
    Contains enhanced detections with higher confidence and better keypoints.
    """
    detections: list[Detection]
    inference_time_ms: float  # Total time for all backends
    frame_width: int
    frame_height: int
    backends_used: list[BackendType]
    fusion_strategy: str
    individual_results: list[DetectionResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict[str, Any]:
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
            "backends_used": [b.value for b in self.backends_used],
            "fusion_strategy": self.fusion_strategy,
            "timestamp": self.timestamp,
        }


class BaseDetector(ABC):
    """
    Abstract base class for all detection backends.
    
    All backends (YOLO, DeepLabCut, SLEAP) must implement this interface
    to work with the PipelineManager and FusionEngine.
    """
    
    @abstractmethod
    def get_capabilities(self) -> BackendCapabilities:
        """Return the capabilities of this backend"""
        ...
    
    @abstractmethod
    def load_model(self, model_name: str, **kwargs) -> None:
        """Load the specified model"""
        ...
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run detection on a single frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            DetectionResult with all detections
        """
        ...
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded"""
        ...
    
    def detect_pose(self, frame: np.ndarray) -> DetectionResult:
        """
        Run pose estimation on a frame.
        Default implementation just calls detect().
        Override in backends that have separate pose models.
        """
        return self.detect(frame)
    
    async def detect_async(self, frame: np.ndarray) -> DetectionResult:
        """
        Async version of detect for parallel execution.
        Default implementation wraps sync detect.
        Override for true async backends.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detect, frame)
    
    def cleanup(self) -> None:
        """Release resources. Override if backend needs cleanup."""
        pass
