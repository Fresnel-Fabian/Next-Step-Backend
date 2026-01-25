# app/schemas/__init__.py
"""
Pydantic schemas package.

All schemas are exported here for easy importing:
    from app.schemas import LoginRequest, ScheduleResponse, PollCreate
"""

# Auth
from app.schemas.auth import LoginRequest, GoogleAuthRequest, Token, TokenData

# User
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse

# Dashboard
from app.schemas.dashboard import DashboardStats, ActivityItem

# Schedule
from app.schemas.schedule import (
    ScheduleBase,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
)

# Document
from app.schemas.document import DocumentBase, DocumentCreate, DocumentResponse

# Poll
from app.schemas.poll import (
    PollOptionInput,
    PollOptionResponse,
    PollCreate,
    PollResponse,
    VoteRequest,
)

# Notification
from app.schemas.notification import (
    NotificationBase,
    NotificationCreate,
    NotificationResponse,
)

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