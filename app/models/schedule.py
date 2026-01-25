# app/models/schedule.py
"""
Schedule model - Represents department class schedules.

This stores scheduling information for each department:
- How many classes they have
- How many staff members
- Current status (Active, Draft, Archived)
"""

from sqlalchemy import String, Integer, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime


class Schedule(Base):
    """
    Schedule database model.

    Represents a department's class schedule.

    Example:
        Schedule(
            department="Mathematics",
            class_count=12,
            staff_count=8,
            status="Active"
        )
    """

    __tablename__ = "schedules"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== SCHEDULE INFO ==========
    # Department name (e.g., "Mathematics", "Science")
    department: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False  # Fast lookups by department
    )

    # Number of classes in this schedule
    class_count: Mapped[int] = mapped_column(Integer, default=0)

    # Number of staff members assigned
    staff_count: Mapped[int] = mapped_column(Integer, default=0)

    # Schedule status
    # Active = currently in use
    # Draft = being prepared
    # Archived = no longer active
    status: Mapped[str] = mapped_column(String(50), default="Active")

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # When schedule was last modified
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),  # Auto-update on changes
    )

    # ========== INDEXES ==========
    # Composite index for common query patterns
    # e.g., "Find all active schedules for Math department"
    __table_args__ = (Index("idx_schedule_dept_status", "department", "status"),)

    def __repr__(self) -> str:
        return f"<Schedule(id={self.id}, department={self.department}, status={self.status})>"
