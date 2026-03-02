# app/models/document.py
"""
Document model - Represents uploaded files and documents.

This stores metadata about documents:
- Title and description
- Category (Policies, Forms, Handbooks, etc.)
- File URL and size
- Who uploaded it
"""

from sqlalchemy import String, Integer, DateTime, func, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class Document(Base):
    """
    Document database model.

    Stores metadata about uploaded documents.

    Example:
        Document(
            title="Employee Handbook 2024",
            category="Policies",
            description="Complete guide for new employees",
            file_url="https://s3.amazonaws.com/.../handbook.pdf",
            file_size=2048576,  # 2MB in bytes
            uploaded_by=1
        )
    """

    __tablename__ = "documents"

    # Document Info
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    # uploader: Mapped["User"] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Google Drive Sync Fields
    drive_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    drive_permission_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    web_view_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_shared_with_me: Mapped[bool] = mapped_column(
        default=False  # distinguishes uploaded vs synced from Shared With Me
    )
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    drive_owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, category={self.category})>"
