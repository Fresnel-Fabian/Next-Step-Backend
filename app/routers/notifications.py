# app/routers/notifications.py
"""
Notification routes.

Endpoints:
- GET   /api/v1/notifications              - List user's notifications
- GET   /api/v1/notifications/unread-count - Get unread count
- PATCH /api/v1/notifications/{id}/read    - Mark as read
- PATCH /api/v1/notifications/read-all     - Mark all as read
- POST  /api/v1/notifications/send         - Send notification (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.database import get_db
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.dependencies import get_current_user, require_admin
from app.models import User, Notification

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False, description="Only show unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List notifications for the current user.

    Query parameters:
    - unread_only: If true, only return unread notifications
    - skip: Pagination offset
    - limit: Max results

    Returns notifications sorted by date (newest first).
    """

    # Only get current user's notifications
    query = select(Notification).where(Notification.user_id == current_user.id)

    # Filter unread only if requested
    if unread_only:
        query = query.where(Notification.is_read == False)

    # Order by date (newest first) and paginate
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [NotificationResponse.from_notification(n) for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get the count of unread notifications.

    Useful for displaying badge numbers in the UI.

    Returns:
    {
        "unreadCount": 5
    }
    """

    count = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == False
        )
    )

    return {"unreadCount": count or 0}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a specific notification as read.

    Only works for notifications belonging to the current user.
    """

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,  # Security: only own notifications
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    notification.is_read = True
    await db.commit()

    return {"message": "Notification marked as read"}


@router.patch("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications as read for the current user.

    Uses bulk update for efficiency.
    """

    # Bulk update - more efficient than loading each notification
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )

    await db.commit()

    return {"message": "All notifications marked as read"}


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),  # Admin only!
):
    """
    Send a notification to a specific user.

    Requires admin role.

    Request body:
    {
        "user_id": 1,
        "title": "Schedule Updated",
        "message": "The Science department schedule has been updated.",
        "type": "info"
    }
    """

    # Verify target user exists
    target_user = await db.execute(select(User).where(User.id == data.user_id))
    if not target_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found"
        )

    notification = Notification(
        user_id=data.user_id, title=data.title, message=data.message, type=data.type
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    return NotificationResponse.from_notification(notification)


@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
async def broadcast_notification(
    title: str = Query(..., description="Notification title"),
    message: str = Query(..., description="Notification message"),
    notification_type: str = Query(
        "info", description="Type: info, success, warning, error"
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),  # Admin only!
):
    """
    Broadcast a notification to ALL users.

    Requires admin role.

    Query parameters:
    - title: Notification title
    - message: Notification body
    - notification_type: info, success, warning, error

    Example:
    POST /api/v1/notifications/broadcast?title=Announcement&message=Staff+meeting+tomorrow&notification_type=warning
    """

    # Get all user IDs
    result = await db.execute(select(User.id))
    user_ids = [row[0] for row in result.all()]

    # Create notification for each user
    notifications = [
        Notification(user_id=uid, title=title, message=message, type=notification_type)
        for uid in user_ids
    ]

    db.add_all(notifications)
    await db.commit()

    return {
        "message": f"Notification sent to {len(user_ids)} users",
        "count": len(user_ids),
    }
