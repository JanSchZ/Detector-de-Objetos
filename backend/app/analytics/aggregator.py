"""
Analytics data aggregation for Argos.
Collects and summarizes detection statistics.
"""
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models import AlertModel, AnalyticsModel, ZoneModel


class AnalyticsAggregator:
    """
    Aggregates detection and alert data for analytics.
    """
    
    # In-memory counters for real-time stats (reset daily)
    _today_detections: Dict[str, int] = defaultdict(int)  # class_name -> count
    _today_zone_entries: Dict[str, int] = defaultdict(int)  # zone_id -> count
    _hourly_counts: List[int] = [0] * 24
    _last_reset: datetime = datetime.now()
    
    @classmethod
    def record_detection(cls, class_name: str, zone_id: Optional[str] = None):
        """Record a detection event for real-time stats."""
        # Reset if new day
        cls._check_reset()
        
        # Increment class count
        cls._today_detections[class_name] += 1
        
        # Increment zone entry if applicable
        if zone_id:
            cls._today_zone_entries[zone_id] += 1
        
        # Increment hourly count
        hour = datetime.now().hour
        cls._hourly_counts[hour] += 1
    
    @classmethod
    def _check_reset(cls):
        """Reset counters if it's a new day."""
        now = datetime.now()
        if now.date() != cls._last_reset.date():
            cls._today_detections.clear()
            cls._today_zone_entries.clear()
            cls._hourly_counts = [0] * 24
            cls._last_reset = now
    
    @classmethod
    def get_realtime_stats(cls) -> dict:
        """Get current day's real-time statistics."""
        cls._check_reset()
        
        total = sum(cls._today_detections.values())
        peak_hour = cls._hourly_counts.index(max(cls._hourly_counts)) if any(cls._hourly_counts) else 0
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_detections": total,
            "class_counts": dict(cls._today_detections),
            "zone_entries": dict(cls._today_zone_entries),
            "hourly_counts": cls._hourly_counts,
            "peak_hour": peak_hour,
            "current_hour": datetime.now().hour,
        }
    
    @classmethod
    async def get_summary(cls, days: int = 7) -> dict:
        """Get analytics summary for the last N days."""
        cls._check_reset()
        
        # Get today's real-time stats
        today_stats = cls.get_realtime_stats()
        
        # Get historical data from database
        async with get_db_context() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get alerts count
            alerts_result = await session.execute(
                select(func.count(AlertModel.id))
                .where(AlertModel.timestamp >= start_date)
            )
            total_alerts = alerts_result.scalar() or 0
            
            # Get alerts by zone
            zone_alerts = await session.execute(
                select(AlertModel.zone_name, func.count(AlertModel.id))
                .where(AlertModel.timestamp >= start_date)
                .group_by(AlertModel.zone_name)
            )
            alerts_by_zone = {row[0]: row[1] for row in zone_alerts}
            
            # Get alerts by class
            class_alerts = await session.execute(
                select(AlertModel.class_name, func.count(AlertModel.id))
                .where(AlertModel.timestamp >= start_date)
                .group_by(AlertModel.class_name)
            )
            alerts_by_class = {row[0]: row[1] for row in class_alerts}
        
        return {
            "period_days": days,
            "today": today_stats,
            "alerts": {
                "total": total_alerts,
                "by_zone": alerts_by_zone,
                "by_class": alerts_by_class,
            },
            "generated_at": datetime.now().isoformat(),
        }
    
    @classmethod
    async def get_detection_trends(cls, period: str = "week") -> dict:
        """Get detection trends over time."""
        if period == "day":
            days = 1
        elif period == "week":
            days = 7
        elif period == "month":
            days = 30
        else:
            days = 7
        
        async with get_db_context() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get daily alert counts
            daily_result = await session.execute(
                select(
                    func.date(AlertModel.timestamp).label("date"),
                    func.count(AlertModel.id).label("count")
                )
                .where(AlertModel.timestamp >= start_date)
                .group_by(func.date(AlertModel.timestamp))
                .order_by(func.date(AlertModel.timestamp))
            )
            
            daily_data = [
                {"date": str(row.date), "count": row.count}
                for row in daily_result
            ]
        
        # Add today's real-time data
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(cls._today_detections.values())
        
        # Merge or append today's data
        if daily_data and daily_data[-1]["date"] == today_str:
            daily_data[-1]["count"] += today_count
        else:
            daily_data.append({"date": today_str, "count": today_count})
        
        return {
            "period": period,
            "days": days,
            "trend": daily_data,
            "total": sum(d["count"] for d in daily_data),
        }
    
    @classmethod
    async def get_zone_analytics(cls, zone_id: str) -> dict:
        """Get detailed analytics for a specific zone."""
        async with get_db_context() as session:
            # Get zone info
            zone_result = await session.execute(
                select(ZoneModel).where(ZoneModel.id == zone_id)
            )
            zone = zone_result.scalar_one_or_none()
            
            if not zone:
                return {"error": "Zone not found"}
            
            # Get recent alerts for this zone
            alerts_result = await session.execute(
                select(AlertModel)
                .where(AlertModel.zone_id == zone_id)
                .order_by(AlertModel.timestamp.desc())
                .limit(10)
            )
            recent_alerts = [
                {
                    "id": a.id,
                    "class_name": a.class_name,
                    "confidence": a.confidence,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                }
                for a in alerts_result.scalars()
            ]
            
            # Get class distribution for this zone
            class_dist = await session.execute(
                select(AlertModel.class_name, func.count(AlertModel.id))
                .where(AlertModel.zone_id == zone_id)
                .group_by(AlertModel.class_name)
            )
            class_distribution = {row[0]: row[1] for row in class_dist}
            
            # Get total alerts
            total_result = await session.execute(
                select(func.count(AlertModel.id))
                .where(AlertModel.zone_id == zone_id)
            )
            total_alerts = total_result.scalar() or 0
        
        return {
            "zone": {
                "id": zone.id,
                "name": zone.name,
                "type": zone.zone_type,
                "enabled": zone.enabled,
            },
            "total_alerts": total_alerts,
            "class_distribution": class_distribution,
            "recent_alerts": recent_alerts,
            "today_entries": cls._today_zone_entries.get(zone_id, 0),
        }
    
    @classmethod
    async def get_heatmap_data(cls) -> dict:
        """Get heatmap data (hourly distribution by day of week)."""
        async with get_db_context() as session:
            # Get last 30 days of alerts
            start_date = datetime.now() - timedelta(days=30)
            
            alerts_result = await session.execute(
                select(AlertModel.timestamp)
                .where(AlertModel.timestamp >= start_date)
            )
            
            # Build heatmap: day_of_week -> hour -> count
            heatmap = [[0] * 24 for _ in range(7)]
            
            for row in alerts_result:
                if row.timestamp:
                    day = row.timestamp.weekday()  # 0=Monday, 6=Sunday
                    hour = row.timestamp.hour
                    heatmap[day][hour] += 1
        
        return {
            "heatmap": heatmap,
            "days": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            "hours": list(range(24)),
            "period_days": 30,
        }


# Singleton instance
_aggregator = AnalyticsAggregator()


def get_aggregator() -> AnalyticsAggregator:
    """Get the analytics aggregator instance."""
    return _aggregator
