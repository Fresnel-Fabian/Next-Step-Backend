# app/services/__init__.py
"""
Services package.

Business logic separated from routes.
"""

from app.services.activity import log_activity
from app.services.auth import (
    authenticate_user,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.google_auth import (
    GoogleAuthError,
    exchange_google_code,
    get_or_create_google_user,
)

__all__ = [
    # Auth
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "authenticate_user",
    # Google Auth
    "GoogleAuthError",
    "exchange_google_code",
    "get_or_create_google_user",
    # Activity
    "log_activity",
]
