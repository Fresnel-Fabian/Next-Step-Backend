# app/services/activity.py
"""
Activity logging service.

Provides a simple function to log activities from anywhere in the app.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity import Activity


async def log_activity(
    db: AsyncSession,
    title: str,
    author: str,
    action_type: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Activity:
    """
    Log an activity to the database.

    Args:
        db: Database session
        title: What happened (e.g., "Schedule Created")
        author: Who did it (e.g., "Math Dept" or "John Doe")
        action_type: Type of action (create, update, delete, upload)
        entity_type: What type of thing (schedule, document, poll)
        entity_id: ID of the entity for linking

    Returns:
        Created Activity object

    Example:
        await log_activity(
            db,
            title="Schedule Created",
            author=current_user.department or current_user.name,
            action_type="create",
            entity_type="schedule",
            entity_id=new_schedule.id
        )
    """
    activity = Activity(
        title=title,
        author=author,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    db.add(activity)
    await db.flush()  # Get ID without committing

    return activity
