"""
Fusion Engine for Argos Pro.
Runs multiple detection backends in parallel and intelligently merges results.
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import numpy as np

from .base_detector import (
    BaseDetector,
    Detection,
    DetectionResult,
    FusedDetectionResult,
    BackendType,
    Keypoint,
)


class FusionStrategy(str, Enum):
    """Strategies for combining results from multiple backends"""
    CONSENSUS = "consensus"      # Only report if 2+ backends agree
    CASCADE = "cascade"          # Fast detector → refined pose
    PARALLEL_MERGE = "parallel"  # Merge all unique detections
    WEIGHTED = "weighted"        # Weight by backend confidence/reliability
    FIRST_WINS = "first_wins"    # Use first backend's result, others validate


@dataclass
class FusionConfig:
    """Configuration for how to merge multi-backend results"""
    strategy: FusionStrategy = FusionStrategy.PARALLEL_MERGE
    min_backends_agree: int = 1  # Minimum backends that must detect something
    iou_threshold: float = 0.5   # IoU threshold for matching detections
    prefer_pose_from: BackendType | None = None  # Prefer keypoints from this backend
    confidence_aggregation: str = "max"  # max, mean, min
    backend_weights: dict[BackendType, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "min_backends_agree": self.min_backends_agree,
            "iou_threshold": self.iou_threshold,
            "prefer_pose_from": self.prefer_pose_from.value if self.prefer_pose_from else None,
            "confidence_aggregation": self.confidence_aggregation,
            "backend_weights": {k.value: v for k, v in self.backend_weights.items()},
        }


class FusionEngine:
    """
    Runs multiple detection backends in parallel and fuses their results.
    
    Benefits of multi-backend fusion:
    - Consensus voting reduces false positives
    - Cascade combines speed (YOLO) with precision (DeepLabCut)
    - Parallel merge maximizes detection coverage
    - Weighted fusion leverages each backend's strengths
    """
    
    def __init__(self, config: FusionConfig | None = None):
        self.config = config or FusionConfig()
    
    def update_config(self, config: FusionConfig) -> None:
        """Update fusion configuration"""
        self.config = config
    
    async def process_parallel(
        self,
        frame: np.ndarray,
        backends: dict[str, BaseDetector],
    ) -> FusedDetectionResult:
        """
        Run all backends concurrently and fuse results.
        
        Args:
            frame: BGR image as numpy array
            backends: Dict of backend_id -> BaseDetector instances
            
        Returns:
            FusedDetectionResult with merged detections
        """
        if not backends:
            h, w = frame.shape[:2]
            return FusedDetectionResult(
                detections=[],
                inference_time_ms=0,
                frame_width=w,
                frame_height=h,
                backends_used=[],
                fusion_strategy=self.config.strategy.value,
            )
        
        import time
        start_time = time.perf_counter()
        
        # Execute all backends in parallel
        tasks = {
            backend_id: asyncio.create_task(backend.detect_async(frame))
            for backend_id, backend in backends.items()
        }
        
        results: dict[str, DetectionResult] = {}
        for backend_id, task in tasks.items():
            try:
                results[backend_id] = await task
            except Exception as e:
                print(f"⚠️ Backend {backend_id} failed: {e}")
                continue
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Apply fusion strategy
        match self.config.strategy:
            case FusionStrategy.CONSENSUS:
                fused_detections = self._consensus_fusion(results)
            case FusionStrategy.CASCADE:
                fused_detections = self._cascade_fusion(results)
            case FusionStrategy.PARALLEL_MERGE:
                fused_detections = self._parallel_merge(results)
            case FusionStrategy.WEIGHTED:
                fused_detections = self._weighted_fusion(results)
            case FusionStrategy.FIRST_WINS:
                fused_detections = self._first_wins_fusion(results)
            case _:
                fused_detections = self._parallel_merge(results)
        
        h, w = frame.shape[:2]
        backends_used = [r.backend_type for r in results.values()]
        
        return FusedDetectionResult(
            detections=fused_detections,
            inference_time_ms=total_time,
            frame_width=w,
            frame_height=h,
            backends_used=backends_used,
            fusion_strategy=self.config.strategy.value,
            individual_results=list(results.values()),
        )
    
    def _calculate_iou(self, box1: tuple, box2: tuple) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _match_detections(
        self,
        detections1: list[Detection],
        detections2: list[Detection],
    ) -> list[tuple[Detection | None, Detection | None]]:
        """
        Match detections from two backends using IoU.
        Returns list of (det1, det2) pairs. None means no match.
        """
        matched: list[tuple[Detection | None, Detection | None]] = []
        used2: set[int] = set()
        
        for det1 in detections1:
            best_match = None
            best_iou = self.config.iou_threshold
            best_idx = -1
            
            for idx, det2 in enumerate(detections2):
                if idx in used2:
                    continue
                if det1.class_id != det2.class_id:
                    continue
                
                iou = self._calculate_iou(det1.bbox, det2.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_match = det2
                    best_idx = idx
            
            if best_match:
                matched.append((det1, best_match))
                used2.add(best_idx)
            else:
                matched.append((det1, None))
        
        # Add unmatched from detections2
        for idx, det2 in enumerate(detections2):
            if idx not in used2:
                matched.append((None, det2))
        
        return matched
    
    def _merge_keypoints(
        self,
        det1: Detection | None,
        det2: Detection | None,
    ) -> list[Keypoint]:
        """
        Merge keypoints from two detections.
        Prefers keypoints from the backend specified in config.
        """
        if det1 is None:
            return det2.keypoints if det2 else []
        if det2 is None:
            return det1.keypoints
        
        # Prefer keypoints from specified backend
        if self.config.prefer_pose_from:
            if det1.backend_source == self.config.prefer_pose_from and det1.keypoints:
                return det1.keypoints
            if det2.backend_source == self.config.prefer_pose_from and det2.keypoints:
                return det2.keypoints
        
        # Otherwise prefer the one with more keypoints
        if len(det1.keypoints) >= len(det2.keypoints):
            return det1.keypoints
        return det2.keypoints
    
    def _aggregate_confidence(self, conf1: float, conf2: float) -> float:
        """Aggregate confidence scores based on config"""
        match self.config.confidence_aggregation:
            case "max":
                return max(conf1, conf2)
            case "min":
                return min(conf1, conf2)
            case "mean":
                return (conf1 + conf2) / 2
            case _:
                return max(conf1, conf2)
    
    def _consensus_fusion(
        self,
        results: dict[str, DetectionResult],
    ) -> list[Detection]:
        """
        Only include detections confirmed by multiple backends.
        Reduces false positives.
        """
        if len(results) < 2:
            # With only one backend, just return its detections
            for result in results.values():
                return result.detections
            return []
        
        # Collect all detections with their source
        all_detections: list[tuple[Detection, str]] = []
        for backend_id, result in results.items():
            for det in result.detections:
                det.backend_source = result.backend_type
                all_detections.append((det, backend_id))
        
        # Group detections by matching them across backends
        consensus_detections: list[Detection] = []
        used: set[int] = set()
        
        for i, (det1, backend1) in enumerate(all_detections):
            if i in used:
                continue
            
            matching_count = 1
            matching_dets = [det1]
            
            for j, (det2, backend2) in enumerate(all_detections):
                if j <= i or j in used or backend1 == backend2:
                    continue
                
                if det1.class_id == det2.class_id:
                    iou = self._calculate_iou(det1.bbox, det2.bbox)
                    if iou >= self.config.iou_threshold:
                        matching_count += 1
                        matching_dets.append(det2)
                        used.add(j)
            
            # Only include if enough backends agree
            if matching_count >= self.config.min_backends_agree:
                # Create merged detection
                avg_conf = sum(d.confidence for d in matching_dets) / len(matching_dets)
                merged = Detection(
                    class_id=det1.class_id,
                    class_name=det1.class_name,
                    class_name_es=det1.class_name_es,
                    confidence=avg_conf,
                    bbox=det1.bbox,
                    keypoints=self._merge_keypoints(matching_dets[0], matching_dets[1] if len(matching_dets) > 1 else None),
                    tracker_id=det1.tracker_id,
                    backend_source=BackendType.YOLO,  # Fused
                )
                consensus_detections.append(merged)
                used.add(i)
        
        return consensus_detections
    
    def _cascade_fusion(
        self,
        results: dict[str, DetectionResult],
    ) -> list[Detection]:
        """
        Use fast detector (YOLO) for bounding boxes, 
        then refine pose with accurate detector (DeepLabCut).
        """
        # Find YOLO result for bounding boxes
        yolo_result = None
        pose_result = None
        
        for result in results.values():
            if result.backend_type == BackendType.YOLO:
                yolo_result = result
            elif result.backend_type in (BackendType.DEEPLABCUT, BackendType.SLEAP):
                pose_result = result
        
        if not yolo_result:
            # Fall back to first available
            for result in results.values():
                return result.detections
            return []
        
        if not pose_result:
            return yolo_result.detections
        
        # Match YOLO detections with pose results and merge
        fused: list[Detection] = []
        matches = self._match_detections(yolo_result.detections, pose_result.detections)
        
        for yolo_det, pose_det in matches:
            if yolo_det is None and pose_det is None:
                continue
            
            if yolo_det is None:
                # Only pose detected, keep it
                fused.append(pose_det)
            elif pose_det is None:
                # Only YOLO detected, keep it
                fused.append(yolo_det)
            else:
                # Both detected - use YOLO bbox, pose keypoints
                merged = Detection(
                    class_id=yolo_det.class_id,
                    class_name=yolo_det.class_name,
                    class_name_es=yolo_det.class_name_es,
                    confidence=self._aggregate_confidence(yolo_det.confidence, pose_det.confidence),
                    bbox=yolo_det.bbox,
                    keypoints=pose_det.keypoints if pose_det.keypoints else yolo_det.keypoints,
                    tracker_id=yolo_det.tracker_id or pose_det.tracker_id,
                    backend_source=BackendType.YOLO,  # Primary source
                )
                fused.append(merged)
        
        return fused
    
    def _parallel_merge(
        self,
        results: dict[str, DetectionResult],
    ) -> list[Detection]:
        """
        Merge all detections, deduplicating by IoU.
        Maximizes coverage - if any backend sees it, include it.
        """
        all_detections: list[Detection] = []
        
        for result in results.values():
            for det in result.detections:
                det.backend_source = result.backend_type
                all_detections.append(det)
        
        if not all_detections:
            return []
        
        # Deduplicate by IoU
        merged: list[Detection] = []
        used: set[int] = set()
        
        for i, det1 in enumerate(all_detections):
            if i in used:
                continue
            
            # Find all matching detections
            group = [det1]
            for j, det2 in enumerate(all_detections):
                if j <= i or j in used:
                    continue
                if det1.class_id == det2.class_id:
                    iou = self._calculate_iou(det1.bbox, det2.bbox)
                    if iou >= self.config.iou_threshold:
                        group.append(det2)
                        used.add(j)
            
            # Merge the group
            if len(group) == 1:
                merged.append(det1)
            else:
                # Use highest confidence detection as base
                best = max(group, key=lambda d: d.confidence)
                best.keypoints = self._merge_keypoints(group[0], group[1] if len(group) > 1 else None)
                best.confidence = max(d.confidence for d in group)
                merged.append(best)
            
            used.add(i)
        
        return merged
    
    def _weighted_fusion(
        self,
        results: dict[str, DetectionResult],
    ) -> list[Detection]:
        """
        Weight detections by backend reliability.
        Useful when some backends are more accurate for specific classes.
        """
        # For now, use default weights
        default_weights = {
            BackendType.YOLO: 1.0,
            BackendType.DEEPLABCUT: 1.2,  # Higher weight for precision
            BackendType.SLEAP: 1.1,
        }
        
        weights = self.config.backend_weights or default_weights
        
        # Apply weights to confidences
        all_detections: list[Detection] = []
        for result in results.values():
            weight = weights.get(result.backend_type, 1.0)
            for det in result.detections:
                det.confidence = min(1.0, det.confidence * weight)
                det.backend_source = result.backend_type
                all_detections.append(det)
        
        # Then merge like parallel
        return self._parallel_merge({"weighted": DetectionResult(
            detections=all_detections,
            inference_time_ms=0,
            frame_width=0,
            frame_height=0,
            backend_type=BackendType.YOLO,
        )})
    
    def _first_wins_fusion(
        self,
        results: dict[str, DetectionResult],
    ) -> list[Detection]:
        """
        Use first backend's detections, others just validate.
        Fast but less accurate.
        """
        for result in results.values():
            # Tag all detections with source
            for det in result.detections:
                det.backend_source = result.backend_type
            return result.detections
        return []
