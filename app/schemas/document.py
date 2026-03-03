# app/schemas/document.py
"""
Document schemas for request/response validation.

References:
    Files resource: https://developers.google.com/workspace/drive/api/reference/rest/v3/files
    Permissions resource: https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions
"""

from pydantic import BaseModel
from datetime import datetime


class DocumentBase(BaseModel):
    """
    Base schema with common document fields.
    """

    title: str
    category: str
    description: str | None = None


class DocumentCreate(DocumentBase):
    """
    Schema for creating a standard (non-Drive) document.

    POST /api/v1/documents
    """

    file_url: str = ""
    file_size: int = 0

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Employee Handbook 2024",
                "category": "Policies",
                "description": "Complete guide for new employees",
                "file_url": "https://storage.example.com/handbook.pdf",
                "file_size": 2048576,
            }
        }
    }


class DriveDocumentCreate(DocumentBase):
    """
    Schema for registering a Google Drive file as a document.

    POST /api/v1/documents/from-drive

    The frontend sends file metadata returned by the Google Drive Picker.
    The backend stores this and sets sharing permissions via the Drive API.

    References:
        Files resource fields (id, webViewLink, mimeType):
        https://developers.google.com/workspace/drive/api/reference/rest/v3/files
    """

    drive_file_id: str
    web_view_link: str  # Files resource `webViewLink` — opens file in Google viewer
    mime_type: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Q3 Budget Report",
                "category": "Reports",
                "description": "Finance report for Q3",
                "drive_file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
                "web_view_link": "https://docs.google.com/spreadsheets/d/1BxiM.../edit",
                "mime_type": "application/vnd.google-apps.spreadsheet",
            }
        }
    }


class DocumentResponse(BaseModel):
    """
    Schema for document in API responses.
    """

    id: int
    title: str
    category: str
    description: str | None
    fileUrl: str
    fileSize: int
    uploadedBy: int
    createdAt: datetime
    # Drive fields — null for non-Drive documents
    driveFileId: str | None = None
    webViewLink: str | None = None
    mimeType: str | None = None
    isSharedWithMe: bool = False
    driveOwnerEmail: str | None = None

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
            createdAt=doc.created_at,
            driveFileId=doc.drive_file_id,
            webViewLink=doc.web_view_link,
            mimeType=doc.mime_type,
            isSharedWithMe=doc.is_shared_with_me,
            driveOwnerEmail=doc.drive_owner_email,
        )
