# app/models/user.py
"""
User model - Represents the 'users' table in database.

This stores all user information including:
- Authentication credentials
- Profile information
- Google OAuth integration
"""

from sqlalchemy import String, Boolean, Enum as SQLEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime
import enum


# ============================================
# 1. Define User Roles (Enum)
# ============================================
class UserRole(str, enum.Enum):
    """
    User roles for authorization.

    Why Enum?
    - Type safety: Can't accidentally assign invalid role
    - Documentation: Clear what roles exist
    - Database constraint: PostgreSQL enforces valid values

    Inherits from 'str' so it can be JSON serialized easily
    """

    ADMIN = "ADMIN"  # Full access: create schedules, manage users
    TEACHER = "TEACHER"  # Create content, view reports
    STUDENT = "STUDENT"  # Basic access: view schedules, notifications


# ============================================
# 2. User Model
# ============================================
class User(Base):
    """
    User database model.

    Represents a user in the system - could be admin, teacher, or staff.
    Supports both traditional email/password and Google OAuth login.
    """

    # Table name in PostgreSQL
    __tablename__ = "users"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # ========== AUTHENTICATION ==========
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # ========== AUTHORIZATION ==========
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.STUDENT,
        nullable=False,
    )

    # ========== STATUS ==========
    # Controls whether the user can log in.
    # Deactivated users are blocked at the auth dependency level.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ========== PROFILE ==========
    avatar: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ========== GOOGLE OAUTH ==========
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ========== RELATIONSHIPS ==========
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"