# app/models/user.py
"""
User model - Represents the 'users' table in database.

This stores all user information including:
- Authentication credentials
- Profile information  
- Google OAuth integration
"""

from sqlalchemy import String, Enum as SQLEnum, DateTime, func
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
    ADMIN = "ADMIN"      # Full access: create schedules, manage users
    TEACHER = "TEACHER"  # Create content, view reports
    STUDENT = "STUDENT"      # Basic access: view schedules, notifications

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
    # Mapped[type] = SQLAlchemy 2.0 syntax for type hints
    # mapped_column() = defines column properties
    id: Mapped[int] = mapped_column(
        primary_key=True,    # Auto-incrementing ID
        index=True           # Create index for fast lookups
    )
    
    # ========== AUTHENTICATION ==========
    # Email - unique identifier for login
    email: Mapped[str] = mapped_column(
        String(255),         # Max 255 characters
        unique=True,         # No duplicate emails
        index=True,          # Fast lookups for login
        nullable=False       # Must have value
    )
    
    # Name - display name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Password hash - stored securely (never plain text!)
    # nullable=True because Google OAuth users don't have password
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True        # Optional: Google users don't need this
    )
    
    # ========== AUTHORIZATION ==========
    # Role - determines what user can do
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),   # Use Python Enum in database
        default=UserRole.STUDENT,  # New users are STAFF by default
        nullable=False
    )
    
    # ========== PROFILE ==========
    # Avatar URL - profile picture
    avatar: Mapped[str | None] = mapped_column(
        String(512),         # URLs can be long
        nullable=True
    )
    
    # Department - which department user belongs to
    department: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    # ========== GOOGLE OAUTH ==========
    # Google ID - unique identifier from Google
    # Used to link Google account to our user
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,         # Each Google account linked once
        nullable=True,       # Only set for Google users
        index=True           # Fast lookups for Google login
    )
    
    # ========== TIMESTAMPS ==========
    # When user registered
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()  # PostgreSQL sets this automatically
    )
    
    # When user last updated profile
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()  # Auto-update on any change
    )
    
    # ========== RELATIONSHIPS ==========
    # One-to-Many: One user has many notifications
    # We'll create Notification model later
    # back_populates creates bidirectional relationship
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"  # Delete notifications when user deleted
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"