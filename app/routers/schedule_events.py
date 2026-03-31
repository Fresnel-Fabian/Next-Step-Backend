# app/routers/schedule_events.py
"""
Schedule Event routes — individual class events on the calendar.

Endpoints:
- GET    /api/v1/schedule-events           - List events (authenticated)
- GET    /api/v1/schedule-events/{id}      - Get specific event
- POST   /api/v1/schedule-events           - Create event (admin only)
- PUT    /api/v1/schedule-events/{id}      - Update event (admin only)
- DELETE /api/v1/schedule-events/{id}      - Delete event (admin only)
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete

from app.database import get_db
from app.schemas.schedule_event import (
    ScheduleEventCreate,
    ScheduleEventUpdate,
    ScheduleEventResponse,
)
from app.dependencies import get_current_user, require_admin
from app.models import User, Notification, Activity
from app.models.schedule_event import ScheduleEvent
from app.services.activity import log_activity

router = APIRouter(prefix="/api/v1/schedule-events", tags=["Schedule Events"])


@router.get("", response_model=list[ScheduleEventResponse])
async def list_schedule_events(
    date: str | None = Query(None, description="Filter by date (YYYY-MM-DD)"),
    professor: str | None = Query(None, description="Filter by professor name"),
    student: str | None = Query(None, description="Filter by student name"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(ScheduleEvent).order_by(
        ScheduleEvent.date, ScheduleEvent.start_time
    )

    if date:
        query = query.where(ScheduleEvent.date == date)

    if professor:
        query = query.where(ScheduleEvent.professor.ilike(f"%{professor}%"))

    if student:
        query = query.where(ScheduleEvent.students_json.ilike(f"%{student}%"))

    result = await db.execute(query)
    events = result.scalars().all()
    return [ScheduleEventResponse.from_event(e) for e in events]


@router.get("/{event_id}", response_model=ScheduleEventResponse)
async def get_schedule_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule event not found"
        )
    return ScheduleEventResponse.from_event(event)


@router.post("", response_model=ScheduleEventResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule_event(
    data: ScheduleEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    event = ScheduleEvent(
        subject=data.subject,
        description=data.description,
        date=data.date,
        start_time=data.startTime,
        end_time=data.endTime,
        professor=data.professor,
        room=data.room,
        color=data.color,
        event_type=data.eventType,
        students_json=json.dumps(data.students) if data.students else None,
        created_by=current_user.id,
    )

    db.add(event)
    await db.flush()

    await log_activity(
        db,
        title=f"Class Created: {data.subject}",
        author=current_user.name,
        action_type="create",
        entity_type="schedule_event",
        entity_id=event.id,
    )

    await db.commit()
    await db.refresh(event)
    return ScheduleEventResponse.from_event(event)


@router.put("/{event_id}", response_model=ScheduleEventResponse)
async def update_schedule_event(
    event_id: int,
    data: ScheduleEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule event not found"
        )

    if data.subject is not None:
        event.subject = data.subject
    if data.description is not None:
        event.description = data.description
    if data.date is not None:
        event.date = data.date
    if data.startTime is not None:
        event.start_time = data.startTime
    if data.endTime is not None:
        event.end_time = data.endTime
    if data.professor is not None:
        event.professor = data.professor
    if data.room is not None:
        event.room = data.room
    if data.color is not None:
        event.color = data.color
    if data.eventType is not None:
        event.event_type = data.eventType
    if data.students is not None:
        event.students_json = json.dumps(data.students)

    await log_activity(
        db,
        title=f"Class Updated: {event.subject}",
        author=current_user.name,
        action_type="update",
        entity_type="schedule_event",
        entity_id=event.id,
    )

    await db.commit()
    await db.refresh(event)
    return ScheduleEventResponse.from_event(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule event not found"
        )

    # Remove all notifications and activity logs related to this event
    await db.execute(
        sa_delete(Notification).where(
            Notification.entity_type == "schedule_event",
            Notification.entity_id == event_id,
        )
    )
    await db.execute(
        sa_delete(Activity).where(
            Activity.entity_type == "schedule_event",
            Activity.entity_id == event_id,
        )
    )

    await db.delete(event)
    await db.commit()
    return None
