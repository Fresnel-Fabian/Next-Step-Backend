# app/schemas/schedule_event.py
from pydantic import BaseModel
from datetime import datetime


class ScheduleEventCreate(BaseModel):
    subject: str
    description: str | None = None
    date: str  # YYYY-MM-DD
    startTime: str  # HH:MM
    endTime: str  # HH:MM
    professor: str
    room: str | None = None
    color: str = "#4285F4"
    eventType: str = "lecture"
    students: list[str] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "subject": "Mathematics 101",
                "description": "Introduction to Calculus",
                "date": "2026-03-31",
                "startTime": "09:00",
                "endTime": "10:30",
                "professor": "Dr. Smith",
                "room": "Room 204",
                "color": "#4285F4",
                "eventType": "lecture",
                "students": ["Alice Martin", "Bob Wilson"],
            }
        }
    }


class ScheduleEventUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    date: str | None = None
    startTime: str | None = None
    endTime: str | None = None
    professor: str | None = None
    room: str | None = None
    color: str | None = None
    eventType: str | None = None
    students: list[str] | None = None


class ScheduleEventResponse(BaseModel):
    id: int
    subject: str
    description: str | None
    date: str
    startTime: str
    endTime: str
    professor: str
    room: str | None
    color: str
    eventType: str
    students: list[str]
    createdBy: int
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_event(cls, event) -> "ScheduleEventResponse":
        import json
        students = []
        if event.students_json:
            try:
                students = json.loads(event.students_json)
            except (json.JSONDecodeError, TypeError):
                students = []

        return cls(
            id=event.id,
            subject=event.subject,
            description=event.description,
            date=event.date,
            startTime=event.start_time,
            endTime=event.end_time,
            professor=event.professor,
            room=event.room,
            color=event.color,
            eventType=event.event_type,
            students=students,
            createdBy=event.created_by,
            createdAt=event.created_at,
            updatedAt=event.updated_at,
        )
