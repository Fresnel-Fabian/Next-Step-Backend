# app/dependencies.py
"""
FastAPI Dependencies - Reusable route prerequisites.

Dependencies are functions that run BEFORE your route handler.
They can:
- Validate data
- Check authentication
- Provide common objects (like current user)

Usage in routes:
    @router.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        # 'user' is automatically provided by the dependency
        return {"message": f"Hello {user.name}"}
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.services.auth import decode_token
from app.models.user import User, UserRole

# ============================================
# 1. Security Scheme
# ============================================
# HTTPBearer extracts token from "Authorization: Bearer <token>" header
# This also adds the padlock icon in Swagger UI docs
security = HTTPBearer()


# ============================================
# 2. Get Current User Dependency
# ============================================
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that extracts and validates JWT token.

    What happens:
    1. HTTPBearer extracts token from Authorization header
    2. We decode and verify the token
    3. We fetch the user from database
    4. We return the user object

    If any step fails → 401 Unauthorized

    Usage:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user

    Args:
        credentials: Automatically extracted from Authorization header
        db: Database session (from get_db dependency)

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    # Extract the token string
    token = credentials.credentials

    # Decode and verify token
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},  # Standard header for 401
        )

    # Extract user ID from token payload
    user_id = payload.get("sub")  # "sub" = subject (standard JWT claim)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# ============================================
# 3. Require Admin Role Dependency
# ============================================
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires admin role.

    Chains with get_current_user:
    1. First, get_current_user runs (validates token, gets user)
    2. Then, we check if user is admin

    Usage:
        @router.post("/schedules")
        async def create_schedule(admin: User = Depends(require_admin)):
            # Only admins can reach here
            pass

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object (if admin)

    Raises:
        HTTPException 403: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ============================================
# 4. Optional: Require Specific Roles
# ============================================
def require_roles(*allowed_roles: UserRole):
    """
    Factory function to create role-checking dependencies.

    Usage:
        @router.get("/teachers-only")
        async def teachers_only(
            user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER))
        ):
            pass

    Args:
        allowed_roles: Roles that are allowed to access the route

    Returns:
        Dependency function
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(r.value for r in allowed_roles)}",
            )
        return current_user

    return role_checker
