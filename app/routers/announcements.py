# app/routers/announcements.py
"""
Announcement routes.

Endpoints:
- GET  /api/v1/announcements       - List announcements (all authenticated)
- POST /api/v1/announcements       - Create announcement (admin + teacher)
- DELETE /api/v1/announcements/{id} - Delete (admin: any; teacher: own only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.schemas.announcement import AnnouncementCreate, AnnouncementResponse
from app.dependencies import get_current_user, require_roles
from app.models import User, Announcement, Notification, Activity
from app.models.user import UserRole
from app.services.activity import log_activity
from app.services.notifications import broadcast_to_all

router = APIRouter(prefix="/api/v1/announcements", tags=["Announcements"])


@router.get("", response_model=list[AnnouncementResponse])
async def list_announcements(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    List all announcements. Visible to all authenticated users.
    """
    result = await db.execute(
        select(Announcement).order_by(Announcement.created_at.desc())
    )
    announcements = result.scalars().all()
    return [AnnouncementResponse.from_announcement(a) for a in announcements]


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """
    Create a new announcement and broadcast a notification to all users.
    Admin and Teacher only.
    """
    announcement = Announcement(
        title=data.title,
        message=data.message,
        file_url=data.file_url,
        file_name=data.file_name,
        created_by=current_user.id,
    )

    db.add(announcement)
    await db.flush()

    # Broadcast notification to all users
    count = await broadcast_to_all(
        db,
        title=f"Announcement: {data.title}",
        message=data.message,
        notification_type="info",
        entity_type="announcement",
        entity_id=announcement.id,
        file_url=data.file_url,
    )

    await log_activity(
        db,
        title=f"Announcement Created: {data.title}",
        author=current_user.name,
        action_type="create",
        entity_type="announcement",
        entity_id=announcement.id,
    )

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.from_announcement(announcement)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """
    Delete an announcement.
    Admins may delete any announcement; teachers may delete only ones they created.
    """
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    if current_user.role == UserRole.TEACHER and announcement.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete announcements you created",
        )

    # Remove all notifications and activity logs related to this announcement
    await db.execute(
        delete(Notification).where(
            Notification.entity_type == "announcement",
            Notification.entity_id == announcement_id,
        )
    )
    await db.execute(
        delete(Activity).where(
            Activity.entity_type == "announcement",
            Activity.entity_id == announcement_id,
        )
    )

    await db.delete(announcement)
    await db.commit()
    return None