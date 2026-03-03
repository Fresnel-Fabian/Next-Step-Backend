# app/schemas/auth.py
"""
Authentication schemas for request/response validation.

These define the exact shape of data for:
- Login requests
- Google PKCE authorization-code exchange requests
- Token responses

ref: https://developers.google.com/identity/protocols/oauth2/native-app
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """
    Schema for email/password login.

    Example request body:
    {
        "email": "user@school.edu",
        "password": "secretpassword123"
    }
    """

    email: EmailStr
    password: str

    # Pydantic V2 config
    model_config = {
        "json_schema_extra": {
            "example": {"email": "student@school.edu", "password": "mypassword123"}
        }
    }


class GoogleAuthRequest(BaseModel):
    """
    Schema for Google PKCE authorization-code login.
    ResponseType.Token (implicit flow) never returns an id_token or a
    refresh_token. ResponseType.Code (PKCE) returns all three.

    Example request body:
    {
        "code": "4/0AX4XfWh...",
        "codeVerifier": "dBjftJeZ4...",
        "redirectUri": "exp://192.168.1.5:19000"
    }
    """

    code: str
    codeVerifier: str
    redirectUri: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "4/0AX4XfWh...",
                "codeVerifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
                "redirectUri": "exp://192.168.1.5:19000",
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
    user: "UserResponse"

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "1",
                    "name": "John Doe",
                    "email": "john@school.edu",
                    "role": "STUDENT",
                    "avatar": None,
                    "department": "Science",
                },
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

Token.model_rebuild()
