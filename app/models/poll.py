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
    """
    Poll database model.

    Represents a voting poll with multiple options.

    Example:
        Poll(
            title="Best day for staff meetings?",
            description="Vote for your preferred meeting day",
            options={"options": [
                {"id": 1, "text": "Monday"},
                {"id": 2, "text": "Wednesday"},
                {"id": 3, "text": "Friday"}
            ]},
            created_by=1,
            expires_at=datetime(2024, 12, 31)
        )
    """

    __tablename__ = "polls"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== POLL INFO ==========
    # Poll question/title
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional description
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Poll options stored as JSON
    # Structure: {"options": [{"id": 1, "text": "..."}, ...]}
    # Why JSON?
    # - Flexible number of options
    # - Easy to add/modify options
    # - No need for separate options table
    options: Mapped[dict] = mapped_column(JSON, nullable=False)

    # ========== STATUS ==========
    # Is the poll still accepting votes?
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True  # Often filter by active status
    )

    # When does the poll expire? (optional)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ========== OWNERSHIP ==========
    # Who created this poll
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ========== RELATIONSHIPS ==========
    # One poll has many votes
    votes: Mapped[list["PollVote"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",  # Delete votes when poll is deleted
    )

    def __repr__(self) -> str:
        return f"<Poll(id={self.id}, title={self.title}, is_active={self.is_active})>"


class PollVote(Base):
    """
    PollVote database model.

    Represents a single user's vote on a poll.

    Constraints:
    - Each user can only vote once per poll
    - Vote must reference valid poll and option

    Example:
        PollVote(
            poll_id=1,
            user_id=5,
            option_id=2  # User 5 voted for option 2 on poll 1
        )
    """

    __tablename__ = "poll_votes"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== VOTE INFO ==========
    # Which poll this vote is for
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),  # Delete vote if poll deleted
        index=True,
    )

    # Which user voted
    user_id: Mapped[int] = mapped_column(Integer, index=True)

    # Which option they voted for
    # References the "id" field in the poll's options JSON
    option_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ========== RELATIONSHIPS ==========
    # Many votes belong to one poll
    poll: Mapped["Poll"] = relationship(back_populates="votes")

    # ========== CONSTRAINTS ==========
    __table_args__ = (
        # Ensure each user can only vote once per poll
        UniqueConstraint("poll_id", "user_id", name="unique_user_poll_vote"),
    )

    def __repr__(self) -> str:
        return f"<PollVote(poll_id={self.poll_id}, user_id={self.user_id}, option_id={self.option_id})>"
