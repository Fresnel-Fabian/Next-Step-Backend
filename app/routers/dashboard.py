# app/routers/dashboard.py
"""
Dashboard routes.

Endpoints:
- GET /api/v1/dashboard/stats    - Get dashboard statistics
- GET /api/v1/dashboard/activity - Get recent activity feed
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.schemas.dashboard import DashboardStats, ActivityItem
from app.dependencies import get_current_user
from app.models import User, Schedule, Document, Notification, Activity

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),  # Require authentication
):
    """
    Get dashboard statistics.

    Returns aggregated counts for:
    - Total staff members
    - Staff trend (new this month)
    - Active schedules
    - Notifications sent (last 30 days)
    - Total documents

    All queries are executed asynchronously for performance.
    """

    # ===== Total Staff Count =====
    total_staff = await db.scalar(select(func.count(User.id)))

    # ===== Staff Added This Month =====
    # Get the first day of current month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    new_staff = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )

    # ===== Active Schedules =====
    active_schedules = await db.scalar(
        select(func.count(Schedule.id)).where(Schedule.status == "Active")
    )

    # ===== Notifications Sent (Last 30 Days) =====
    thirty_days_ago = now - timedelta(days=30)

    notifications_sent = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.created_at >= thirty_days_ago
        )
    )

    # ===== Total Documents =====
    total_documents = await db.scalar(select(func.count(Document.id)))

    # Build and return response
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
    """
    Get recent activity feed.

    Query parameters:
    - limit: Maximum number of activities to return (default: 20)

    Returns list of recent activities sorted by timestamp (newest first).
    """

    result = await db.execute(
        select(Activity)
        .order_by(Activity.timestamp.desc())  # Newest first
        .limit(limit)
    )

    activities = result.scalars().all()

    # Convert to response schema
    return [
        ActivityItem(id=a.id, title=a.title, author=a.author, timestamp=a.timestamp)
        for a in activities
    ]
