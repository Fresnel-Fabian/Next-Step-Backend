# app/routers/auth.py
"""
Authentication routes.

Endpoints:
- POST /api/v1/auth/login    - Email/password login
- POST /api/v1/auth/google   - Google PKCE code exchange login
- POST /api/v1/auth/register - Create new account
- GET  /api/v1/auth/me       - Get current user profile
- GET  /api/v1/auth/drive-token - Return a valid Drive access token

ref: https://developers.google.com/identity/protocols/oauth2/native-app
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
    exchange_google_code,
    get_or_create_google_user,
    GoogleAuthError,
)
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# POST /api/v1/auth/logi
@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
        Authenticate user with email and password.
        Returns user with role (ADMIN, TEACHER, STUDENT) - frontend routes based on role.

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
                "role": "STUDENT",
                "avatar": null,
                "department": "Science"
            }
        }
    ```
    """
    user = await authenticate_user(db, request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return {"token": token, "user": UserResponse.from_user(user)}


# POST /api/v1/auth/google
@router.post("/google")
async def google_auth(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with a Google PKCE authorization code.

    The Expo frontend uses ResponseType.Code to obtain an authorization code
    and a PKCE code verifier, then sends them here. The backend exchanges the
    code with Google to receive id_token, access_token, and refresh_token.

    Request:
    ```json
    {
        "code": "4/0AX4XfWh...",
        "codeVerifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        "redirectUri": "exp://192.168.1.5:19000"
    }
    ```

    Returns `{ token, user }`.
    """
    try:
        google_data = await exchange_google_code(
            code=request.code,
            code_verifier=request.codeVerifier,
            redirect_uri=request.redirectUri,
        )
    except GoogleAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user = await get_or_create_google_user(db, google_data)
    token = create_access_token(data={"sub": str(user.id)})
    return {"token": token, "user": UserResponse.from_user(user)}


# POST /api/v1/auth/register
@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
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
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hash_password(user_data.password),
        department=user_data.department,
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_user(user)


# GET /api/v1/auth/me
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return UserResponse.from_user(current_user)


# GET /api/v1/auth/drive-token
@router.get("/drive-token")
async def get_drive_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a valid Drive access token, refreshing it if expired.

    The frontend calls this before making direct Drive API requests to ensure
    its cached token is still valid.
    """
    from app.services.google_drive import get_drive_service, DriveAuthError

    try:
        await get_drive_service(current_user, db)
        return {"access_token": current_user.drive_access_token}
    except DriveAuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
