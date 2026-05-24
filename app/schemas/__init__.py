# app/schemas/__init__.py
"""
Pydantic schemas package.

All schemas are exported here for easy importing:
    from app.schemas import LoginRequest, ScheduleResponse, PollCreate
"""

# Auth
from app.schemas.auth import GoogleAuthRequest, LoginRequest, Token, TokenData

# Dashboard
from app.schemas.dashboard import ActivityItem, DashboardStats

# Document
from app.schemas.document import DocumentBase, DocumentCreate, DocumentResponse

# Notification
from app.schemas.notification import (
    NotificationBase,
    NotificationCreate,
    NotificationResponse,
)

# Poll
from app.schemas.poll import (
    PollCreate,
    PollOptionInput,
    PollOptionResponse,
    PollResponse,
    VoteRequest,
)

# Schedule
from app.schemas.schedule import (
    ScheduleBase,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)

# User
from app.schemas.user import UserBase, UserCreate, UserResponse, UserUpdate

__all__ = [
    # Auth
    "LoginRequest",
    "GoogleAuthRequest",
    "Token",
    "TokenData",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Dashboard
    "DashboardStats",
    "ActivityItem",
    # Schedule
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    # Document
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    # Poll
    "PollOptionInput",
    "PollOptionResponse",
    "PollCreate",
    "PollResponse",
    "VoteRequest",
    # Notification
    "NotificationBase",
    "NotificationCreate",
    "NotificationResponse",
]
