"""
Pipeline API routes for Argos Pro.
Manages detection backends, presets, and fusion configuration.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.detection import (
    get_pipeline_manager,
    BackendType,
    FusionStrategy,
    FusionConfig,
    PRESETS,
)


router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


# Request/Response Models
class ApplyPresetRequest(BaseModel):
    preset_id: str = Field(..., description="Preset ID to apply")


class AddBackendRequest(BaseModel):
    backend_type: str = Field(..., description="Backend type: yolo, deeplabcut, sleap")
    model_name: str = Field(default="", description="Model name or path")
    config: dict = Field(default_factory=dict, description="Backend-specific config")


class UpdateFusionRequest(BaseModel):
    strategy: str = Field(default="parallel", description="Fusion strategy")
    min_backends_agree: int = Field(default=1, ge=1)
    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    prefer_pose_from: str | None = Field(default=None)
    confidence_aggregation: str = Field(default="max")


class EnableBackendRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable backend")


# Endpoints
@router.get("/status")
async def get_pipeline_status() -> dict[str, Any]:
    """Get full pipeline status including backends and capabilities"""
    manager = get_pipeline_manager()
    return manager.get_status()


@router.get("/presets")
async def list_presets() -> list[dict[str, Any]]:
    """List all available presets"""
    manager = get_pipeline_manager()
    return manager.get_available_presets()


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str) -> dict[str, Any]:
    """Get details of a specific preset"""
    preset = PRESETS.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return preset.to_dict()


@router.post("/presets/{preset_id}/apply")
async def apply_preset(preset_id: str) -> dict[str, Any]:
    """Apply a preset configuration"""
    manager = get_pipeline_manager()
    
    success = await manager.apply_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    
    return {
        "success": True,
        "preset": preset_id,
        "status": manager.get_status(),
    }


@router.get("/backends")
async def list_backends() -> list[dict[str, Any]]:
    """List all registered backends"""
    manager = get_pipeline_manager()
    return [instance.to_dict() for instance in manager.backends.values()]


@router.post("/backends")
async def add_backend(request: AddBackendRequest) -> dict[str, Any]:
    """Add a new detection backend"""
    manager = get_pipeline_manager()
    
    try:
        backend_type = BackendType(request.backend_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backend type: {request.backend_type}. Valid: yolo, deeplabcut, sleap"
        )
    
    try:
        backend_id = await manager.add_backend(
            backend_type=backend_type,
            model_name=request.model_name,
            config=request.config,
        )
        
        return {
            "success": True,
            "backend_id": backend_id,
            "backend": manager.backends[backend_id].to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backends/{backend_id}")
async def remove_backend(backend_id: str) -> dict[str, Any]:
    """Remove a backend by ID"""
    manager = get_pipeline_manager()
    
    if backend_id not in manager.backends:
        raise HTTPException(status_code=404, detail=f"Backend '{backend_id}' not found")
    
    manager.remove_backend(backend_id)
    return {"success": True, "removed": backend_id}


@router.patch("/backends/{backend_id}/enable")
async def toggle_backend(backend_id: str, request: EnableBackendRequest) -> dict[str, Any]:
    """Enable or disable a backend"""
    manager = get_pipeline_manager()
    
    if backend_id not in manager.backends:
        raise HTTPException(status_code=404, detail=f"Backend '{backend_id}' not found")
    
    manager.enable_backend(backend_id, request.enabled)
    return {
        "success": True,
        "backend_id": backend_id,
        "enabled": request.enabled,
    }


@router.get("/capabilities")
async def get_capabilities() -> dict[str, Any]:
    """Get combined capabilities of all active backends"""
    manager = get_pipeline_manager()
    return manager.get_combined_capabilities()


@router.get("/fusion")
async def get_fusion_config() -> dict[str, Any]:
    """Get current fusion configuration"""
    manager = get_pipeline_manager()
    return manager.get_fusion_config().to_dict()


@router.put("/fusion")
async def update_fusion_config(request: UpdateFusionRequest) -> dict[str, Any]:
    """Update fusion configuration"""
    manager = get_pipeline_manager()
    
    try:
        strategy = FusionStrategy(request.strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {request.strategy}. Valid: consensus, cascade, parallel, weighted, first_wins"
        )
    
    prefer_pose = None
    if request.prefer_pose_from:
        try:
            prefer_pose = BackendType(request.prefer_pose_from)
        except ValueError:
            pass
    
    config = FusionConfig(
        strategy=strategy,
        min_backends_agree=request.min_backends_agree,
        iou_threshold=request.iou_threshold,
        prefer_pose_from=prefer_pose,
        confidence_aggregation=request.confidence_aggregation,
    )
    
    manager.update_fusion_config(config)
    return {
        "success": True,
        "fusion": config.to_dict(),
    }


@router.post("/clear")
async def clear_all_backends() -> dict[str, Any]:
    """Remove all backends"""
    manager = get_pipeline_manager()
    await manager.clear_all_backends()
    return {"success": True, "message": "All backends cleared"}
