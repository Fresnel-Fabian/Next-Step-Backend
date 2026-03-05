# app/schemas/notification.py
from pydantic import BaseModel
from datetime import datetime


class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"


class NotificationCreate(NotificationBase):
    user_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": 1,
                "title": "Schedule Updated",
                "message": "The Science department schedule has been updated.",
                "type": "info",
            }
        }
    }


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    isRead: bool
    createdAt: datetime
    # New fields
    entityType: str | None = None
    fileUrl: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_notification(cls, notif) -> "NotificationResponse":
        return cls(
            id=notif.id,
            title=notif.title,
            message=notif.message,
            type=notif.type,
            isRead=notif.is_read,
            createdAt=notif.created_at,
            entityType=notif.entity_type,
            fileUrl=notif.file_url,
        )