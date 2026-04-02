# app/models/notification.py
from sqlalchemy import String, DateTime, func, ForeignKey, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="info")

    # What kind of entity triggered this notification
    # Values: "announcement", "document", "poll", "schedule_event", "system"
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ID of the source entity (for cascade delete)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Download link if notification contains a document
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title})>"