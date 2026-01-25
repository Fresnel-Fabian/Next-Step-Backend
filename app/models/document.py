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
    The actual file is stored elsewhere (S3, local filesystem, etc.)
    and we store the URL reference here.
    
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
    
    # ========== PRIMARY KEY ==========
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )
    
    # ========== DOCUMENT INFO ==========
    # Document title
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Category for filtering
    # e.g., "Policies", "Forms", "Handbooks", "Reports"
    category: Mapped[str] = mapped_column(
        String(100),
        index=True,  # Fast filtering by category
        nullable=False
    )
    
    # Optional description
    description: Mapped[str | None] = mapped_column(
        Text,  # Text allows longer content than String
        nullable=True
    )
    
    # ========== FILE INFO ==========
    # URL where file is stored
    file_url: Mapped[str] = mapped_column(
        String(512),  # URLs can be long
        nullable=False
    )
    
    # File size in bytes
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # ========== RELATIONSHIPS ==========
    # Who uploaded this document
    uploaded_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),  # References users table
        index=True
    )
    
    # Relationship to User model (optional, for easy access)
    # uploader: Mapped["User"] = relationship()
    
    # ========== TIMESTAMPS ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, category={self.category})>"