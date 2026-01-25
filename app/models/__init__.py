# app/models/__init__.py
"""
Database models package.

All SQLAlchemy models are exported here for easy importing:
    from app.models import User, Schedule, Document, Poll
"""

from app.models.user import User, UserRole
from app.models.schedule import Schedule
from app.models.document import Document
from app.models.poll import Poll, PollVote
from app.models.notification import Notification
from app.models.activity import Activity

__all__ = [
    # User
    "User",
    "UserRole",
    # Schedule
    "Schedule",
    # Document
    "Document",
    # Poll
    "Poll",
    "PollVote",
    # Notification
    "Notification",
    # Activity
    "Activity",
]
