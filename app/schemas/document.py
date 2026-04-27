# app/schemas/document.py
"""
Document schemas for request/response validation.

Endpoints:
- GET /api/v1/documents
- POST /api/v1/documents
- DELETE /api/v1/documents/{id}
"""

from pydantic import BaseModel
from datetime import datetime
import enum


class AccessLevel(str, enum.Enum):
    ALL = "ALL"           # visible to everyone
    TEACHERS = "TEACHERS" # visible to admin + teachers only
    STUDENTS = "STUDENTS" # visible to admin + students only


class DocumentBase(BaseModel):
    title: str
    category: str
    description: str | None = None


class DocumentCreate(DocumentBase):
    """
    Schema for creating a new document.

    Example:
    {
        "title": "Employee Handbook 2024",
        "category": "Policies",
        "description": "Complete guide for new employees",
        "file_url": "https://storage.example.com/handbook.pdf",
        "file_size": 2048576,
        "access_level": "ALL"
    }
    """
    file_url: str
    file_size: int = 0
    access_level: AccessLevel = AccessLevel.ALL

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Employee Handbook 2024",
                "category": "Policies",
                "description": "Complete guide for new employees",
                "file_url": "https://storage.example.com/handbook.pdf",
                "file_size": 2048576,
                "access_level": "ALL",
            }
        }
    }


class DocumentResponse(BaseModel):
    """
    Schema for document in API responses.

    Example response:
    {
        "id": 1,
        "title": "Employee Handbook 2024",
        "category": "Policies",
        "description": "Complete guide",
        "fileUrl": "https://...",
        "fileSize": 2048576,
        "uploadedBy": 1,
        "accessLevel": "ALL",
        "createdAt": "2024-01-15T10:30:00Z"
    }
    """
    id: int
    title: str
    category: str
    description: str | None
    fileUrl: str
    fileSize: int
    uploadedBy: int
    accessLevel: AccessLevel
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_document(cls, doc) -> "DocumentResponse":
        """Create response from SQLAlchemy Document model."""
        return cls(
            id=doc.id,
            title=doc.title,
            category=doc.category,
            description=doc.description,
            fileUrl=doc.file_url,
            fileSize=doc.file_size,
            uploadedBy=doc.uploaded_by,
            accessLevel=doc.access_level or AccessLevel.ALL,
            createdAt=doc.created_at,
        )