"""Package init for api module"""
from app.api.routes import router, get_zone_manager, get_alert_notifier
from app.api.websocket import detection_websocket

__all__ = ["router", "detection_websocket", "get_zone_manager", "get_alert_notifier"]
