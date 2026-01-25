# app/schemas/user.py
"""
User schemas for request/response validation.

Separates what we receive (Create/Update) from what we send (Response).
"""

from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserBase(BaseModel):
    """
    Base schema with common fields.

    Other schemas inherit from this to avoid repetition (DRY principle).
    """

    name: str
    email: EmailStr
    department: str | None = None


class UserCreate(UserBase):
    """
    Schema for creating a new user (registration).

    Includes password (only time we accept password from client).

    Example request:
    {
        "name": "John Doe",
        "email": "john@school.edu",
        "password": "secretpassword123",
        "department": "Science"
    }
    """

    password: str
    role: UserRole = UserRole.STUDENT  # Default role

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john@school.edu",
                "password": "secretpassword123",
                "department": "Science",
                "role": "STUDENT",
            }
        }
    }


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    All fields optional - only update what's provided.

    Example request:
    {
        "name": "John Smith",
        "department": "Mathematics"
    }
    """

    name: str | None = None
    department: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {"name": "John Smith", "department": "Mathematics"}
        }
    }


class UserResponse(BaseModel):
    """
    Schema for user data in API responses.

    NEVER includes password or sensitive internal fields.

    Note: 'id' is string to match your frontend API spec.

    Example response:
    {
        "id": "1",
        "name": "John Doe",
        "email": "john@school.edu",
        "role": "TEACHER",
        "avatar": "https://...",
        "department": "Science"
    }
    """

    id: str  # String to match your API spec
    name: str
    email: str
    role: UserRole
    avatar: str | None = None
    department: str | None = None

    model_config = {
        # Allows creating from SQLAlchemy model
        "from_attributes": True
    }

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """
        Create UserResponse from SQLAlchemy User model.

        Why a custom method?
        - Converts int id to string
        - Ensures consistent transformation

        Usage:
            user = await db.get(User, 1)
            response = UserResponse.from_user(user)
        """
        return cls(
            id=str(user.id),  # Convert int to string
            name=user.name,
            email=user.email,
            role=user.role,
            avatar=user.avatar,
            department=user.department,
        )
