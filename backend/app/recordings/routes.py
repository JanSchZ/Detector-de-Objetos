"""
API routes for recordings management.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional

from .storage import get_storage
from .recorder import get_recorder

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


@router.get("")
async def list_recordings(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all recordings with metadata."""
    storage = get_storage()
    
    # Get from database
    recordings = await storage.get_recordings_from_db(limit=limit, offset=offset)
    
    # Get storage stats
    total_size_mb = storage.get_total_size_mb()
    
    return {
        "recordings": recordings,
        "total_size_mb": total_size_mb,
        "max_size_mb": storage.max_storage_mb,
        "max_age_days": storage.max_age_days,
    }


@router.get("/files")
async def list_recording_files():
    """List recording files from filesystem (without database)."""
    storage = get_storage()
    files = storage.list_files()
    
    return {
        "files": files,
        "total": len(files),
        "total_size_mb": storage.get_total_size_mb(),
    }


@router.get("/status")
async def get_recording_status():
    """Get current recording status."""
    recorder = get_recorder()
    
    return {
        "is_recording": recorder.is_recording,
        "buffer_seconds": recorder.pre_seconds,
        "post_seconds": recorder.post_seconds,
        "fps": recorder.fps,
        "recordings_dir": str(recorder.get_recordings_dir()),
    }


@router.get("/{recording_id}")
async def get_recording(recording_id: str):
    """Get recording metadata by ID."""
    storage = get_storage()
    recordings = await storage.get_recordings_from_db(limit=1000)
    
    for rec in recordings:
        if rec["id"] == recording_id:
            return rec
    
    raise HTTPException(status_code=404, detail="Recording not found")


@router.get("/{recording_id}/video")
async def stream_recording_video(recording_id: str):
    """Stream recording video file."""
    storage = get_storage()
    recordings = await storage.get_recordings_from_db(limit=1000)
    
    recording = None
    for rec in recordings:
        if rec["id"] == recording_id:
            recording = rec
            break
    
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not storage.file_exists(recording["filename"]):
        raise HTTPException(status_code=404, detail="Recording file not found")
    
    file_path = storage.get_file_path(recording["filename"])
    
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=recording["filename"],
    )


@router.get("/file/{filename}")
async def stream_recording_by_filename(filename: str):
    """Stream recording video by filename (direct file access)."""
    storage = get_storage()
    
    if not storage.file_exists(filename):
        raise HTTPException(status_code=404, detail="Recording file not found")
    
    file_path = storage.get_file_path(filename)
    
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename,
    )


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a recording by ID."""
    storage = get_storage()
    
    success = await storage.delete_recording_from_db(recording_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {"status": "deleted", "id": recording_id}


@router.post("/cleanup")
async def cleanup_recordings():
    """Run cleanup to remove old and excess recordings."""
    storage = get_storage()
    
    deleted_old = storage.cleanup_old_files()
    deleted_size = storage.cleanup_by_size()
    
    return {
        "status": "completed",
        "deleted_old": deleted_old,
        "deleted_size": deleted_size,
        "total_deleted": deleted_old + deleted_size,
        "current_size_mb": storage.get_total_size_mb(),
    }
