# app/routers/auth.py
"""
Authentication routes.

Endpoints:
- POST /api/v1/auth/login    - Email/password login
- POST /api/v1/auth/google   - Google OAuth login
- POST /api/v1/auth/register - Create new account
- GET  /api/v1/auth/me       - Get current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.auth import LoginRequest, GoogleAuthRequest
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    hash_password,
)
from app.services.google_auth import (
    verify_google_token,
    get_or_create_google_user,
    GoogleAuthError,
)
from app.dependencies import get_current_user
from app.models.user import User

# ============================================
# Create Router
# ============================================
# prefix: All routes will start with /api/v1/auth
# tags: Groups routes in Swagger UI docs
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


# ============================================
# POST /api/v1/auth/login
# ============================================
@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email and password.
    
    Request body:
```json
    {
        "email": "user@school.edu",
        "password": "yourpassword"
    }
```
    
    Returns:
```json
    {
        "token": "eyJhbG...",
        "user": {
            "id": "1",
            "name": "John Doe",
            "email": "user@school.edu",
            "role": "STAFF",
            "avatar": null,
            "department": "Science"
        }
    }
```
    """
    # Authenticate user (checks email exists and password matches)
    user = await authenticate_user(db, request.email, request.password)
    
    if not user:
        # Don't reveal whether email exists or password is wrong (security)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create our app's JWT token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Return token and user info
    return {
        "token": token,
        "user": UserResponse.from_user(user)
    }


# ============================================
# POST /api/v1/auth/google
# ============================================
@router.post("/google")
async def google_auth(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with Google OAuth.
    
    Frontend sends the idToken received from Google SDK.
    
    Request body:
```json
    {
        "idToken": "eyJhbGciOiJSUzI1NiIs..."
    }
```
    
    Returns: Same as /login
    
    Flow:
    1. Verify idToken with Google servers
    2. Extract user info (email, name, picture)
    3. Find or create user in our database
    4. Return our JWT token
    """
    try:
        # Step 1: Verify token with Google
        google_data = await verify_google_token(request.idToken)
        
    except GoogleAuthError as e:
        # Token verification failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    # Step 2: Find or create user in our database
    user = await get_or_create_google_user(db, google_data)
    
    # Step 3: Create our JWT token
    token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "token": token,
        "user": UserResponse.from_user(user)
    }


# ============================================
# POST /api/v1/auth/register
# ============================================
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Request body:
```json
    {
        "name": "John Doe",
        "email": "john@school.edu",
        "password": "securepassword123",
        "department": "Science"
    }
```
    
    Returns: User object (without token - they need to login)
    
    Note: In production, you might want to:
    - Send verification email
    - Require admin approval
    - Add rate limiting
    """
    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hash_password(user_data.password),  # Hash password!
        department=user_data.department,
        role=user_data.role,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)  # Get auto-generated fields (id, created_at)
    
    return UserResponse.from_user(user)


# ============================================
# GET /api/v1/auth/me
# ============================================
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    
    Requires: Authorization header with valid JWT token
    
    Headers:
```
    Authorization: Bearer eyJhbG...
```
    
    Returns: Current user's profile
    
    Note: The user is automatically extracted from the token
    by the get_current_user dependency.
    """
    return UserResponse.from_user(current_user)