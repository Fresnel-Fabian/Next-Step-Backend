# app/models/invitation.py
import secrets
import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    token = Column(
        String,
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
    status = Column(
        SAEnum(InvitationStatus),
        default=InvitationStatus.PENDING,
        nullable=False,
    )
    # Stored as VARCHAR to match the database column added via ALTER TABLE
    role = Column(String, default="STUDENT", nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    invited_by = relationship("User", foreign_keys=[created_by])

    def is_valid(self) -> bool:
        """Check if invite is still pending and not expired."""
        return (
            self.status == InvitationStatus.PENDING
            and datetime.utcnow() < self.expires_at
        )