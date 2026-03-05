# app/schemas/poll.py
"""
Poll schemas for request/response validation.

Endpoints:
- GET  /api/v1/polls
- GET  /api/v1/polls/{id}
- POST /api/v1/polls
- POST /api/v1/polls/{id}/vote
- GET  /api/v1/polls/{id}/results  (admin only)
- PATCH /api/v1/polls/{id}/close
"""

from pydantic import BaseModel
from datetime import datetime


class PollOptionInput(BaseModel):
    """
    Schema for poll option in create request.

    Example:
    {
        "id": 1,
        "text": "Pizza"
    }
    """
    id: int
    text: str


class PollOptionResponse(BaseModel):
    """
    Schema for poll option in response (includes vote counts).

    Example:
    {
        "id": 1,
        "text": "Pizza",
        "votes": 15,
        "percentage": 45.5
    }
    """
    id: int
    text: str
    votes: int = 0
    percentage: float = 0.0


class PollCreate(BaseModel):
    """
    Schema for creating a new poll.

    Request body for POST /api/v1/polls

    Example:
    {
        "title": "What should we serve for lunch?",
        "description": "Vote for your preferred meal",
        "options": [
            {"id": 1, "text": "Pizza"},
            {"id": 2, "text": "Burger"},
            {"id": 3, "text": "Salad"}
        ],
        "expires_at": "2024-12-31T23:59:59Z"
    }
    """
    title: str
    description: str | None = None
    options: list[PollOptionInput]
    expires_at: datetime | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "What should we serve for lunch?",
                "description": "Vote for your preferred meal",
                "options": [
                    {"id": 1, "text": "Pizza"},
                    {"id": 2, "text": "Burger"},
                    {"id": 3, "text": "Salad"},
                ],
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }
    }


class PollResponse(BaseModel):
    """
    Schema for poll in API responses.
    Includes calculated vote percentages for each option.
    """
    id: int
    title: str
    description: str | None
    options: list[PollOptionResponse]
    isActive: bool
    totalVotes: int
    createdAt: datetime
    expiresAt: datetime | None

    model_config = {"from_attributes": True}


class VoteRequest(BaseModel):
    """
    Schema for casting a vote.

    Request body for POST /api/v1/polls/{id}/vote

    Example:
    {
        "option_id": 2
    }
    """
    option_id: int

    model_config = {"json_schema_extra": {"example": {"option_id": 2}}}


# ── Admin-only schemas ───────────────────────────────────────────

class VoterDetail(BaseModel):
    """
    Individual voter info.
    Only exposed to admin via GET /api/v1/polls/{id}/results
    """
    user_id: int
    user_name: str
    option_id: int
    option_text: str
    voted_at: datetime


class PollResultsResponse(BaseModel):
    """
    Full poll results with voter breakdown.
    Admin only.
    """
    poll_id: int
    title: str
    total_votes: int
    options: list[PollOptionResponse]
    voters: list[VoterDetail]