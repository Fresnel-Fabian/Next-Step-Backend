# app/routers/polls.py
"""
Poll routes.

Endpoints:
- GET    /api/v1/polls                  - List polls (authenticated)
- GET    /api/v1/polls/{id}             - Get specific poll (authenticated)
- POST   /api/v1/polls                  - Create poll (admin only)
- POST   /api/v1/polls/{id}/vote        - Vote on poll (authenticated)
- GET    /api/v1/polls/{id}/results     - Full results (admin + teacher)
- PATCH  /api/v1/polls/{id}/close       - Close poll (admin only)
- DELETE /api/v1/polls/{id}             - Delete poll (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_db
from app.schemas.poll import (
    PollCreate,
    PollResponse,
    PollOptionResponse,
    VoteRequest,
    PollResultsResponse,
    VoterDetail,
)
from app.dependencies import get_current_user, require_admin, require_roles
from app.models import User, Poll, PollVote
from app.models.user import UserRole
from app.services.activity import log_activity
from app.services.notifications import broadcast_to_all

router = APIRouter(prefix="/api/v1/polls", tags=["Polls"])


async def build_poll_response(db: AsyncSession, poll: Poll) -> PollResponse:
    vote_counts_result = await db.execute(
        select(PollVote.option_id, func.count(PollVote.id))
        .where(PollVote.poll_id == poll.id)
        .group_by(PollVote.option_id)
    )
    votes_map = dict(vote_counts_result.all())
    total_votes = sum(votes_map.values())

    options = []
    for opt in poll.options.get("options", []):
        vote_count = votes_map.get(opt["id"], 0)
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        options.append(
            PollOptionResponse(
                id=opt["id"],
                text=opt["text"],
                votes=vote_count,
                percentage=round(percentage, 1),
            )
        )

    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        options=options,
        isActive=poll.is_active,
        totalVotes=total_votes,
        createdAt=poll.created_at,
        expiresAt=poll.expires_at,
    )


@router.get("", response_model=list[PollResponse])
async def list_polls(
    poll_status: str | None = Query(None, description="Filter: 'active' or 'completed'"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Poll)

    if poll_status == "active":
        query = query.where(Poll.is_active == True)
    elif poll_status == "completed":
        query = query.where(Poll.is_active == False)

    query = query.order_by(Poll.created_at.desc())
    result = await db.execute(query)
    polls = result.scalars().all()
    now = datetime.now(timezone.utc)
    for poll in polls:
        if poll.is_active and poll.expires_at and poll.expires_at.replace(tzinfo=timezone.utc) < now:
            poll.is_active = False
    await db.commit()

    return [await build_poll_response(db, poll) for poll in polls]


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    return await build_poll_response(db, poll)


@router.post("", response_model=PollResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(
    data: PollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    options_dict = {"options": [{"id": o.id, "text": o.text} for o in data.options]}

    poll = Poll(
        title=data.title,
        description=data.description,
        options=options_dict,
        expires_at=data.expires_at,
        created_by=current_user.id,
        is_active=True,
    )

    db.add(poll)
    await db.flush()

    # Broadcast notification to all users when poll is created
    await broadcast_to_all(
        db,
        title=f"New Poll: {data.title}",
        message=data.description or f"A new poll has been created. Cast your vote now.",
        notification_type="info",
        entity_type="poll",
    )

    await log_activity(
        db,
        title=f"Poll Created: {data.title}",
        author=current_user.name,
        action_type="create",
        entity_type="poll",
        entity_id=poll.id,
    )

    await db.commit()
    await db.refresh(poll)

    return await build_poll_response(db, poll)


@router.post("/{poll_id}/vote")
async def vote_on_poll(
    poll_id: int,
    data: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Poll is closed"
        )

    if poll.expires_at and poll.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Poll has expired"
        )

    existing_vote = await db.execute(
        select(PollVote).where(
            PollVote.poll_id == poll_id, PollVote.user_id == current_user.id
        )
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already voted on this poll",
        )

    valid_option_ids = [o["id"] for o in poll.options.get("options", [])]
    if data.option_id not in valid_option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid option"
        )

    vote = PollVote(poll_id=poll_id, user_id=current_user.id, option_id=data.option_id)
    db.add(vote)
    await db.commit()

    return {"message": "Vote recorded successfully"}


@router.get("/{poll_id}/results", response_model=PollResultsResponse)
async def get_poll_results(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    option_map = {o["id"]: o["text"] for o in poll.options.get("options", [])}

    votes_result = await db.execute(
        select(PollVote, User)
        .join(User, PollVote.user_id == User.id)
        .where(PollVote.poll_id == poll_id)
        .order_by(PollVote.created_at.desc())
    )
    vote_rows = votes_result.all()

    voters = [
        VoterDetail(
            user_id=vote.user_id,
            user_name=user.name,
            option_id=vote.option_id,
            option_text=option_map.get(vote.option_id, "Unknown"),
            voted_at=vote.created_at,
        )
        for vote, user in vote_rows
    ]

    poll_summary = await build_poll_response(db, poll)

    return PollResultsResponse(
        poll_id=poll.id,
        title=poll.title,
        total_votes=poll_summary.totalVotes,
        options=poll_summary.options,
        voters=voters,
    )


@router.patch("/{poll_id}/close")
async def close_poll(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Poll is already closed"
        )

    poll.is_active = False

    await log_activity(
        db,
        title=f"Poll Closed: {poll.title}",
        author=current_user.name,
        action_type="close",
        entity_type="poll",
        entity_id=poll_id,
    )

    await db.commit()
    return {"message": "Poll closed successfully"}


@router.delete("/{poll_id}")
async def delete_poll(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    await db.delete(poll)

    await log_activity(
        db,
        title=f"Poll Deleted: {poll.title}",
        author=current_user.name,
        action_type="delete",
        entity_type="poll",
        entity_id=poll_id,
    )

    await db.commit()
    return {"message": "Poll deleted successfully"}

class UpdateExpiryRequest(BaseModel):
    expires_at: datetime


@router.patch("/{poll_id}/expiry")
async def update_poll_expiry(
    poll_id: int,
    data: UpdateExpiryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update the expiry date of a poll. Admin only."""
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    if not poll.is_active:
        raise HTTPException(status_code=400, detail="Cannot update expiry of a closed poll")

    poll.expires_at = data.expires_at

    await log_activity(
        db,
        title=f"Poll Expiry Updated: {poll.title}",
        author=current_user.name,
        action_type="update",
        entity_type="poll",
        entity_id=poll_id,
    )

    await db.commit()
    return {"message": "Poll expiry updated", "expires_at": poll.expires_at}