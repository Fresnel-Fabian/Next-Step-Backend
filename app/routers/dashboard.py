# app/routers/dashboard.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.dashboard import DashboardStats, ActivityItem
from app.dependencies import get_current_user, require_admin
from app.models import User, Schedule, Document, Notification, Activity

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    (
        total_staff,
        new_staff,
        active_schedules,
        notifications_sent,
        total_documents,
    ) = await asyncio.gather(
        db.scalar(select(func.count(User.id))),
        db.scalar(
            select(func.count(User.id)).where(User.created_at >= month_start)
        ),
        db.scalar(
            select(func.count(Schedule.id)).where(Schedule.status == "Active")
        ),
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.created_at >= thirty_days_ago
            )
        ),
        db.scalar(select(func.count(Document.id))),
    )

    return DashboardStats(
        totalStaff=total_staff or 0,
        staffTrend=f"+{new_staff or 0} this month",
        activeSchedules=active_schedules or 0,
        notificationsSent=notifications_sent or 0,
        totalDocuments=total_documents or 0,
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
    """
    Delete a single activity item. Admin only.
    """
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
    """
    Delete all activity items. Admin only.
    """
    result = await db.execute(select(Activity))
    activities = result.scalars().all()

    for activity in activities:
        await db.delete(activity)

    await db.commit()
    return None