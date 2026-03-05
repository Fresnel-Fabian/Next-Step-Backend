# app/services/notifications.py
"""
Reusable notification broadcasting service.

Used by:
- announcements router (when admin/teacher creates announcement)
- documents router (when doc is uploaded)
- polls router (when admin creates a poll)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.notification import Notification


async def broadcast_to_all(
    db: AsyncSession,
    title: str,
    message: str,
    notification_type: str = "info",
    entity_type: str | None = None,
    file_url: str | None = None,
) -> int:
    """
    Send a notification to every user in the system.

    Args:
        db: Database session
        title: Notification title
        message: Notification body
        notification_type: info / success / warning / error
        entity_type: announcement / document / poll / system
        file_url: Optional download link (for document notifications)

    Returns:
        Number of users notified
    """
    result = await db.execute(select(User.id))
    user_ids = [row[0] for row in result.all()]

    notifications = [
        Notification(
            user_id=uid,
            title=title,
            message=message,
            type=notification_type,
            entity_type=entity_type,
            file_url=file_url,
        )
        for uid in user_ids
    ]

    db.add_all(notifications)
    return len(user_ids)