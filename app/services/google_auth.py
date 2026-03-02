# app/services/google_auth.py
"""
Google OAuth service - verifies tokens from frontend.

Flow:
1. User clicks "Sign in with Google" in React Native
2. Google SDK returns idToken (web: `credential`) to frontend
3. Frontend sends idToken to our backend
4. THIS SERVICE verifies the token with Google
5. Creates/finds user in our database
6. Returns our own JWT token

References:
- Google token verification docs: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- google-auth Python library: https://google-auth.readthedocs.io/en/master/reference/google.oauth2.id_token.html
- Why run_in_executor for sync I/O in async FastAPI: https://fastapi.tiangolo.com/async/#very-technical-details
"""

import asyncio
from functools import partial
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User, UserRole

settings = get_settings()
_google_request = requests.Request()


class GoogleAuthError(Exception):
    """Custom exception for Google authentication errors."""

    pass


async def verify_google_token(token: str) -> dict:
    """
    Verify Google ID token and extract user info.

    What this does:
    1. Contacts Google's servers to fetch their public keys (if not cached)
    2. Verifies token signature
    3. Checks that the `aud` (audience) field matches one of our client IDs
    4. Checks token is not expired
    5. Returns user info from the verified payload

    Args:
        token: The idToken from frontend (Google JWT)

    Returns:
        Dict with user info:
        {
            "google_id": "1234567890",
            "email": "user@gmail.com",
            "name": "John Doe",
            "avatar": "https://lh3.googleusercontent.com/..."
        }

    Raises:
        GoogleAuthError: If token cannot be verified with any client ID.

    References:
        https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
        https://google-auth.readthedocs.io/en/master/reference/google.oauth2.id_token.html
    """
    loop = asyncio.get_event_loop()
    idinfo = None
    last_error = None

    for client_id in settings.google_client_ids:
        try:
            idinfo = await loop.run_in_executor(
                None,
                partial(
                    id_token.verify_oauth2_token,
                    token,
                    _google_request,
                    client_id,
                ),
            )
            break
        except ValueError as e:
            last_error = e
            continue

    # Verify the issuer (who created this token)
    # Must be Google's accounts service
    if idinfo is None:
        raise GoogleAuthError(f"Invalid token: {str(last_error)}")

    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        raise GoogleAuthError("Invalid token issuer")

    # Extract user information
    return {
        "google_id": idinfo["sub"],  # Unique Google user ID
        "email": idinfo["email"],
        "name": idinfo.get("name", ""),  # May not always be present
        "avatar": idinfo.get("picture"),  # Profile picture URL
    }


async def get_or_create_google_user(db: AsyncSession, google_data: dict) -> User:
    """
    Find existing user or create new one from Google data.

    Three scenarios:
    1. User exists with this google_id → Return existing user
    2. User exists with this email (registered before) → Link Google account
    3. New user → Create account

    Args:
        db: Database session
        google_data: Dict from verify_google_token()

    Returns:
        User object (existing or newly created)

    References:
        https://developers.google.com/identity/gsi/web/guides/overview
    """

    # ========== Scenario 1: Check by Google ID ==========
    # User has logged in with Google before
    result = await db.execute(
        select(User).where(User.google_id == google_data["google_id"])
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    # ========== Scenario 2: Check by Email ==========
    # User might have registered with email/password first
    # Now they're linking their Google account
    result = await db.execute(select(User).where(User.email == google_data["email"]))
    user = result.scalar_one_or_none()

    if user:
        user.google_id = google_data["google_id"]
        if not user.avatar and google_data.get("avatar"):
            user.avatar = google_data["avatar"]
        await db.commit()
        await db.refresh(user)
        return user

    # ========== Scenario 3: Create New User ==========
    # Completely new user signing up with Google
    user = User(
        email=google_data["email"],
        name=google_data["name"],
        google_id=google_data["google_id"],
        avatar=google_data.get("avatar"),
        role=UserRole.STUDENT,  # Default role for new users
        hashed_password=None,  # No password for Google users
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
