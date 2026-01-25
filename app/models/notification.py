# app/models/notification.py
"""
Notification model - User notifications.

Notifications can be:
- Schedule changes
- New documents uploaded
- Poll results
- System announcements
"""

from sqlalchemy import String, DateTime, func, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class Notification(Base):
    """
    Notification database model.

    Represents a notification for a specific user.

    Types:
    - info: General information
    - success: Positive news
    - warning: Important notices
    - error: Problems or issues

    Example:
        Notification(
            user_id=1,
            title="New Schedule Available",
            message="The Science department schedule has been updated.",
            type="info"
        )
    """

    __tablename__ = "notifications"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== NOTIFICATION INFO ==========
    # Which user this notification is for
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,  # Fast lookup of user's notifications
    )

    # Notification title (short)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Notification body (detailed message)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Type of notification for styling
    # info = blue, success = green, warning = yellow, error = red
    type: Mapped[str] = mapped_column(String(50), default="info")

    # ========== STATUS ==========
    # Has the user read this notification?
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True  # Often filter by read/unread
    )

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ========== RELATIONSHIPS ==========
    # Many notifications belong to one user
    user: Mapped["User"] = relationship(back_populates="notifications")

    # ========== INDEXES ==========
    # Common query: "Get unread notifications for user X"
    __table_args__ = (
        # Index for efficient queries
        # Index('idx_notification_user_unread', 'user_id', 'is_read'),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title})>"
        )
