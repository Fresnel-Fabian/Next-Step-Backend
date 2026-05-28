# app/routers/__init__.py
"""
API Routers package.

All route modules are exported here for easy importing.
"""

from app.routers import (
    auth,
    dashboard,
    documents,
    notifications,
    polls,
    schedules,
    users,
)

__all__ = [
    "auth",
    "users",
    "dashboard",
    "schedules",
    "documents",
    "polls",
    "notifications",
]
