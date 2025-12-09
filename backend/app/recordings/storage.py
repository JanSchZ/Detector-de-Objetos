"""
Recording storage management for Argos.
Handles file storage, cleanup, and database persistence.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from app.database import get_db_context
from app.models import RecordingModel


class RecordingStorage:
    """
    Manages recording files and database entries.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage limits
        self.max_storage_mb = int(os.getenv("VM_MAX_RECORDINGS_MB", "5000"))  # 5GB default
        self.max_age_days = int(os.getenv("VM_MAX_RECORDINGS_DAYS", "30"))
    
    def get_file_path(self, filename: str) -> Path:
        """Get full path for a recording file."""
        return self.base_dir / filename
    
    def file_exists(self, filename: str) -> bool:
        """Check if a recording file exists."""
        return self.get_file_path(filename).exists()
    
    def get_file_info(self, filename: str) -> Optional[dict]:
        """Get file info for a recording."""
        path = self.get_file_path(filename)
        if not path.exists():
            return None
        
        stat = path.stat()
        return {
            "filename": filename,
            "path": str(path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    
    def list_files(self) -> List[dict]:
        """List all recording files with info."""
        files = []
        for path in self.base_dir.glob("*.mp4"):
            info = self.get_file_info(path.name)
            if info:
                files.append(info)
        
        # Sort by creation time, newest first
        files.sort(key=lambda x: x["created_at"], reverse=True)
        return files
    
    def get_total_size_mb(self) -> float:
        """Get total size of all recordings in MB."""
        total_bytes = sum(
            f.stat().st_size 
            for f in self.base_dir.glob("*.mp4") 
            if f.is_file()
        )
        return round(total_bytes / (1024 * 1024), 2)
    
    def delete_file(self, filename: str) -> bool:
        """Delete a recording file."""
        path = self.get_file_path(filename)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def cleanup_old_files(self) -> int:
        """
        Delete recordings older than max_age_days.
        Returns number of files deleted.
        """
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        deleted = 0
        
        for path in self.base_dir.glob("*.mp4"):
            if path.is_file():
                file_time = datetime.fromtimestamp(path.stat().st_ctime)
                if file_time < cutoff:
                    path.unlink()
                    deleted += 1
        
        return deleted
    
    def cleanup_by_size(self) -> int:
        """
        Delete oldest recordings if total size exceeds limit.
        Returns number of files deleted.
        """
        files = self.list_files()
        total_mb = self.get_total_size_mb()
        deleted = 0
        
        # Files are sorted newest first, so we delete from the end
        while total_mb > self.max_storage_mb and files:
            oldest = files.pop()
            self.delete_file(oldest["filename"])
            total_mb -= oldest["size_mb"]
            deleted += 1
        
        return deleted
    
    async def save_recording_to_db(
        self,
        filename: str,
        alert_id: Optional[str] = None,
        duration_seconds: float = 0,
    ) -> Optional[RecordingModel]:
        """Save recording metadata to database."""
        file_info = self.get_file_info(filename)
        if not file_info:
            return None
        
        async with get_db_context() as session:
            recording = RecordingModel(
                alert_id=alert_id,
                filename=filename,
                path=file_info["path"],
                duration_seconds=duration_seconds,
                file_size_bytes=file_info["size_bytes"],
            )
            session.add(recording)
            await session.flush()
            await session.refresh(recording)
            return recording
    
    async def get_recordings_from_db(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get recordings from database with file info."""
        from sqlalchemy import select, desc
        
        async with get_db_context() as session:
            result = await session.execute(
                select(RecordingModel)
                .order_by(desc(RecordingModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            recordings = result.scalars().all()
            
            return [
                {
                    "id": r.id,
                    "alert_id": r.alert_id,
                    "filename": r.filename,
                    "path": r.path,
                    "duration_seconds": r.duration_seconds,
                    "file_size_bytes": r.file_size_bytes,
                    "resolution": f"{r.resolution_width}x{r.resolution_height}" if r.resolution_width else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "exists": self.file_exists(r.filename),
                }
                for r in recordings
            ]
    
    async def delete_recording_from_db(self, recording_id: str) -> bool:
        """Delete recording from database and filesystem."""
        from sqlalchemy import select, delete
        
        async with get_db_context() as session:
            result = await session.execute(
                select(RecordingModel).where(RecordingModel.id == recording_id)
            )
            recording = result.scalar_one_or_none()
            
            if not recording:
                return False
            
            # Delete file
            self.delete_file(recording.filename)
            
            # Delete from database
            await session.execute(
                delete(RecordingModel).where(RecordingModel.id == recording_id)
            )
            
            return True


# Global storage instance
_storage: Optional[RecordingStorage] = None


def get_storage() -> RecordingStorage:
    """Get or create the global recording storage."""
    global _storage
    if _storage is None:
        recordings_dir = os.getenv(
            "VM_RECORDINGS_DIR",
            str(Path(__file__).parent.parent.parent / "data" / "recordings")
        )
        _storage = RecordingStorage(recordings_dir)
    return _storage
