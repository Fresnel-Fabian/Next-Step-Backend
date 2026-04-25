# app/schemas/invitation.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.invitation import InvitationStatus
from app.models.user import UserRole


class InviteRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.STUDENT  # defaults to STUDENT if not provided


class InvitationResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    status: InvitationStatus
    invite_link: str
    expires_at: datetime
    created_at: datetime


class BulkInviteResponse(BaseModel):
    invited: list[str]   # successfully invited
    skipped: list[str]   # already a user or already has pending invite
    failed: list[str]    # invalid emails or other errors