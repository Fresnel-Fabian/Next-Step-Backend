# app/schemas/announcement.py
from pydantic import BaseModel
from datetime import datetime


class AnnouncementCreate(BaseModel):
    title: str
    message: str
    file_url: str | None = None
    file_name: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Staff Meeting Tomorrow",
                "message": "There will be a mandatory staff meeting tomorrow at 9am in the main hall.",
                "file_url": None,
                "file_name": None,
            }
        }
    }


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    message: str
    fileUrl: str | None
    fileName: str | None
    createdBy: int
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_announcement(cls, a) -> "AnnouncementResponse":
        return cls(
            id=a.id,
            title=a.title,
            message=a.message,
            fileUrl=a.file_url,
            fileName=a.file_name,
            createdBy=a.created_by,
            createdAt=a.created_at,
        )