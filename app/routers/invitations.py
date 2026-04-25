# app/routers/invitations.py
import csv
import io
import secrets
import aiosmtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_admin
from app.models import User, Invitation
from app.models.invitation import InvitationStatus
from app.models.user import UserRole
from app.schemas.invitation import InviteRequest, InvitationResponse, BulkInviteResponse
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/invitations", tags=["Invitations"])

INVITE_EXPIRY_DAYS = 7


def make_invite_link(token: str) -> str:
    return f"{settings.frontend_url}/invite?token={token}"


def build_email(to: str, role: str, invite_link: str) -> MIMEMultipart:
    """Build the HTML invite email."""
    role_label = role.capitalize()
    sender = settings.mail_from or settings.mail_username

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"You're invited to join Next Step as a {role_label}"
    msg["From"] = f"{settings.mail_from_name} <{sender}>"
    msg["To"] = to

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #F9FAFB; padding: 32px;">
        <div style="max-width: 480px; margin: auto; background: white; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB;">
          <h2 style="color: #111827; margin-bottom: 8px;">You've been invited!</h2>
          <p style="color: #6B7280; margin-bottom: 24px;">
            You've been invited to join <strong>Next Step</strong> as a <strong>{role_label}</strong>.
          </p>
          <a href="{invite_link}"
             style="display: inline-block; background: #2563EB; color: white; padding: 14px 28px;
                    border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;">
            Accept Invitation
          </a>
          <p style="color: #9CA3AF; font-size: 12px; margin-top: 24px;">
            This link expires in {INVITE_EXPIRY_DAYS} days. If you didn't expect this email, you can ignore it.
          </p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))
    return msg


async def send_invite_email(to: str, role: str, invite_link: str) -> None:
    """Send invite email via Gmail SMTP. Logs warning on failure instead of crashing."""
    if not settings.mail_username or not settings.mail_password:
        logger.warning("Email not configured — skipping email send for %s", to)
        return

    try:
        msg = build_email(to, role, invite_link)
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.mail_username,
            password=settings.mail_password,
        )
        logger.info("Invite email sent to %s", to)
    except Exception as e:
        # Don't crash the request if email fails — just log it
        logger.error("Failed to send invite email to %s: %s", to, str(e))


async def create_invite(email: str, role: UserRole, admin: User, db: AsyncSession) -> Invitation:
    """Create a single invitation record."""
    token = secrets.token_urlsafe(32)
    invite = Invitation(
        email=email.lower(),
        token=token,
        role=role,
        created_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


def to_response(invite: Invitation) -> InvitationResponse:
    """Convert Invitation model to InvitationResponse schema."""
    return InvitationResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        invite_link=make_invite_link(invite.token),
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.post("/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: InviteRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Invite a single student or teacher by email.
    Admin only. Sends an invite email and returns the invite link.

    Request body:
    {
        "email": "user@gmail.com",
        "role": "STUDENT"   // or "TEACHER"
    }
    """
    email = data.email.lower()

    # Check if already a user
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    # Check if already has a pending invite
    existing_invite = await db.scalar(
        select(Invitation).where(
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING,
        )
    )
    if existing_invite and existing_invite.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email already has a pending invitation.",
        )

    invite = await create_invite(email, data.role, admin, db)

    # Send invite email (non-blocking — won't crash if email fails)
    await send_invite_email(
        to=email,
        role=data.role.value,
        invite_link=make_invite_link(invite.token),
    )

    return to_response(invite)


@router.post("/invite/bulk", response_model=BulkInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_bulk(
    file: UploadFile = File(..., description="CSV file with one email per row"),
    role: UserRole = Query(UserRole.STUDENT, description="Role for all invited users: STUDENT or TEACHER"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Invite multiple users via CSV upload.
    All emails in the CSV will be assigned the same role and each will receive an invite email.

    Query parameter:
    - role: STUDENT (default) or TEACHER

    CSV format — one email per row:
        email
        user1@gmail.com
        user2@gmail.com
    """
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.reader(io.StringIO(text))

    emails = []
    for row in reader:
        if not row:
            continue
        cell = row[0].strip().lower()
        if cell == "email" or not cell:
            continue
        emails.append(cell)

    if not emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No emails found in the CSV file.",
        )

    invited, skipped, failed = [], [], []

    for email in emails:
        try:
            existing_user = await db.scalar(select(User).where(User.email == email))
            if existing_user:
                skipped.append(email)
                continue

            existing_invite = await db.scalar(
                select(Invitation).where(
                    Invitation.email == email,
                    Invitation.status == InvitationStatus.PENDING,
                )
            )
            if existing_invite and existing_invite.is_valid():
                skipped.append(email)
                continue

            invite = await create_invite(email, role, admin, db)

            # Send invite email (non-blocking)
            await send_invite_email(
                to=email,
                role=role.value,
                invite_link=make_invite_link(invite.token),
            )

            invited.append(email)

        except Exception as e:
            logger.error("Failed to invite %s: %s", email, str(e))
            failed.append(email)

    return BulkInviteResponse(invited=invited, skipped=skipped, failed=failed)

@router.get("/validate")
async def validate_invite(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Validate an invite token and return basic info. No auth required."""
    invite = await db.scalar(select(Invitation).where(Invitation.token == token))

    if not invite or not invite.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite link is invalid or has expired.",
        )

    return {
        "email": invite.email,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat(),
    }


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    role: UserRole | None = Query(None, description="Filter by role: STUDENT or TEACHER"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all invitations. Optionally filter by role. Admin only."""
    query = select(Invitation).order_by(Invitation.created_at.desc())

    if role:
        query = query.where(Invitation.role == role.value)

    result = await db.execute(query)
    return [to_response(i) for i in result.scalars().all()]

@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Cancel/delete a pending invitation. Admin only."""
    invite = await db.scalar(select(Invitation).where(Invitation.id == invitation_id))

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invite.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending invitations can be cancelled.",
        )

    await db.delete(invite)
    await db.commit()
