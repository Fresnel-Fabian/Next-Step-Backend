# app/schemas/dashboard.py
"""
Dashboard schemas for stats and activity feed.

These match your frontend API specification:
- GET /api/v1/dashboard/stats
- GET /api/v1/dashboard/activity
"""

from pydantic import BaseModel
from datetime import datetime


class DashboardStats(BaseModel):
    """
    Dashboard statistics response.

    Response for GET /api/v1/dashboard/stats

    Example:
    {
        "totalStaff": 156,
        "staffTrend": "+12 this month",
        "activeSchedules": 12,
        "notificationsSent": 48,
        "totalDocuments": 284
    }
    """

    totalStaff: int
    staffTrend: str  # e.g., "+12 this month"
    activeSchedules: int
    notificationsSent: int
    totalDocuments: int


class ActivityItem(BaseModel):
    """
    Single activity item for the activity feed.

    Response item for GET /api/v1/dashboard/activity

    Example:
    {
        "id": 1,
        "title": "Schedule Created",
        "author": "Math Dept",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """

    id: int
    title: str
    author: str
    timestamp: datetime

    model_config = {"from_attributes": True}  # Allow creating from SQLAlchemy model
