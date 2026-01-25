# app/schemas/auth.py
"""
Authentication schemas for request/response validation.

These define the exact shape of data for:
- Login requests
- Google OAuth requests  
- Token responses
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """
    Schema for email/password login.
    
    Example request body:
    {
        "email": "user@school.edu",
        "password": "secretpassword123"
    }
    """
    email: EmailStr  # Validates email format automatically!
    password: str
    
    # Pydantic V2 config
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "teacher@school.edu",
                "password": "mypassword123"
            }
        }
    }


class GoogleAuthRequest(BaseModel):
    """
    Schema for Google OAuth login.
    
    The frontend sends the idToken received from Google.
    
    Example request body:
    {
        "idToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    """
    idToken: str  # JWT token from Google (camelCase to match frontend)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "idToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class Token(BaseModel):
    """
    Schema for token response (returned after successful login).
    
    Example response:
    {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": { ... }
    }
    """
    token: str
    user: "UserResponse"  # Forward reference (defined in user.py)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "1",
                    "name": "John Doe",
                    "email": "john@school.edu",
                    "role": "TEACHER",
                    "avatar": None,
                    "department": "Science"
                }
            }
        }
    }


class TokenData(BaseModel):
    """
    Schema for decoded JWT token payload.
    
    Used internally to extract user_id from token.
    """
    user_id: int | None = None


# Import at bottom to avoid circular import
from app.schemas.user import UserResponse
Token.model_rebuild()  # Rebuild model now that UserResponse is available