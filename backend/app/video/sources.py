"""
Manejadores de fuentes de video.
Soporta webcam local y cámaras IP (celular).
"""
import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import Generator
import time
import threading
from queue import Queue, Empty

from app.config import DetectionConfig, VideoSourceType


class VideoSource(ABC):
    """Clase base abstracta para fuentes de video"""
    
    @abstractmethod
    def start(self) -> bool:
        """Inicia la captura de video. Retorna True si fue exitoso."""
        pass
    
    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        """Lee un frame. Retorna (success, frame)."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Detiene la captura de video."""
        pass
    
    @abstractmethod
    def is_opened(self) -> bool:
        """Verifica si la fuente está abierta."""
        pass
    
    @property
    @abstractmethod
    def frame_size(self) -> tuple[int, int]:
        """Retorna (width, height) del frame."""
        pass


class WebcamSource(VideoSource):
    """Fuente de video desde webcam local"""
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap: cv2.VideoCapture | None = None
        self._frame_size: tuple[int, int] = (0, 0)
        
    def start(self) -> bool:
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"❌ No se pudo abrir webcam {self.camera_index}")
            return False
        
        # Configurar resolución (intentar 720p)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Obtener resolución real
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._frame_size = (w, h)
        
        print(f"✅ Webcam {self.camera_index} iniciada @ {w}x{h}")
        return True
    
    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.cap is None:
            return False, None
        return self.cap.read()
    
    def stop(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
            print("🛑 Webcam detenida")
    
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
    
    @property
    def frame_size(self) -> tuple[int, int]:
        return self._frame_size


class IPCameraSource(VideoSource):
    """
    Fuente de video desde cámara IP (celular con IP Webcam, DroidCam, etc.)
    Usa un thread separado para buffering y evitar lag.
    """
    
    def __init__(self, url: str):
        self.url = url
        self.cap: cv2.VideoCapture | None = None
        self._frame_size: tuple[int, int] = (0, 0)
        self._running = False
        self._thread: threading.Thread | None = None
        self._frame_queue: Queue[np.ndarray] = Queue(maxsize=1)  # Buffer pequeño para menor latencia
        self._last_frame: np.ndarray | None = None
        self._reconnect_delay = 5.0
        
    def _connect(self) -> bool:
        """Intenta conectar a la cámara"""
        try:
            # Eliminar CAP_FFMPEG para que OpenCV autodetecte (match test_cam.py)
            cap = cv2.VideoCapture(self.url)
            
            if not cap.isOpened():
                return False
                
            # Leer un frame de prueba
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return False
                
            self.cap = cap
            h, w = frame.shape[:2]
            self._frame_size = (w, h)
            print(f"✅ Conectado a cámara IP {self.url} @ {w}x{h}")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a cámara IP: {e}")
            return False

    def _capture_loop(self) -> None:
        """Thread de captura continua con reconexión automática"""
        print(f"🔄 Iniciando loop de captura para: {self.url}")
        
        while self._running:
            if self.cap is None or not self.cap.isOpened():
                if self._connect():
                    print(f"✅ Reconexión exitosa a: {self.url}")
                else:
                    time.sleep(self._reconnect_delay)
                    continue
            
            try:
                ret, frame = self.cap.read()
                if ret:
                    # Siempre mantener solo el último frame
                    if self._frame_queue.full():
                        try:
                            self._frame_queue.get_nowait()
                        except Empty:
                            pass
                    self._frame_queue.put(frame)
                else:
                    # Fallo de lectura, forzar reconexión
                    print("⚠️ Fallo lectura de frame, reconectando...")
                    self.cap.release()
                    self.cap = None
                    time.sleep(1.0)
            except Exception as e:
                print(f"❌ Error en captura: {e}")
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(1.0)
    
    def start(self) -> bool:
        # Intentar conexión inicial
        if not self._connect():
            print(f"⚠️ No se pudo conectar inicialmente a: {self.url}. Reintentando en background...")
            # No fallamos aquí para permitir que el loop de reintento funcione
            
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        
        return True
    
    def read(self) -> tuple[bool, np.ndarray | None]:
        try:
            # Timeout corto para no bloquear
            frame = self._frame_queue.get(timeout=0.1)
            self._last_frame = frame
            return True, frame
        except Empty:
            # Retornar último frame conocido mientras reconecta
            if self._last_frame is not None:
                return True, self._last_frame
            return False, None
    
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.cap:
            self.cap.release()
            self.cap = None
        print("🛑 Cámara IP desconectada")
    
    def is_opened(self) -> bool:
        return self._running
    
    @property
    def frame_size(self) -> tuple[int, int]:
        return self._frame_size


def create_video_source(config: DetectionConfig) -> VideoSource:
    """Factory function para crear la fuente de video según configuración"""
    if config.video_source == VideoSourceType.IP_CAMERA:
        if not config.ip_camera_url:
            raise ValueError("URL de cámara IP no configurada")
        return IPCameraSource(config.ip_camera_url)
    else:
        return WebcamSource(config.webcam_index)
