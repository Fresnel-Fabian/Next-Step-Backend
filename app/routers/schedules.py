# app/routers/schedules.py
"""
Schedule routes.

Endpoints:
- GET    /api/v1/schedules          - List all schedules
- GET    /api/v1/schedules/{id}     - Get specific schedule
- POST   /api/v1/schedules          - Create schedule (admin)
- PUT    /api/v1/schedules/{id}     - Update schedule (admin)
- DELETE /api/v1/schedules/{id}     - Delete schedule (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.dependencies import get_current_user, require_admin
from app.models import User, Schedule
from app.services.activity import log_activity

router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["Schedules"]
)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    search: str | None = Query(None, description="Search by department name"),
    status: str | None = Query(None, description="Filter by status (Active, Draft, Archived)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    List all schedules with optional filtering.
    
    Query parameters:
    - search: Filter by department name (case-insensitive partial match)
    - status: Filter by status (exact match)
    
    Example: GET /api/v1/schedules?search=math&status=Active
    """
    
    # Start building query
    query = select(Schedule)
    
    # Apply search filter (case-insensitive)
    if search:
        query = query.where(
            Schedule.department.ilike(f"%{search}%")  # ilike = case-insensitive LIKE
        )
    
    # Apply status filter
    if status:
        query = query.where(Schedule.status == status)
    
    # Order by last updated (newest first)
    query = query.order_by(Schedule.last_updated.desc())
    
    # Execute query
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    # Convert to response schema
    return [ScheduleResponse.from_schedule(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    Get a specific schedule by ID.
    
    Raises 404 if not found.
    """
    
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    return ScheduleResponse.from_schedule(schedule)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Create a new schedule.
    
    Requires admin role.
    
    Request body:
    {
        "department": "Mathematics",
        "class_count": 12,
        "staff_count": 8,
        "status": "Active"
    }
    """
    
    # Create new schedule
    schedule = Schedule(
        department=data.department,
        class_count=data.class_count,
        staff_count=data.staff_count,
        status=data.status
    )
    
    db.add(schedule)
    await db.flush()  # Get the ID
    
    # Log activity
    await log_activity(
        db,
        title=f"Schedule Created: {data.department}",
        author=current_user.department or current_user.name,
        action_type="create",
        entity_type="schedule",
        entity_id=schedule.id
    )
    
    await db.commit()
    await db.refresh(schedule)
    
    return ScheduleResponse.from_schedule(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Update an existing schedule.
    
    Requires admin role.
    Only updates fields that are provided (partial update).
    """
    
    # Find schedule
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Update only provided fields
    if data.department is not None:
        schedule.department = data.department
    if data.class_count is not None:
        schedule.class_count = data.class_count
    if data.staff_count is not None:
        schedule.staff_count = data.staff_count
    if data.status is not None:
        schedule.status = data.status
    
    # Log activity
    await log_activity(
        db,
        title=f"Schedule Updated: {schedule.department}",
        author=current_user.department or current_user.name,
        action_type="update",
        entity_type="schedule",
        entity_id=schedule.id
    )
    
    await db.commit()
    await db.refresh(schedule)
    
    return ScheduleResponse.from_schedule(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Delete a schedule.
    
    Requires admin role.
    Returns 204 No Content on success.
    """
    
    # Find schedule
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    department = schedule.department  # Save for activity log
    
    # Log activity (before delete)
    await log_activity(
        db,
        title=f"Schedule Deleted: {department}",
        author=current_user.department or current_user.name,
        action_type="delete",
        entity_type="schedule",
        entity_id=schedule_id
    )
    
    # Delete schedule
    await db.delete(schedule)
    await db.commit()
    
    # Return 204 No Content (no response body)
    return None