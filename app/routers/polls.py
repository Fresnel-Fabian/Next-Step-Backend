# app/routers/polls.py
"""
Poll routes.

Endpoints:
- GET   /api/v1/polls              - List polls
- GET   /api/v1/polls/{id}         - Get specific poll
- POST  /api/v1/polls              - Create poll (admin)
- POST  /api/v1/polls/{id}/vote    - Vote on poll
- PATCH /api/v1/polls/{id}/close   - Close poll (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.database import get_db
from app.schemas.poll import (
    PollCreate,
    PollResponse,
    PollOptionResponse,
    VoteRequest,
)
from app.dependencies import get_current_user, require_admin
from app.models import User, Poll, PollVote
from app.services.activity import log_activity

router = APIRouter(
    prefix="/api/v1/polls",
    tags=["Polls"]
)


async def build_poll_response(db: AsyncSession, poll: Poll) -> PollResponse:
    """
    Build PollResponse with calculated vote counts and percentages.
    
    This is a helper function because we need to:
    1. Count votes for each option
    2. Calculate percentages
    3. Build the response object
    """
    
    # Get vote counts grouped by option_id
    vote_counts_result = await db.execute(
        select(PollVote.option_id, func.count(PollVote.id))
        .where(PollVote.poll_id == poll.id)
        .group_by(PollVote.option_id)
    )
    
    # Convert to dict: {option_id: count}
    votes_map = dict(vote_counts_result.all())
    
    # Calculate total votes
    total_votes = sum(votes_map.values())
    
    # Build options with vote counts and percentages
    options = []
    for opt in poll.options.get("options", []):
        vote_count = votes_map.get(opt["id"], 0)
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        
        options.append(PollOptionResponse(
            id=opt["id"],
            text=opt["text"],
            votes=vote_count,
            percentage=round(percentage, 1)  # Round to 1 decimal
        ))
    
    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        options=options,
        isActive=poll.is_active,
        totalVotes=total_votes,
        createdAt=poll.created_at,
        expiresAt=poll.expires_at
    )


@router.get("", response_model=list[PollResponse])
async def list_polls(
    status: str | None = Query(None, description="Filter: 'active' or 'completed'"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    List polls with optional status filtering.
    
    Query parameters:
    - status: "active" for open polls, "completed" for closed polls
    
    Returns polls with calculated vote percentages.
    """
    
    query = select(Poll)
    
    # Filter by status
    if status == "active":
        query = query.where(Poll.is_active == True)
    elif status == "completed":
        query = query.where(Poll.is_active == False)
    
    # Order by creation date (newest first)
    query = query.order_by(Poll.created_at.desc())
    
    result = await db.execute(query)
    polls = result.scalars().all()
    
    # Build response with vote counts for each poll
    response = []
    for poll in polls:
        poll_response = await build_poll_response(db, poll)
        response.append(poll_response)
    
    return response


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    Get a specific poll by ID with vote counts.
    """
    
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    return await build_poll_response(db, poll)


@router.post("", response_model=PollResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(
    data: PollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Create a new poll.
    
    Requires admin role.
    
    Request body:
    {
        "title": "Best meeting day?",
        "description": "Vote for your preferred day",
        "options": [
            {"id": 1, "text": "Monday"},
            {"id": 2, "text": "Wednesday"},
            {"id": 3, "text": "Friday"}
        ],
        "expires_at": "2024-12-31T23:59:59Z"
    }
    """
    
    # Convert options to storage format
    options_dict = {
        "options": [{"id": o.id, "text": o.text} for o in data.options]
    }
    
    poll = Poll(
        title=data.title,
        description=data.description,
        options=options_dict,
        expires_at=data.expires_at,
        created_by=current_user.id,
        is_active=True
    )
    
    db.add(poll)
    await db.flush()
    
    # Log activity
    await log_activity(
        db,
        title=f"Poll Created: {data.title}",
        author=current_user.name,
        action_type="create",
        entity_type="poll",
        entity_id=poll.id
    )
    
    await db.commit()
    await db.refresh(poll)
    
    return await build_poll_response(db, poll)


@router.post("/{poll_id}/vote")
async def vote_on_poll(
    poll_id: int,
    data: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cast a vote on a poll.
    
    Constraints:
    - Poll must be active
    - Poll must not be expired
    - User can only vote once per poll
    - Option must be valid
    
    Request body:
    {
        "option_id": 2
    }
    """
    
    # Get the poll
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Check if poll is active
    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is closed"
        )
    
    # Check if poll is expired
    if poll.expires_at and poll.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll has expired"
        )
    
    # Check if user already voted
    existing_vote = await db.execute(
        select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == current_user.id
        )
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already voted on this poll"
        )
    
    # Validate option_id exists in poll options
    valid_option_ids = [o["id"] for o in poll.options.get("options", [])]
    if data.option_id not in valid_option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid option"
        )
    
    # Create vote
    vote = PollVote(
        poll_id=poll_id,
        user_id=current_user.id,
        option_id=data.option_id
    )
    
    db.add(vote)
    await db.commit()
    
    return {"message": "Vote recorded successfully"}


@router.patch("/{poll_id}/close")
async def close_poll(
    poll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Close a poll (stop accepting votes).
    
    Requires admin role.
    """
    
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is already closed"
        )
    
    poll.is_active = False
    
    # Log activity
    await log_activity(
        db,
        title=f"Poll Closed: {poll.title}",
        author=current_user.name,
        action_type="close",
        entity_type="poll",
        entity_id=poll_id
    )
    
    await db.commit()
    
    return {"message": "Poll closed successfully"}