# app/models/schedule_event.py
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class ScheduleEvent(Base):
    """
    Individual class/event within a schedule.

    Stores time-based events that appear on the calendar view:
    subject, date, start/end times, professor, room, etc.
    """

    __tablename__ = "schedule_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM

    professor: Mapped[str] = mapped_column(String(255), nullable=False)
    room: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="#4285F4")

    # 'lecture', 'lab', 'seminar', 'tutorial'
    event_type: Mapped[str] = mapped_column(String(50), default="lecture")

    # JSON-encoded list of student names (e.g. '["Alice","Bob"]')
    students_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<ScheduleEvent(id={self.id}, subject={self.subject}, date={self.date})>"
