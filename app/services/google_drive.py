# app/services/google_drive.py
"""
Google Drive API service.

- Perform expiry check ourselves using utc_now() vs from_db(user.drive_token_expiry) (always
  aware). Then pass expiry=None to Credentials so google-auth never tries to do its own comparison
  since their versioning issues keep on having type mismatches between naive and aware datetimes.
"""

import asyncio

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.utils.datetime_helpers import from_db, to_db, utc_now

settings = get_settings()


class DriveAuthError(Exception):
    """Raised when a user has no Drive tokens or tokens cannot be refreshed."""

    pass


async def get_drive_service(user, db: AsyncSession):
    """
    Build an authenticated Drive API v3 client for a specific user.
    Refreshes the access token when it is expired.

    Args:
        user: User model instance — must have drive_access_token set.
        db:   AsyncSession for writing refreshed tokens back to the DB.

    Returns:
        Authenticated Google Drive API service object (v3).

    Raises:
        DriveAuthError: If the user has no tokens or refresh fails.
    """
    if not user.drive_access_token:
        raise DriveAuthError(
            "User has no Drive access token. "
            "They must sign in with Google and grant Drive permissions."
        )

    expiry_aware = from_db(user.drive_token_expiry)  # None or aware UTC datetime
    token_is_expired = expiry_aware is not None and utc_now() >= expiry_aware

    if not token_is_expired:
        # Token is still valid — build the service immediately without refresh.
        creds = Credentials(
            token=user.drive_access_token,
            refresh_token=user.drive_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_ids[0],
            client_secret=settings.google_client_secret,
            expiry=None,  # skip google-auth's internal expiry comparison
        )
        return build("drive", "v3", credentials=creds)

    # Token is expired — try each registered client ID for refresh.
    # (The refresh token is bound to whichever client ID was used at first login.)
    refresh_error: Exception | None = None

    for client_id in settings.google_client_ids:
        if not user.drive_refresh_token:
            break

        creds = Credentials(
            token=user.drive_access_token,
            refresh_token=user.drive_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=settings.google_client_secret,
            expiry=None,  # skip internal comparison during refresh too
        )

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, creds.refresh, Request())

            user.drive_access_token = creds.token
            if creds.expiry:
                user.drive_token_expiry = to_db(creds.expiry)
            await db.commit()

            return build("drive", "v3", credentials=creds)

        except Exception as e:
            refresh_error = e
            continue

    detail = (
        str(refresh_error)
        if refresh_error
        else "Token expired and no refresh token available"
    )
    raise DriveAuthError(f"Could not obtain valid Drive credentials: {detail}")


async def get_shared_with_me(user, db: AsyncSession) -> list[dict]:
    """Fetch files shared with this user from Google Drive."""
    service = await get_drive_service(user, db)
    results = (
        service.files()
        .list(
            q="sharedWithMe=true",
            fields=(
                "files("
                "  id, name, mimeType, webViewLink, webContentLink, size,"
                "  owners(emailAddress, displayName), sharedWithMeTime"
                ")"
            ),
            pageSize=50,
        )
        .execute()
    )
    return results.get("files", [])


async def set_file_permission(
    file_id: str,
    user,
    db: AsyncSession,
    role: str = "reader",
    permission_type: str = "domain",
    domain: str = None,
) -> str:
    """Set sharing permission on a Drive file. Returns permissionId."""
    service = await get_drive_service(user, db)
    body: dict = {"role": role, "type": permission_type}
    if permission_type == "domain" and domain:
        body["domain"] = domain
    permission = (
        service.permissions().create(fileId=file_id, body=body, fields="id").execute()
    )
    return permission["id"]


async def revoke_file_permission(
    file_id: str,
    permission_id: str,
    user,
    db: AsyncSession,
) -> None:
    """Revoke a sharing permission from a Drive file."""
    service = await get_drive_service(user, db)
    service.permissions().delete(
        fileId=file_id,
        permissionId=permission_id,
    ).execute()
