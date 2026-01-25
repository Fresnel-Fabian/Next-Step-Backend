# app/routers/users.py
"""
User management routes.

Endpoints:
- PUT /api/v1/users/profile - Update current user's profile
- GET /api/v1/users         - List all users (admin only)
- GET /api/v1/users/{id}    - Get specific user
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.user import UserUpdate, UserResponse
from app.dependencies import get_current_user, require_admin
from app.models.user import User

# ============================================
# Create Router
# ============================================
router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# ============================================
# PUT /api/v1/users/profile
# ============================================
@router.put("/profile", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
        Update the current user's profile.

        Only updates fields that are provided (partial update).

        Request body (all fields optional):
    ```json
        {
            "name": "New Name",
            "department": "New Department"
        }
    ```

        Returns: Updated user profile
    """
    print("hello")
    # Update only provided fields
    if updates.name is not None:
        current_user.name = updates.name

    if updates.department is not None:
        current_user.department = updates.department

    # Save changes
    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_user(current_user)


# ============================================
# GET /api/v1/users (Admin Only)
# ============================================
@router.get("", response_model=list[UserResponse])
async def list_users(
    department: str | None = Query(None, description="Filter by department"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_admin
    ),  # _ means we don't use the value, just check admin
):
    """
    List all users (admin only).

    Query parameters:
    - department: Filter by department name
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 50, max: 100)

    Returns: List of users
    """
    query = select(User)

    # Apply department filter if provided
    if department:
        query = query.where(User.department == department)

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    return [UserResponse.from_user(u) for u in users]


# ============================================
# GET /api/v1/users/{user_id}
# ============================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),  # Any authenticated user can view
):
    """
    Get a specific user by ID.

    Path parameters:
    - user_id: The user's ID

    Returns: User profile

    Raises: 404 if user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.from_user(user)
