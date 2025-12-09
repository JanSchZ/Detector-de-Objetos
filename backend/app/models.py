"""
Database models for Argos.
Defines all persistent entities: users, zones, alerts, recordings, and analytics.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class UserModel(Base):
    """User account for authentication."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ZoneModel(Base):
    """Security zone definition."""
    __tablename__ = "zones"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(20), nullable=False)  # warning, danger, interest
    polygon: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of [x, y] points
    color: Mapped[str] = mapped_column(String(7), default="#f59e0b")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alerts: Mapped[List["AlertModel"]] = relationship("AlertModel", back_populates="zone")


class AlertModel(Base):
    """Alert triggered by zone intrusion."""
    __tablename__ = "alerts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    zone_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(20), nullable=False)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tracker_id: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_successfully: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    zone: Mapped[Optional["ZoneModel"]] = relationship("ZoneModel", back_populates="alerts")
    recording: Mapped[Optional["RecordingModel"]] = relationship("RecordingModel", back_populates="alert", uselist=False)


class RecordingModel(Base):
    """Video clip recording associated with an alert."""
    __tablename__ = "recordings"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    alert_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    resolution_width: Mapped[int] = mapped_column(Integer, default=0)
    resolution_height: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    alert: Mapped[Optional["AlertModel"]] = relationship("AlertModel", back_populates="recording")


class AnalyticsModel(Base):
    """Daily analytics aggregation."""
    __tablename__ = "analytics"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    zone_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    
    # Aggregated data (stored as JSON for flexibility)
    total_detections: Mapped[int] = mapped_column(Integer, default=0)
    class_counts: Mapped[str] = mapped_column(Text, default="{}")  # JSON: {"person": 150, "car": 23}
    hourly_counts: Mapped[str] = mapped_column(Text, default="[]")  # JSON: [0, 5, 12, ...] for each hour
    peak_hour: Mapped[int] = mapped_column(Integer, default=0)  # Hour with most detections
    total_alerts: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConfigModel(Base):
    """Persistent configuration storage."""
    __tablename__ = "config"
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
