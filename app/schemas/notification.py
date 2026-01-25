# app/schemas/notification.py
"""
Notification schemas for request/response validation.

Endpoints:
- GET /api/v1/notifications
- PATCH /api/v1/notifications/{id}/read
- PATCH /api/v1/notifications/read-all
- POST /api/v1/notifications/send (admin)
"""

from pydantic import BaseModel
from datetime import datetime


class NotificationBase(BaseModel):
    """
    Base schema with common notification fields.
    """

    title: str
    message: str
    type: str = "info"  # info, success, warning, error


class NotificationCreate(NotificationBase):
    """
    Schema for creating a notification (admin endpoint).

    Request body for POST /api/v1/notifications/send

    Example:
    {
        "user_id": 1,
        "title": "Schedule Updated",
        "message": "The Science department schedule has been updated.",
        "type": "info"
    }
    """

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
    """
    Schema for notification in API responses.

    Example response:
    {
        "id": 1,
        "title": "Schedule Updated",
        "message": "The Science department schedule has been updated.",
        "type": "info",
        "isRead": false,
        "createdAt": "2024-01-15T10:30:00Z"
    }
    """

    id: int
    title: str
    message: str
    type: str
    isRead: bool  # camelCase
    createdAt: datetime  # camelCase

    model_config = {"from_attributes": True}

    @classmethod
    def from_notification(cls, notif) -> "NotificationResponse":
        """Create response from SQLAlchemy Notification model."""
        return cls(
            id=notif.id,
            title=notif.title,
            message=notif.message,
            type=notif.type,
            isRead=notif.is_read,
            createdAt=notif.created_at,
        )
