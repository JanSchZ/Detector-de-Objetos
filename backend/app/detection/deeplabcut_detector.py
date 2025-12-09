"""
DeepLabCut Detector for Argos Pro.
Integrates DeepLabCut's SuperAnimal models for high-accuracy animal pose estimation.
"""
import numpy as np
import time
from typing import Any

from .base_detector import (
    BaseDetector,
    BackendCapabilities,
    BackendType,
    TargetType,
    Detection,
    DetectionResult,
    Keypoint,
)


# SuperAnimal model configurations
SUPERANIMAL_MODELS = {
    "superanimal_quadruped": {
        "name": "SuperAnimal-Quadruped",
        "keypoints": 39,
        "targets": [TargetType.QUADRUPED],
        "description": "Dogs, cats, horses, and other four-legged animals",
    },
    "superanimal_bird": {
        "name": "SuperAnimal-Bird",
        "keypoints": 24,
        "targets": [TargetType.BIRD],
        "description": "Various bird species",
    },
    "superanimal_topviewmouse": {
        "name": "SuperAnimal-TopViewMouse",
        "keypoints": 12,
        "targets": [TargetType.RODENT],
        "description": "Lab mice viewed from above",
    },
}

# Quadruped keypoint names (39 keypoints from SuperAnimal)
QUADRUPED_KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_earbase", "right_earbase",
    "left_earend", "right_earend", "throat", "withers", "tailbase",
    "left_front_elbow", "right_front_elbow", "left_front_knee", "right_front_knee",
    "left_front_paw", "right_front_paw", "left_back_elbow", "right_back_elbow",
    "left_back_knee", "right_back_knee", "left_back_paw", "right_back_paw",
    # Additional points for detailed pose
    "neck", "spine_mid", "spine_back", "tail_mid", "tail_end",
    "left_shoulder", "right_shoulder", "left_hip", "right_hip",
    "chin", "left_whisker", "right_whisker", "chest", "belly",
    "left_rear_paw", "right_rear_paw", "snout", "forehead",
]


class DeepLabCutDetector(BaseDetector):
    """
    DeepLabCut detector using SuperAnimal pre-trained models.
    
    Features:
    - Zero-shot animal pose estimation (no training required)
    - High accuracy keypoint detection
    - Supports quadrupeds, birds, and rodents
    
    Note: DeepLabCut is optional. Install with: pip install deeplabcut[tf]
    """
    
    def __init__(self):
        self._model = None
        self._model_name: str | None = None
        self._dlc_available = self._check_dlc_available()
        
    def _check_dlc_available(self) -> bool:
        """Check if DeepLabCut is installed"""
        try:
            import deeplabcut
            return True
        except ImportError:
            print("⚠️ DeepLabCut not installed. Install with: pip install deeplabcut[tf]")
            return False
    
    def get_capabilities(self) -> BackendCapabilities:
        """Return DeepLabCut backend capabilities"""
        return BackendCapabilities(
            backend_type=BackendType.DEEPLABCUT,
            supports_pose=True,
            supports_tracking=True,
            supports_3d=False,
            supports_multi_animal=True,
            max_fps=15,  # DLC is slower but more accurate
            supported_targets=[
                TargetType.QUADRUPED,
                TargetType.BIRD,
                TargetType.RODENT,
            ],
            requires_gpu=True,  # GPU recommended for reasonable speed
        )
    
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded"""
        return self._model is not None
    
    def load_model(self, model_name: str = "superanimal_quadruped", **kwargs) -> None:
        """
        Load a SuperAnimal model.
        
        Args:
            model_name: One of 'superanimal_quadruped', 'superanimal_bird', 
                       'superanimal_topviewmouse', or path to custom model
        """
        if not self._dlc_available:
            raise RuntimeError("DeepLabCut not installed. Run: pip install deeplabcut[tf]")
        
        if self._model_name == model_name and self._model is not None:
            return
        
        print(f"🔄 Loading DeepLabCut model: {model_name}...")
        
        try:
            import deeplabcut
            
            # Load SuperAnimal model from DLC Model Zoo
            if model_name in SUPERANIMAL_MODELS:
                # Use DLC's built-in SuperAnimal models
                self._model = deeplabcut.create_superanimal_project(
                    model_name,
                    "/tmp/dlc_temp_project",
                    videotype="",
                    copy_videos=False,
                )
                self._model_name = model_name
                print(f"✅ Loaded SuperAnimal model: {SUPERANIMAL_MODELS[model_name]['name']}")
            else:
                # Load custom model from path
                self._model = model_name  # Path to config.yaml
                self._model_name = model_name
                print(f"✅ Loaded custom DLC model: {model_name}")
                
        except Exception as e:
            print(f"❌ Failed to load DeepLabCut model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run pose estimation on a frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            DetectionResult with animal detections and keypoints
        """
        if not self._dlc_available:
            return self._empty_result(frame)
        
        if self._model is None:
            self.load_model()
        
        start_time = time.perf_counter()
        
        try:
            import deeplabcut
            
            # Run inference
            # DLC returns DataFrame with columns: bodypart, x, y, likelihood
            poses = deeplabcut.analyze_image(
                self._model,
                frame,
                shuffle=1,
                trainingsetindex=0,
            )
            
            detections = self._process_poses(poses, frame.shape)
            
        except Exception as e:
            print(f"⚠️ DLC inference error: {e}")
            detections = []
        
        inference_time = (time.perf_counter() - start_time) * 1000
        
        h, w = frame.shape[:2]
        return DetectionResult(
            detections=detections,
            inference_time_ms=inference_time,
            frame_width=w,
            frame_height=h,
            backend_type=BackendType.DEEPLABCUT,
        )
    
    def _process_poses(
        self,
        poses: Any,  # pd.DataFrame
        frame_shape: tuple,
    ) -> list[Detection]:
        """Process DLC pose output into Detection objects"""
        detections = []
        
        try:
            import pandas as pd
            
            if poses is None or (isinstance(poses, pd.DataFrame) and poses.empty):
                return []
            
            # DLC output format varies by model; handle common cases
            # For SuperAnimal models, output is typically:
            # MultiIndex columns: (scorer, bodypart, x/y/likelihood)
            
            # Group keypoints by individual (for multi-animal)
            individuals = poses.columns.get_level_values(0).unique() if hasattr(poses.columns, 'get_level_values') else ['individual0']
            
            for individual in individuals:
                try:
                    if hasattr(poses.columns, 'get_level_values'):
                        individual_data = poses[individual]
                    else:
                        individual_data = poses
                    
                    keypoints = []
                    valid_keypoints = 0
                    min_x, min_y = float('inf'), float('inf')
                    max_x, max_y = 0, 0
                    
                    # Extract keypoints
                    bodyparts = individual_data.columns.get_level_values(0).unique() if hasattr(individual_data.columns, 'get_level_values') else []
                    
                    for bp_idx, bodypart in enumerate(bodyparts):
                        try:
                            if hasattr(individual_data[bodypart], 'x'):
                                x = float(individual_data[bodypart]['x'].iloc[0])
                                y = float(individual_data[bodypart]['y'].iloc[0])
                                likelihood = float(individual_data[bodypart]['likelihood'].iloc[0])
                            else:
                                x = float(individual_data[bodypart].iloc[0, 0])
                                y = float(individual_data[bodypart].iloc[0, 1])
                                likelihood = float(individual_data[bodypart].iloc[0, 2])
                            
                            if likelihood > 0.3:
                                keypoints.append(Keypoint(
                                    x=int(x),
                                    y=int(y),
                                    confidence=likelihood,
                                    name=str(bodypart),
                                ))
                                valid_keypoints += 1
                                min_x = min(min_x, x)
                                min_y = min(min_y, y)
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)
                        except Exception:
                            continue
                    
                    # Only create detection if we have enough keypoints
                    if valid_keypoints >= 5:
                        # Create bounding box from keypoints
                        padding = 20
                        bbox = (
                            max(0, int(min_x - padding)),
                            max(0, int(min_y - padding)),
                            min(frame_shape[1], int(max_x + padding)),
                            min(frame_shape[0], int(max_y + padding)),
                        )
                        
                        # Average confidence
                        avg_conf = sum(kp.confidence for kp in keypoints) / len(keypoints)
                        
                        detections.append(Detection(
                            class_id=16,  # COCO 'dog' as placeholder for quadruped
                            class_name="animal",
                            class_name_es="animal",
                            confidence=avg_conf,
                            bbox=bbox,
                            keypoints=keypoints,
                            backend_source=BackendType.DEEPLABCUT,
                        ))
                        
                except Exception as e:
                    print(f"⚠️ Error processing individual {individual}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error processing poses: {e}")
        
        return detections
    
    def _empty_result(self, frame: np.ndarray) -> DetectionResult:
        """Return empty result when DLC not available"""
        h, w = frame.shape[:2]
        return DetectionResult(
            detections=[],
            inference_time_ms=0,
            frame_width=w,
            frame_height=h,
            backend_type=BackendType.DEEPLABCUT,
        )
    
    def cleanup(self) -> None:
        """Release DeepLabCut resources"""
        self._model = None
        self._model_name = None
