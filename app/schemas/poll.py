# app/schemas/poll.py
"""
Poll schemas for request/response validation.

Endpoints:
- GET /api/v1/polls
- POST /api/v1/polls
- POST /api/v1/polls/{id}/vote
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
        "text": "Monday"
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
        "text": "Monday",
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
        "title": "Best day for staff meetings?",
        "description": "Vote for your preferred meeting day",
        "options": [
            {"id": 1, "text": "Monday"},
            {"id": 2, "text": "Wednesday"},
            {"id": 3, "text": "Friday"}
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
                "title": "Best day for staff meetings?",
                "description": "Vote for your preferred meeting day",
                "options": [
                    {"id": 1, "text": "Monday"},
                    {"id": 2, "text": "Wednesday"},
                    {"id": 3, "text": "Friday"}
                ],
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }
    }


class PollResponse(BaseModel):
    """
    Schema for poll in API responses.
    
    Includes calculated vote percentages for each option.
    
    Example response:
    {
        "id": 1,
        "title": "Best day for staff meetings?",
        "description": "Vote for your preferred day",
        "options": [
            {"id": 1, "text": "Monday", "votes": 15, "percentage": 45.5},
            {"id": 2, "text": "Wednesday", "votes": 10, "percentage": 30.3},
            {"id": 3, "text": "Friday", "votes": 8, "percentage": 24.2}
        ],
        "isActive": true,
        "totalVotes": 33,
        "createdAt": "2024-01-15T10:30:00Z",
        "expiresAt": "2024-12-31T23:59:59Z"
    }
    """
    id: int
    title: str
    description: str | None
    options: list[PollOptionResponse]
    isActive: bool  # camelCase
    totalVotes: int  # camelCase
    createdAt: datetime  # camelCase
    expiresAt: datetime | None  # camelCase
    
    model_config = {
        "from_attributes": True
    }


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
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "option_id": 2
            }
        }
    }