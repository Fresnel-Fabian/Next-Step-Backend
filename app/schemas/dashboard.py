# app/schemas/dashboard.py
"""
Dashboard schemas for stats and activity feed.
"""

from pydantic import BaseModel
from datetime import datetime


class DashboardStats(BaseModel):
    totalTeachers: int
    teachersTrend: str
    totalStudents: int
    studentsTrend: str
    activeSchedules: int
    schedulesTrend: str
    activePolls: int
    pollsTrend: str


class ActivityItem(BaseModel):
    id: int
    title: str
    author: str
    timestamp: datetime

    model_config = {"from_attributes": True}