"""
Zona geometry system for geofencing.
Detecta si objetos están dentro de zonas definidas.
"""
from dataclasses import dataclass
from typing import Any
from enum import Enum
from shapely.geometry import Point, Polygon
from shapely.prepared import prep


class ZoneType(str, Enum):
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class Zone:
    """Define una zona de detección"""
    id: str
    name: str
    zone_type: ZoneType
    polygon: list[tuple[float, float]]  # Coordenadas normalizadas (0-1)
    color: str = "#f59e0b"
    enabled: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.zone_type.value,
            "polygon": self.polygon,
            "color": self.color,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Zone":
        return cls(
            id=data["id"],
            name=data["name"],
            zone_type=ZoneType(data["type"]),
            polygon=[tuple(p) for p in data["polygon"]],
            color=data.get("color", "#f59e0b"),
            enabled=data.get("enabled", True),
        )


@dataclass
class ZoneEvent:
    """Evento cuando un objeto entra/sale de una zona"""
    tracker_id: int
    class_name: str
    zone_id: str
    zone_name: str
    zone_type: ZoneType
    event_type: str  # "enter" | "inside" | "exit"
    timestamp: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "tracker_id": self.tracker_id,
            "class_name": self.class_name,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "zone_type": self.zone_type.value,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
        }


class ZoneManager:
    """
    Administra zonas y detecta cuándo objetos entran/salen.
    """
    
    def __init__(self):
        self.zones: dict[str, Zone] = {}
        self._prepared_polygons: dict[str, Any] = {}
        self._object_zones: dict[int, set[str]] = {}  # tracker_id -> set of zone_ids
    
    def add_zone(self, zone: Zone) -> None:
        """Agrega o actualiza una zona"""
        self.zones[zone.id] = zone
        # Pre-preparar polígono para queries rápidas
        poly = Polygon(zone.polygon)
        self._prepared_polygons[zone.id] = prep(poly)
    
    def remove_zone(self, zone_id: str) -> bool:
        """Elimina una zona"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            del self._prepared_polygons[zone_id]
            return True
        return False
    
    def clear_zones(self) -> None:
        """Elimina todas las zonas"""
        self.zones.clear()
        self._prepared_polygons.clear()
        self._object_zones.clear()
    
    def get_zones(self) -> list[Zone]:
        """Retorna todas las zonas"""
        return list(self.zones.values())
    
    def check_point(
        self, 
        x: float, 
        y: float, 
        frame_width: int,
        frame_height: int
    ) -> list[Zone]:
        """
        Verifica en qué zonas está un punto.
        
        Args:
            x, y: Coordenadas en píxeles
            frame_width, frame_height: Tamaño del frame
            
        Returns:
            Lista de zonas que contienen el punto
        """
        # Normalizar coordenadas a 0-1
        norm_x = x / frame_width
        norm_y = y / frame_height
        point = Point(norm_x, norm_y)
        
        zones_containing: list[Zone] = []
        for zone_id, prepared in self._prepared_polygons.items():
            zone = self.zones[zone_id]
            if zone.enabled and prepared.contains(point):
                zones_containing.append(zone)
        
        return zones_containing
    
    def check_objects(
        self,
        objects: list[dict],  # Lista de TrackedObject.to_dict()
        frame_width: int,
        frame_height: int,
        timestamp: float,
    ) -> list[ZoneEvent]:
        """
        Verifica todos los objetos contra todas las zonas.
        Detecta eventos de entrada/salida.
        
        Args:
            objects: Lista de objetos trackeados (con bottom_center)
            frame_width, frame_height: Tamaño del frame
            timestamp: Timestamp actual
            
        Returns:
            Lista de eventos de zona
        """
        events: list[ZoneEvent] = []
        current_object_zones: dict[int, set[str]] = {}
        
        for obj in objects:
            tracker_id = obj["tracker_id"]
            bottom = obj["bottom_center"]
            x, y = bottom[0], bottom[1]
            
            # Verificar zonas
            containing_zones = self.check_point(x, y, frame_width, frame_height)
            current_zones = {z.id for z in containing_zones}
            current_object_zones[tracker_id] = current_zones
            
            # Verificar cambios respecto a frame anterior
            previous_zones = self._object_zones.get(tracker_id, set())
            
            # Nuevas entradas
            entered_zones = current_zones - previous_zones
            for zone_id in entered_zones:
                zone = self.zones[zone_id]
                events.append(ZoneEvent(
                    tracker_id=tracker_id,
                    class_name=obj["class_name_es"],
                    zone_id=zone_id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    event_type="enter",
                    timestamp=timestamp,
                ))
            
            # Objetos que siguen dentro
            still_inside = current_zones & previous_zones
            for zone_id in still_inside:
                zone = self.zones[zone_id]
                events.append(ZoneEvent(
                    tracker_id=tracker_id,
                    class_name=obj["class_name_es"],
                    zone_id=zone_id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    event_type="inside",
                    timestamp=timestamp,
                ))
            
            # Salidas
            exited_zones = previous_zones - current_zones
            for zone_id in exited_zones:
                if zone_id in self.zones:  # Zona podría haber sido eliminada
                    zone = self.zones[zone_id]
                    events.append(ZoneEvent(
                        tracker_id=tracker_id,
                        class_name=obj["class_name_es"],
                        zone_id=zone_id,
                        zone_name=zone.name,
                        zone_type=zone.zone_type,
                        event_type="exit",
                        timestamp=timestamp,
                    ))
        
        # Actualizar estado
        self._object_zones = current_object_zones
        
        return events
    
    def get_danger_events(self, events: list[ZoneEvent]) -> list[ZoneEvent]:
        """Filtra solo eventos de zonas danger (entrada o dentro)"""
        return [
            e for e in events 
            if e.zone_type == ZoneType.DANGER and e.event_type in ("enter", "inside")
        ]
    
    def get_warning_events(self, events: list[ZoneEvent]) -> list[ZoneEvent]:
        """Filtra solo eventos de zonas warning (entrada o dentro)"""
        return [
            e for e in events 
            if e.zone_type == ZoneType.WARNING and e.event_type in ("enter", "inside")
        ]



# Zonas por defecto (ejemplo piscina)
DEFAULT_POOL_ZONES = [
    Zone(
        id="pool-edge",
        name="Borde Piscina",
        zone_type=ZoneType.WARNING,
        polygon=[(0.1, 0.35), (0.9, 0.35), (0.9, 0.45), (0.1, 0.45)],
        color="#f59e0b",
    ),
    Zone(
        id="pool-water",
        name="Dentro del Agua",
        zone_type=ZoneType.DANGER,
        polygon=[(0.1, 0.45), (0.9, 0.45), (0.9, 0.85), (0.1, 0.85)],
        color="#ef4444",
    ),
]

# Global Zone Manager Singleton
ZONE_MANAGER = ZoneManager()
for z in DEFAULT_POOL_ZONES:
    ZONE_MANAGER.add_zone(z)
