# app/services/google_auth.py
"""
Google OAuth service - verifies tokens from frontend.

Flow:
1. User clicks "Sign in with Google" in React Native
2. Google SDK returns idToken
3. Frontend sends idToken to our backend
4. THIS SERVICE verifies the token with Google
5. Creates/finds user in our database
6. Returns our own JWT token
"""

from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User, UserRole

settings = get_settings()


class GoogleAuthError(Exception):
    """Custom exception for Google authentication errors."""

    pass


async def verify_google_token(token: str) -> dict:
    """
    Verify Google ID token and extract user info.

    What this does:
    1. Contacts Google's servers
    2. Verifies token signature
    3. Checks token is for our app (CLIENT_ID)
    4. Checks token is not expired
    5. Returns user info from Google

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
        GoogleAuthError: If token is invalid
    """
    try:
        # Verify the token with Google
        # This makes a network request to Google's servers
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,  # Must match your frontend!
        )

        # Verify the issuer (who created this token)
        # Must be Google's accounts service
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise GoogleAuthError("Invalid token issuer")

        # Extract user information
        return {
            "google_id": idinfo["sub"],  # Unique Google user ID
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),  # May not always be present
            "avatar": idinfo.get("picture"),  # Profile picture URL
        }

    except ValueError as e:
        # Token verification failed
        raise GoogleAuthError(f"Invalid token: {str(e)}")


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
    """

    # ========== Scenario 1: Check by Google ID ==========
    # User has logged in with Google before
    result = await db.execute(
        select(User).where(User.google_id == google_data["google_id"])
    )
    user = result.scalar_one_or_none()

    if user:
        # Found! Return existing user
        return user

    # ========== Scenario 2: Check by Email ==========
    # User might have registered with email/password first
    # Now they're linking their Google account
    result = await db.execute(select(User).where(User.email == google_data["email"]))
    user = result.scalar_one_or_none()

    if user:
        # Found user by email - link their Google account
        user.google_id = google_data["google_id"]

        # Update avatar if they don't have one
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


## 5.8: Understanding the Google OAuth Flow
"""

Here's exactly what happens when a user clicks "Sign in with Google":
```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React Native)                      │
├─────────────────────────────────────────────────────────────────┤
│  1. User clicks "Sign in with Google"                           │
│                    ↓                                             │
│  2. Google SDK opens OAuth popup/screen                         │
│                    ↓                                             │
│  3. User enters Google credentials (to Google, not your app!)   │
│                    ↓                                             │
│  4. Google returns idToken to your app                          │
│     idToken = "eyJhbGciOiJSUzI1NiIs..."                        │
│                    ↓                                             │
│  5. Your app sends idToken to your backend                      │
│     POST /api/v1/auth/google                                    │
│     Body: { "idToken": "eyJhbGciOiJSUzI1NiIs..." }            │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  6. Receive idToken from frontend                               │
│                    ↓                                             │
│  7. verify_google_token(idToken)                                │
│     - Contacts Google servers                                   │
│     - Verifies signature                                        │
│     - Checks CLIENT_ID matches                                  │
│     - Returns: { google_id, email, name, avatar }              │
│                    ↓                                             │
│  8. get_or_create_google_user()                                 │
│     - Find or create user in database                           │
│                    ↓                                             │
│  9. create_access_token()                                       │
│     - Create OUR app's JWT token                                │
│                    ↓                                             │
│  10. Return response                                            │
│      { token: "our_jwt...", user: {...} }                      │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React Native)                      │
├─────────────────────────────────────────────────────────────────┤
│  11. Store our JWT token                                        │
│      AsyncStorage.setItem('token', response.token)              │
│                    ↓                                             │
│  12. Use token for all future API requests                      │
│      Authorization: Bearer our_jwt...                           │
└─────────────────────────────────────────────────────────────────┘
"""
