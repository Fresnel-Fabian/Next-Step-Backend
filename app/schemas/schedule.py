# app/schemas/schedule.py
"""
Schedule schemas for request/response validation.

Endpoints:
- GET /api/v1/schedules
- POST /api/v1/schedules
- PUT /api/v1/schedules/{id}
- DELETE /api/v1/schedules/{id}
"""

from pydantic import BaseModel
from datetime import datetime


class ScheduleBase(BaseModel):
    """
    Base schema with common schedule fields.
    """

    department: str
    class_count: int = 0
    staff_count: int = 0
    status: str = "Active"


class ScheduleCreate(ScheduleBase):
    """
    Schema for creating a new schedule.

    Request body for POST /api/v1/schedules

    Example:
    {
        "department": "Mathematics",
        "class_count": 12,
        "staff_count": 8,
        "status": "Active"
    }
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "department": "Mathematics",
                "class_count": 12,
                "staff_count": 8,
                "status": "Active",
            }
        }
    }


class ScheduleUpdate(BaseModel):
    """
    Schema for updating a schedule (all fields optional).

    Request body for PUT /api/v1/schedules/{id}
    """

    department: str | None = None
    class_count: int | None = None
    staff_count: int | None = None
    status: str | None = None


class ScheduleResponse(BaseModel):
    """
    Schema for schedule in API responses.

    Note: Uses camelCase to match frontend API spec.

    Example response:
    {
        "id": "101",
        "department": "Mathematics",
        "classCount": 12,
        "staffCount": 8,
        "status": "Active",
        "lastUpdated": "2024-01-15T08:30:00Z"
    }
    """

    id: str  # String to match API spec
    department: str
    classCount: int  # camelCase for frontend
    staffCount: int  # camelCase for frontend
    status: str
    lastUpdated: datetime  # camelCase for frontend

    model_config = {"from_attributes": True}

    @classmethod
    def from_schedule(cls, schedule) -> "ScheduleResponse":
        """
        Create response from SQLAlchemy Schedule model.

        Handles:
        - Converting int id to string
        - Converting snake_case to camelCase
        """
        return cls(
            id=str(schedule.id),
            department=schedule.department,
            classCount=schedule.class_count,
            staffCount=schedule.staff_count,
            status=schedule.status,
            lastUpdated=schedule.last_updated,
        )
