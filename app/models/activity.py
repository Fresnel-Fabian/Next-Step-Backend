# app/models/activity.py
"""
Activity model - Activity log for dashboard.

Tracks actions like:
- Schedule created/updated/deleted
- Documents uploaded
- Polls created
- Users joined
"""

from sqlalchemy import String, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime


class Activity(Base):
    """
    Activity database model.
    
    Logs activities for the dashboard feed.
    
    Example:
        Activity(
            title="Schedule Created",
            author="Math Dept",
            action_type="create",
            entity_type="schedule",
            entity_id=1
        )
    """
    
    __tablename__ = "activities"
    
    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )
    
    # ========== ACTIVITY INFO ==========
    # What happened (displayed in UI)
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Who did it (user name or department)
    author: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Type of action: create, update, delete, upload
    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    # What type of entity: schedule, document, poll, user
    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    
    # ID of the entity (for linking)
    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    # ========== TIMESTAMPS ==========
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True  # Sort by timestamp
    )
    
    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, title={self.title}, action={self.action_type})>"