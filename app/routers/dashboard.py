# app/routers/dashboard.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.dashboard import DashboardStats, ActivityItem
from app.dependencies import get_current_user, require_admin
from app.models import User, Schedule, Document, Activity, Poll
from app.models.schedule_event import ScheduleEvent
from app.models.user import UserRole

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Teachers
    total_teachers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.TEACHER)
    )
    new_teachers = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.TEACHER,
            User.created_at >= month_start,
        )
    )

    # Students
    total_students = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.STUDENT)
    )
    new_students = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.STUDENT,
            User.created_at >= month_start,
        )
    )

    # Upcoming schedule events (today and future)
    today = now.strftime("%Y-%m-%d")
    active_schedules = await db.scalar(
        select(func.count(ScheduleEvent.id)).where(ScheduleEvent.date >= today)
    )

    # Active Polls
    active_polls = await db.scalar(
        select(func.count(Poll.id)).where(Poll.is_active == True)
    )

    return DashboardStats(
        totalTeachers=total_teachers or 0,
        teachersTrend=f"+{new_teachers or 0} this month",
        totalStudents=total_students or 0,
        studentsTrend=f"+{new_students or 0} this month",
        activeSchedules=active_schedules or 0,
        schedulesTrend="upcoming events",
        activePolls=active_polls or 0,
        pollsTrend="currently open",
    )


@router.get("/activity", response_model=list[ActivityItem])
async def get_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Activity).order_by(Activity.timestamp.desc()).limit(limit)
    )
    activities = result.scalars().all()
    return [
        ActivityItem(id=a.id, title=a.title, author=a.author, timestamp=a.timestamp)
        for a in activities
    ]


@router.delete("/activity/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    await db.delete(activity)
    await db.commit()
    return None


@router.delete("/activity", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_activity(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Activity))
    for activity in result.scalars().all():
        await db.delete(activity)
    await db.commit()
    return None