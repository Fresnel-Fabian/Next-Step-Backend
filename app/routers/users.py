# app/routers/users.py
"""
User management routes.

Endpoints:
- PUT   /api/v1/users/profile          - Update current user's profile
- GET   /api/v1/users                  - List all users (admin only)
- GET   /api/v1/users/{id}             - Get specific user
- DELETE /api/v1/users/{id}            - Permanently delete user (admin only)
- PATCH /api/v1/users/{id}/deactivate  - Deactivate user (admin only)
- PATCH /api/v1/users/{id}/activate    - Reactivate user (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.user import UserUpdate, UserResponse
from app.dependencies import get_current_user, require_admin
from app.models.user import User, UserRole

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
    """Update the current user's profile. Only updates fields that are provided."""
    if updates.name is not None:
        current_user.name = updates.name

    if updates.department is not None:
        current_user.department = updates.department

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_user(current_user)


# ============================================
# GET /api/v1/users (Admin Only)
# ============================================
@router.get("", response_model=list[UserResponse])
async def list_users(
    role: UserRole | None = Query(None, description="Filter by role: STUDENT, TEACHER, ADMIN"),
    department: str | None = Query(None, description="Filter by department"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users. Optionally filter by role or department. Admin only."""
    query = select(User)

    if role:
        query = query.where(User.role == role)

    if department:
        query = query.where(User.department == department)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [UserResponse.from_user(u) for u in result.scalars().all()]


# ============================================
# GET /api/v1/users/{user_id}
# ============================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a specific user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.from_user(user)


# ============================================
# DELETE /api/v1/users/{user_id} (Admin Only)
# ============================================
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Permanently delete a user. Admin only.

    Cannot delete yourself.
    """
    if int(admin.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()


# ============================================
# PATCH /api/v1/users/{user_id}/deactivate (Admin Only)
# ============================================
@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Deactivate a user account. Admin only.

    The user will be blocked from logging in but their data is preserved.
    Cannot deactivate yourself.
    """
    if int(admin.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated.",
        )

    user.is_active = False
    await db.commit()

    return {"message": f"{user.name}'s account has been deactivated."}


# ============================================
# PATCH /api/v1/users/{user_id}/activate (Admin Only)
# ============================================
@router.patch("/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Reactivate a previously deactivated user. Admin only.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active.",
        )

    user.is_active = True
    await db.commit()

    return {"message": f"{user.name}'s account has been reactivated."}