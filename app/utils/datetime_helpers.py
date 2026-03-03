# app/utils/datetime_helpers.py
"""
Datetime helpers that enforce a single rule throughout the codebase:

    RULE: asyncpg / PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns require
          *naive* datetimes. All Python business logic should use *aware* UTC
          datetimes. Convert at the DB boundary, not touching schema.

    utc_now()  → aware UTC datetime  (use in Python logic / comparisons)
    to_db(dt)  → naive UTC datetime  (use before writing to DB or in query args)
    from_db(dt)→ aware UTC datetime  (use after reading from DB)
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_db(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Strip tzinfo so asyncpg can write to a TIMESTAMP WITHOUT TIME ZONE column.

    Assumes the value is already UTC. Naive datetimes are returned unchanged.
    Aware datetimes have their tzinfo annotation removed.

    Usage:
        user.drive_token_expiry = to_db(utc_now() + timedelta(hours=1))
        await db.scalar(select(User).where(User.created_at >= to_db(cutoff)))
    """
    if dt is None:
        return None
    return dt.replace(tzinfo=None)


def from_db(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Re-attach UTC tzinfo to a naive datetime read from the DB.

    asyncpg returns naive datetimes for TIMESTAMP WITHOUT TIME ZONE columns.
    We treat all stored timestamps as UTC and re-annotate them so Python
    comparisons and google-auth's Credentials.expired work correctly.

    Usage:
        expiry = from_db(user.drive_token_expiry)
        if expiry and expiry < utc_now():
            ...  # token expired
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)
