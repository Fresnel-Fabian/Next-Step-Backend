# app/models/poll.py
"""
Poll models - For creating and voting on polls.

Two models:
- Poll: The poll question with options
- PollVote: Individual user votes

Poll options are stored as JSON for flexibility:
{
    "options": [
        {"id": 1, "text": "Option A"},
        {"id": 2, "text": "Option B"},
        {"id": 3, "text": "Option C"}
    ]
}
"""

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    func,
    ForeignKey,
    Boolean,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime



class Poll(Base):
    __tablename__ = "polls"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== POLL INFO ==========
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Poll options stored as JSON
    # Structure: {"options": [{"id": 1, "text": "..."}, ...]}
    options: Mapped[dict] = mapped_column(JSON, nullable=False)

    # ========== STATUS ==========
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # timezone=True required for safe comparison with datetime.now(timezone.utc)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ========== OWNERSHIP ==========
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ========== RELATIONSHIPS ==========
    votes: Mapped[list["PollVote"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Poll(id={self.id}, title={self.title}, is_active={self.is_active})>"


class PollVote(Base):
    __tablename__ = "poll_votes"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== VOTE INFO ==========
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        index=True,
    )

    # ForeignKey added so SQLAlchemy can join with User for results endpoint
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    option_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ========== RELATIONSHIPS ==========
    poll: Mapped["Poll"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship("User")

    # ========== CONSTRAINTS ==========
    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="unique_user_poll_vote"),
    )

    def __repr__(self) -> str:
        return f"<PollVote(poll_id={self.poll_id}, user_id={self.user_id}, option_id={self.option_id})>"