"""
API routes for analytics.
"""
from fastapi import APIRouter, Query
from typing import Literal

from .aggregator import AnalyticsAggregator

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_analytics_summary(days: int = Query(7, ge=1, le=90)):
    """Get analytics summary for the specified period."""
    return await AnalyticsAggregator.get_summary(days=days)


@router.get("/realtime")
async def get_realtime_stats():
    """Get current day's real-time statistics."""
    return AnalyticsAggregator.get_realtime_stats()


@router.get("/detections")
async def get_detection_trends(
    period: Literal["day", "week", "month"] = Query("week")
):
    """Get detection trends over time."""
    return await AnalyticsAggregator.get_detection_trends(period=period)


@router.get("/zones/{zone_id}")
async def get_zone_analytics(zone_id: str):
    """Get detailed analytics for a specific zone."""
    return await AnalyticsAggregator.get_zone_analytics(zone_id)


@router.get("/heatmap")
async def get_heatmap_data():
    """Get heatmap data showing activity by day and hour."""
    return await AnalyticsAggregator.get_heatmap_data()
