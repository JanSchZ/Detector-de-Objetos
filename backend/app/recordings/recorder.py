"""
Video clip recording for VisionMind.
Captures video clips before and after alert events.
"""
import asyncio
import os
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import cv2
import numpy as np


class RecordingBuffer:
    """
    Circular buffer that stores frames for pre-event recording.
    Thread-safe implementation for use with video capture threads.
    """
    
    def __init__(self, buffer_seconds: int = 5, fps: int = 15):
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.max_frames = buffer_seconds * fps
        self.buffer: deque = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        self.frame_size: Optional[tuple[int, int]] = None
    
    def add_frame(self, frame: np.ndarray):
        """Add a frame to the circular buffer."""
        with self.lock:
            # Store frame with timestamp
            self.buffer.append({
                "frame": frame.copy(),
                "timestamp": time.time(),
            })
            if self.frame_size is None and frame is not None:
                self.frame_size = (frame.shape[1], frame.shape[0])
    
    def get_buffered_frames(self) -> list[dict]:
        """Get all frames currently in the buffer."""
        with self.lock:
            return list(self.buffer)
    
    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()


class ClipRecorder:
    """
    Records video clips when alerts are triggered.
    Uses a pre-event buffer and captures additional post-event frames.
    """
    
    def __init__(
        self,
        output_dir: str = "recordings",
        pre_seconds: int = 5,
        post_seconds: int = 10,
        fps: int = 15,
        codec: str = "mp4v",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.fps = fps
        self.codec = codec
        
        # Recording state
        self._recording = False
        self._current_writer: Optional[cv2.VideoWriter] = None
        self._current_filename: Optional[str] = None
        self._post_frames_remaining = 0
        self._recording_start_time = 0
        self._frame_count = 0
        
        # Frame buffer for pre-event recording
        self.buffer = RecordingBuffer(buffer_seconds=pre_seconds, fps=fps)
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Callback for when recording completes
        self._on_complete: Optional[Callable] = None
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    def add_frame(self, frame: np.ndarray):
        """
        Add a frame to the system.
        If recording, adds to the current clip.
        Otherwise, adds to the pre-event buffer.
        """
        with self._lock:
            if self._recording and self._current_writer is not None:
                self._current_writer.write(frame)
                self._frame_count += 1
                self._post_frames_remaining -= 1
                
                # Check if recording should stop
                if self._post_frames_remaining <= 0:
                    self._stop_recording()
            else:
                # Add to circular buffer for pre-event recording
                self.buffer.add_frame(frame)
    
    def start_recording(self, alert_id: str, alert_info: Optional[dict] = None) -> Optional[str]:
        """
        Start recording a clip for the given alert.
        Returns the filename of the new recording.
        """
        with self._lock:
            if self._recording:
                # Already recording, extend the post-event duration
                self._post_frames_remaining = self.post_seconds * self.fps
                return self._current_filename
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clip_{timestamp}_{alert_id[:8]}.mp4"
            filepath = self.output_dir / filename
            
            # Get frame size from buffer
            buffered_frames = self.buffer.get_buffered_frames()
            if not buffered_frames and self.buffer.frame_size is None:
                print(f"⚠️ No frames in buffer, cannot start recording")
                return None
            
            frame_size = self.buffer.frame_size
            if frame_size is None and buffered_frames:
                f = buffered_frames[0]["frame"]
                frame_size = (f.shape[1], f.shape[0])
            
            if frame_size is None:
                return None
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*self.codec)
            self._current_writer = cv2.VideoWriter(
                str(filepath),
                fourcc,
                self.fps,
                frame_size,
            )
            
            if not self._current_writer.isOpened():
                print(f"❌ No se pudo crear el archivo de video: {filepath}")
                return None
            
            # Write buffered pre-event frames
            for frame_data in buffered_frames:
                self._current_writer.write(frame_data["frame"])
                self._frame_count += 1
            
            # Set recording state
            self._recording = True
            self._current_filename = filename
            self._post_frames_remaining = self.post_seconds * self.fps
            self._recording_start_time = time.time()
            
            print(f"🎬 Iniciando grabación: {filename} (pre-buffer: {len(buffered_frames)} frames)")
            
            return filename
    
    def _stop_recording(self):
        """Stop the current recording (internal, called with lock held)."""
        if self._current_writer is not None:
            self._current_writer.release()
            
            duration = time.time() - self._recording_start_time
            print(f"🎬 Grabación finalizada: {self._current_filename} ({self._frame_count} frames, {duration:.1f}s)")
            
            # Call completion callback
            if self._on_complete:
                asyncio.create_task(self._on_complete(
                    self._current_filename,
                    self._frame_count,
                    duration,
                ))
            
            self._current_writer = None
            self._current_filename = None
            self._recording = False
            self._frame_count = 0
    
    def stop_recording(self):
        """Force stop the current recording."""
        with self._lock:
            if self._recording:
                self._stop_recording()
    
    def on_recording_complete(self, callback: Callable):
        """Set callback for when recording completes."""
        self._on_complete = callback
    
    def get_recordings_dir(self) -> Path:
        """Get the recordings directory path."""
        return self.output_dir


# Global recorder instance
_recorder: Optional[ClipRecorder] = None


def get_recorder() -> ClipRecorder:
    """Get or create the global clip recorder."""
    global _recorder
    if _recorder is None:
        recordings_dir = os.getenv(
            "VM_RECORDINGS_DIR",
            str(Path(__file__).parent.parent.parent / "data" / "recordings")
        )
        _recorder = ClipRecorder(
            output_dir=recordings_dir,
            pre_seconds=int(os.getenv("VM_RECORDING_PRE_SECONDS", "5")),
            post_seconds=int(os.getenv("VM_RECORDING_POST_SECONDS", "10")),
            fps=int(os.getenv("VM_RECORDING_FPS", "15")),
        )
    return _recorder
