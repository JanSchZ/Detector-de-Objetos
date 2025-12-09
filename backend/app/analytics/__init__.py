"""
Analytics module for VisionMind.
Provides detection statistics, trends, and aggregated data.
"""
from .aggregator import AnalyticsAggregator
from .routes import router

__all__ = ["AnalyticsAggregator", "router"]
