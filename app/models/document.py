# app/models/document.py
"""
Document model - Represents uploaded files and documents.

This stores metadata about documents:
- Title and description
- Category (Policies, Forms, Handbooks, etc.)
- File URL and size
- Who uploaded it
- Access level (ALL, TEACHERS, STUDENTS)
"""

from sqlalchemy import String, Integer, DateTime, func, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime


class Document(Base):
    """
    Document database model.

    Stores metadata about uploaded documents.
    The actual file is stored on the local filesystem (uploads/)
    and we store the URL reference here.

    access_level controls visibility:
    - ALL      → everyone (admin, teachers, students)
    - TEACHERS → admin + teachers only
    - STUDENTS → admin + students only
    """

    __tablename__ = "documents"

    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ========== DOCUMENT INFO ==========
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    category: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ========== FILE INFO ==========
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)

    # ========== ACCESS CONTROL ==========
    access_level: Mapped[str] = mapped_column(
        String(20), default="ALL", nullable=False
    )

    # ========== RELATIONSHIPS ==========
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )

    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, access_level={self.access_level})>"