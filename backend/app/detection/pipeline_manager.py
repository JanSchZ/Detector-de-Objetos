"""
Pipeline Manager for Argos.
Central orchestrator that manages detection backends and presets.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any
import numpy as np

from .base_detector import (
    BaseDetector,
    BackendType,
    BackendCapabilities,
    DetectionResult,
    FusedDetectionResult,
    TargetType,
)
from .fusion_engine import FusionEngine, FusionConfig, FusionStrategy


@dataclass
class BackendInstance:
    """Represents a configured and loaded backend"""
    backend_id: str
    backend_type: BackendType
    detector: BaseDetector
    enabled: bool = True
    model_name: str = ""
    config: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "backend_type": self.backend_type.value,
            "enabled": self.enabled,
            "model_name": self.model_name,
            "capabilities": self.detector.get_capabilities().to_dict(),
        }


@dataclass
class PipelinePreset:
    """Pre-configured pipeline setup for common use cases"""
    id: str
    name: str
    description: str
    icon: str
    backends: list[dict]
    fusion: FusionConfig
    features: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "backends": self.backends,
            "fusion": self.fusion.to_dict(),
            "features": self.features,
        }


# Pre-defined presets
PRESETS: dict[str, PipelinePreset] = {
    "home_security": PipelinePreset(
        id="home_security",
        name="🏠 Seguridad del Hogar",
        description="Detecta personas y mascotas, alertas de intrusión",
        icon="🏠",
        backends=[
            {"type": "yolo", "model": "yolo11n.pt", "targets": ["person", "dog", "cat"]},
        ],
        fusion=FusionConfig(strategy=FusionStrategy.FIRST_WINS),
        features={
            "intrusion_alerts": True,
            "zone_monitoring": True,
            "pose_estimation": False,
        }
    ),
    "pet_monitor": PipelinePreset(
        id="pet_monitor",
        name="🐕 Monitor de Mascotas",
        description="Tracking detallado de mascotas con esqueleto",
        icon="🐕",
        backends=[
            {"type": "yolo", "model": "yolo11n.pt", "targets": ["dog", "cat"]},
            {"type": "deeplabcut", "model": "superanimal_quadruped"},
        ],
        fusion=FusionConfig(
            strategy=FusionStrategy.CASCADE,
            prefer_pose_from=BackendType.DEEPLABCUT
        ),
        features={
            "skeleton_overlay": True,
            "behavior_analysis": True,
            "activity_tracking": True,
        }
    ),
    "high_precision": PipelinePreset(
        id="high_precision",
        name="🎯 Alta Precisión",
        description="Máxima precisión combinando múltiples backends",
        icon="🎯",
        backends=[
            {"type": "yolo", "model": "yolo11m.pt"},
            {"type": "deeplabcut", "model": "superanimal_quadruped"},
        ],
        fusion=FusionConfig(
            strategy=FusionStrategy.CONSENSUS,
            min_backends_agree=2,
            confidence_aggregation="mean",
        ),
        features={
            "dual_verification": True,
            "reduce_false_positives": True,
        }
    ),
    "lab_research": PipelinePreset(
        id="lab_research",
        name="🧪 Investigación de Laboratorio",
        description="Multi-animal tracking de alta velocidad",
        icon="🧪",
        backends=[
            {"type": "sleap", "model": "custom_trained"},
        ],
        fusion=FusionConfig(strategy=FusionStrategy.FIRST_WINS),
        features={
            "multi_animal": True,
            "trajectory_export": True,
            "frame_by_frame": True,
        }
    ),
    "wildlife": PipelinePreset(
        id="wildlife",
        name="🦁 Vida Silvestre",
        description="Detección + pose de animales salvajes",
        icon="🦁",
        backends=[
            {"type": "yolo", "model": "yolo11n.pt", "targets": ["bird", "bear", "elephant", "zebra", "giraffe"]},
            {"type": "deeplabcut", "model": "superanimal_quadruped"},
        ],
        fusion=FusionConfig(
            strategy=FusionStrategy.PARALLEL_MERGE,
            prefer_pose_from=BackendType.DEEPLABCUT,
        ),
        features={
            "species_identification": True,
            "pose_estimation": True,
        }
    ),
    "industrial": PipelinePreset(
        id="industrial",
        name="🏭 Industrial",
        description="Detección de objetos y seguridad laboral",
        icon="🏭",
        backends=[
            {"type": "yolo", "model": "yolo11m.pt"},
        ],
        fusion=FusionConfig(strategy=FusionStrategy.FIRST_WINS),
        features={
            "ppe_detection": True,
            "safety_zones": True,
            "vehicle_tracking": True,
        }
    ),
    "custom": PipelinePreset(
        id="custom",
        name="⚙️ Personalizado",
        description="Configuración manual de backends",
        icon="⚙️",
        backends=[],
        fusion=FusionConfig(strategy=FusionStrategy.PARALLEL_MERGE),
        features={},
    ),
}


class PipelineManager:
    """
    Central manager for detection pipelines.
    
    Handles:
    - Loading and configuring multiple detection backends
    - Applying presets for common use cases
    - Coordinating parallel detection with FusionEngine
    - Hot-swapping backends without restart
    """
    
    def __init__(self):
        self._backends: dict[str, BackendInstance] = {}
        self._fusion_engine = FusionEngine()
        self._active_preset: str | None = None
        self._backend_counter = 0
    
    @property
    def active_preset(self) -> str | None:
        """Get the currently active preset ID"""
        return self._active_preset
    
    @property
    def backends(self) -> dict[str, BackendInstance]:
        """Get all registered backends"""
        return self._backends
    
    def get_available_presets(self) -> list[dict]:
        """Get list of all available presets"""
        return [preset.to_dict() for preset in PRESETS.values()]
    
    def get_preset(self, preset_id: str) -> PipelinePreset | None:
        """Get a specific preset by ID"""
        return PRESETS.get(preset_id)
    
    async def apply_preset(self, preset_id: str) -> bool:
        """
        Apply a preset configuration.
        Loads/unloads backends as needed.
        """
        preset = PRESETS.get(preset_id)
        if not preset:
            print(f"❌ Preset '{preset_id}' not found")
            return False
        
        print(f"🔄 Applying preset: {preset.name}")
        
        # Clear existing backends
        await self.clear_all_backends()
        
        # Configure fusion engine
        self._fusion_engine.update_config(preset.fusion)
        
        # Load backends specified in preset
        for backend_config in preset.backends:
            backend_type = BackendType(backend_config["type"])
            model_name = backend_config.get("model", "")
            
            await self.add_backend(
                backend_type=backend_type,
                model_name=model_name,
                config=backend_config,
            )
        
        self._active_preset = preset_id
        print(f"✅ Preset '{preset.name}' applied with {len(self._backends)} backends")
        return True
    
    async def add_backend(
        self,
        backend_type: BackendType,
        model_name: str = "",
        config: dict | None = None,
    ) -> str:
        """
        Add and configure a new detection backend.
        Returns the backend_id.
        """
        self._backend_counter += 1
        backend_id = f"{backend_type.value}_{self._backend_counter}"
        
        # Create detector based on type
        detector = self._create_detector(backend_type)
        if detector is None:
            raise ValueError(f"Backend type '{backend_type}' not supported")
        
        # Load model
        if model_name:
            try:
                detector.load_model(model_name)
            except Exception as e:
                print(f"⚠️ Failed to load model '{model_name}': {e}")
                # Continue with default model
        
        instance = BackendInstance(
            backend_id=backend_id,
            backend_type=backend_type,
            detector=detector,
            enabled=True,
            model_name=model_name,
            config=config or {},
        )
        
        self._backends[backend_id] = instance
        print(f"✅ Added backend: {backend_id} ({model_name or 'default model'})")
        return backend_id
    
    def _create_detector(self, backend_type: BackendType) -> BaseDetector | None:
        """Factory method to create detector instances"""
        match backend_type:
            case BackendType.YOLO:
                from .yolo_detector import YOLODetector
                return YOLODetector()
            case BackendType.DEEPLABCUT:
                try:
                    from .deeplabcut_detector import DeepLabCutDetector
                    return DeepLabCutDetector()
                except ImportError:
                    print("⚠️ DeepLabCut not installed. Run: pip install deeplabcut")
                    return None
            case BackendType.SLEAP:
                try:
                    from .sleap_detector import SLEAPDetector
                    return SLEAPDetector()
                except ImportError:
                    print("⚠️ SLEAP not installed. Run: pip install sleap")
                    return None
            case _:
                return None
    
    def remove_backend(self, backend_id: str) -> bool:
        """Remove a backend by ID"""
        if backend_id in self._backends:
            instance = self._backends.pop(backend_id)
            instance.detector.cleanup()
            print(f"🗑️ Removed backend: {backend_id}")
            return True
        return False
    
    def enable_backend(self, backend_id: str, enabled: bool = True) -> bool:
        """Enable or disable a backend"""
        if backend_id in self._backends:
            self._backends[backend_id].enabled = enabled
            status = "enabled" if enabled else "disabled"
            print(f"{'✅' if enabled else '⏸️'} Backend {backend_id} {status}")
            return True
        return False
    
    async def clear_all_backends(self) -> None:
        """Remove all backends"""
        for backend_id in list(self._backends.keys()):
            self.remove_backend(backend_id)
        self._backends.clear()
    
    def get_active_backends(self) -> dict[str, BaseDetector]:
        """Get only enabled backends"""
        return {
            bid: instance.detector
            for bid, instance in self._backends.items()
            if instance.enabled
        }
    
    async def process_frame(self, frame: np.ndarray) -> FusedDetectionResult:
        """
        Process a frame through all active backends.
        Returns fused detection result.
        """
        active = self.get_active_backends()
        return await self._fusion_engine.process_parallel(frame, active)
    
    def process_frame_sync(self, frame: np.ndarray) -> FusedDetectionResult:
        """Synchronous version for compatibility"""
        return asyncio.run(self.process_frame(frame))
    
    def get_combined_capabilities(self) -> dict[str, Any]:
        """Get combined capabilities of all active backends"""
        active = self.get_active_backends()
        
        if not active:
            return {
                "supports_pose": False,
                "supports_tracking": False,
                "supports_3d": False,
                "supports_multi_animal": False,
                "max_fps": 0,
                "supported_targets": [],
                "backends_count": 0,
            }
        
        # Aggregate capabilities
        caps = [d.get_capabilities() for d in active.values()]
        
        return {
            "supports_pose": any(c.supports_pose for c in caps),
            "supports_tracking": any(c.supports_tracking for c in caps),
            "supports_3d": any(c.supports_3d for c in caps),
            "supports_multi_animal": any(c.supports_multi_animal for c in caps),
            "max_fps": min(c.max_fps for c in caps) if caps else 0,
            "supported_targets": list(set(
                t.value for c in caps for t in c.supported_targets
            )),
            "backends_count": len(active),
            "backends": [
                {"id": bid, "type": self._backends[bid].backend_type.value}
                for bid in active.keys()
            ],
        }
    
    def get_fusion_config(self) -> FusionConfig:
        """Get current fusion configuration"""
        return self._fusion_engine.config
    
    def update_fusion_config(self, config: FusionConfig) -> None:
        """Update fusion configuration"""
        self._fusion_engine.update_config(config)
    
    def get_status(self) -> dict[str, Any]:
        """Get full pipeline status"""
        return {
            "active_preset": self._active_preset,
            "backends": [
                instance.to_dict() for instance in self._backends.values()
            ],
            "fusion": self._fusion_engine.config.to_dict(),
            "capabilities": self.get_combined_capabilities(),
        }


# Global pipeline manager instance
_pipeline_manager: PipelineManager | None = None


def get_pipeline_manager() -> PipelineManager:
    """Get or create the global pipeline manager"""
    global _pipeline_manager
    if _pipeline_manager is None:
        _pipeline_manager = PipelineManager()
    return _pipeline_manager
