# app/services/google_auth.py
"""
Google OAuth service — PKCE authorization code exchange.
"""

import logging
import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleAuthError(Exception):
    logger.debug("GoogleAuthError: %s", str(Exception))
    pass


async def exchange_google_code(
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """
    Exchange a PKCE authorization code for Google tokens and verify id_token.
    """
    web_client_id = settings.google_web_client_id

    logger.debug(
        "Exchanging Google code | client_id=%s redirect_uri=%s",
        web_client_id,
        redirect_uri,
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": web_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )

    if resp.status_code != 200:
        try:
            google_error = resp.json()
            error_code = google_error.get("error", "unknown_error")
            error_desc = google_error.get("error_description", resp.text)
        except Exception:
            error_code = "parse_error"
            error_desc = resp.text

        logger.error(
            "Google token exchange failed | status=%s error=%s desc=%s "
            "redirect_uri=%s client_id=%s",
            resp.status_code,
            error_code,
            error_desc,
            redirect_uri,
            web_client_id,
        )

        if error_code == "redirect_uri_mismatch":
            raise GoogleAuthError(
                f"redirect_uri_mismatch: the redirect URI sent by the frontend "
                f"({redirect_uri!r}) is not registered in Google Cloud Console "
                f"for client {web_client_id!r}."
            )

        raise GoogleAuthError(
            f"Google token exchange failed ({error_code}): {error_desc}"
        )

    token_data = resp.json()

    id_token_jwt = token_data.get("id_token")
    if not id_token_jwt:
        raise GoogleAuthError(
            "Google token exchange did not return an id_token. "
            "Ensure the 'openid' scope is included in the auth request."
        )

    idinfo = None
    last_error = None
    for cid in settings.google_client_ids:
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_jwt,
                google_requests.Request(),
                cid,
            )
            break
        except ValueError as e:
            last_error = e

    # Verify the issuer (who created this token)
    # Must be Google's accounts service
    if idinfo is None:
        raise GoogleAuthError(f"Invalid token: {str(last_error)}")

    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        raise GoogleAuthError("Invalid token issuer")

    return {
        "google_id": idinfo["sub"],
        "email": idinfo["email"],
        "name": idinfo.get("name", ""),
        "avatar": idinfo.get("picture"),
    }


async def get_or_create_google_user(db: AsyncSession, google_data: dict) -> User:
    """Find existing user or create new one from Google data."""
    result = await db.execute(
        select(User).where(User.google_id == google_data["google_id"])
    )
    user = result.scalar_one_or_none()
    if user:
        await db.commit()
        await db.refresh(user)
        return user

    result = await db.execute(select(User).where(User.email == google_data["email"]))
    user = result.scalar_one_or_none()
    if user:
        user.google_id = google_data["google_id"]
        if not user.avatar and google_data.get("avatar"):
            user.avatar = google_data["avatar"]
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        email=google_data["email"],
        name=google_data["name"],
        google_id=google_data["google_id"],
        avatar=google_data.get("avatar"),
        role=UserRole.ADMIN,  # TODO: CHANGE THIS LATER
        hashed_password=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
