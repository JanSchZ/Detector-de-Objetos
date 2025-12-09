"""
Alert notification system.
Envía notificaciones push via Ntfy o Pushover.
"""
import asyncio
import httpx
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime
import time

from app.zones.geometry import ZoneEvent, ZoneType


class AlertPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Alert:
    """Representa una alerta generada"""
    id: str
    title: str
    message: str
    priority: AlertPriority
    zone_type: ZoneType
    tracker_id: int
    class_name: str
    timestamp: float
    sent: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "zone_type": self.zone_type.value,
            "tracker_id": self.tracker_id,
            "class_name": self.class_name,
            "timestamp": self.timestamp,
            "sent": self.sent,
        }


@dataclass
class AlertConfig:
    """Configuración del sistema de alertas"""
    enabled: bool = True
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = "argos-alerts"
    min_confidence: float = 0.7
    min_frames_in_zone: int = 3  # Frames mínimos antes de alertar
    cooldown_seconds: float = 30.0  # Cooldown entre alertas iguales
    alert_classes: list[str] = field(default_factory=lambda: ["persona", "perro", "gato", "niño"])


class AlertNotifier:
    """
    Sistema de alertas con filtrado anti-falsos positivos.
    Envía notificaciones push via Ntfy.
    """
    
    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig()
        self._frame_counts: dict[str, int] = {}  # "tracker_id:zone_id" -> frame count
        self._last_alerts: dict[str, float] = {}  # "class:zone" -> last alert timestamp
        self._alert_history: list[Alert] = []
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea cliente HTTP"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    async def close(self) -> None:
        """Cierra el cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_key(self, tracker_id: int, zone_id: str) -> str:
        return f"{tracker_id}:{zone_id}"
    
    def _get_cooldown_key(self, class_name: str, zone_id: str) -> str:
        return f"{class_name}:{zone_id}"
    
    def _is_in_cooldown(self, class_name: str, zone_id: str) -> bool:
        """Verifica si una combinación clase/zona está en cooldown"""
        key = self._get_cooldown_key(class_name, zone_id)
        last_time = self._last_alerts.get(key, 0)
        return (time.time() - last_time) < self.config.cooldown_seconds
    
    def _update_cooldown(self, class_name: str, zone_id: str) -> None:
        """Registra tiempo de última alerta"""
        key = self._get_cooldown_key(class_name, zone_id)
        self._last_alerts[key] = time.time()
    
    def process_zone_events(
        self, 
        events: list[ZoneEvent],
    ) -> list[Alert]:
        """
        Procesa eventos de zona y genera alertas.
        Aplica filtros anti-falsos positivos.
        
        Args:
            events: Lista de eventos de zona
            
        Returns:
            Lista de alertas a enviar
        """
        if not self.config.enabled:
            return []
        
        alerts: list[Alert] = []
        
        for event in events:
            # Solo procesar entradas y permanencia
            if event.event_type not in ("enter", "inside"):
                continue
            
            # Verificar si la clase está habilitada para alertas
            if event.class_name.lower() not in [c.lower() for c in self.config.alert_classes]:
                continue
            
            key = self._get_key(event.tracker_id, event.zone_id)
            
            # Incrementar contador de frames
            if event.event_type == "enter":
                self._frame_counts[key] = 1
            else:  # inside
                self._frame_counts[key] = self._frame_counts.get(key, 0) + 1
            
            frame_count = self._frame_counts[key]
            
            # Verificar mínimo de frames
            if frame_count < self.config.min_frames_in_zone:
                continue
            
            # Verificar cooldown
            if self._is_in_cooldown(event.class_name, event.zone_id):
                continue
            
            # Generar alerta solo en el frame exacto que cumple el mínimo
            # o primera vez después de cooldown
            if frame_count == self.config.min_frames_in_zone or (
                frame_count > self.config.min_frames_in_zone and 
                not self._is_in_cooldown(event.class_name, event.zone_id)
            ):
                alert = self._create_alert(event)
                alerts.append(alert)
                self._update_cooldown(event.class_name, event.zone_id)
                self._alert_history.append(alert)
        
        # Limpiar contadores de objetos que ya no están
        active_keys = {self._get_key(e.tracker_id, e.zone_id) for e in events}
        self._frame_counts = {k: v for k, v in self._frame_counts.items() if k in active_keys}
        
        return alerts
    
    def _create_alert(self, event: ZoneEvent) -> Alert:
        """Crea un objeto Alert desde un ZoneEvent"""
        is_danger = event.zone_type == ZoneType.DANGER
        
        if is_danger:
            priority = AlertPriority.URGENT
            title = f"🚨 ¡ALERTA CRÍTICA!"
            emoji = "🚨"
        else:
            priority = AlertPriority.HIGH
            title = f"⚠️ Advertencia"
            emoji = "⚠️"
        
        message = f"{emoji} {event.class_name.capitalize()} detectado en {event.zone_name}"
        
        alert_id = f"{event.tracker_id}-{event.zone_id}-{int(event.timestamp)}"
        
        return Alert(
            id=alert_id,
            title=title,
            message=message,
            priority=priority,
            zone_type=event.zone_type,
            tracker_id=event.tracker_id,
            class_name=event.class_name,
            timestamp=event.timestamp,
        )
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Envía una alerta via Ntfy.
        
        Args:
            alert: Alerta a enviar
            
        Returns:
            True si se envió correctamente
        """
        if not self.config.enabled:
            return False
        
        try:
            client = await self._get_client()
            
            # Mapear prioridad a Ntfy
            priority_map = {
                AlertPriority.LOW: "2",
                AlertPriority.NORMAL: "3",
                AlertPriority.HIGH: "4",
                AlertPriority.URGENT: "5",
            }
            
            headers = {
                "Title": alert.title,
                "Priority": priority_map.get(alert.priority, "3"),
                "Tags": f"{alert.zone_type.value},argos",
            }
            
            url = f"{self.config.ntfy_server}/{self.config.ntfy_topic}"
            response = await client.post(url, content=alert.message, headers=headers)
            
            if response.status_code == 200:
                alert.sent = True
                return True
            else:
                print(f"Error enviando alerta: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error enviando alerta: {e}")
            return False
    
    async def send_alerts(self, alerts: list[Alert]) -> int:
        """
        Envía múltiples alertas.
        
        Returns:
            Número de alertas enviadas exitosamente
        """
        sent_count = 0
        for alert in alerts:
            if await self.send_alert(alert):
                sent_count += 1
        return sent_count
    
    def get_recent_alerts(self, limit: int = 10) -> list[Alert]:
        """Retorna las últimas N alertas"""
        return self._alert_history[-limit:]
    
    def clear_history(self) -> None:
        """Limpia el historial de alertas"""
        self._alert_history.clear()
        self._frame_counts.clear()
        self._last_alerts.clear()
