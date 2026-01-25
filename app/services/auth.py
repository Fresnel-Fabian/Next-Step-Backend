# app/services/auth.py
"""
Authentication service - handles passwords and JWT tokens.

This module provides:
- Password hashing (never store plain text!)
- Password verification
- JWT token creation
- JWT token decoding
- User authentication
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User

settings = get_settings()

# ============================================
# 1. Password Hashing Setup
# ============================================
# CryptContext handles password hashing securely
# bcrypt is the recommended algorithm (slow = secure)
pwd_context = CryptContext(
    schemes=["argon2"],  # Use bcrypt algorithm
    deprecated="auto"    # Auto-handle old hash formats
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password.
    
    NEVER store plain text passwords!
    
    How bcrypt works:
    1. Generates random salt
    2. Combines salt + password
    3. Runs through bcrypt algorithm (slow on purpose)
    4. Returns hash like: $2b$12$LQv3c1yqBw...
    
    Args:
        password: Plain text password from user
        
    Returns:
        Hashed password (safe to store in database)
        
    Example:
        >>> hash_password("mypassword123")
        '$2b$12$LQv3c1yqBWQEqN3N0s9Ue...'
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Used during login to check if password is correct.
    
    Args:
        plain_password: Password user entered
        hashed_password: Hash stored in database
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================
# 2. JWT Token Functions
# ============================================
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    JWT = JSON Web Token
    
    Structure: header.payload.signature
    Example: eyJhbGc.eyJzdWI.SflKxw
    
    Our payload contains:
    - sub (subject): user ID
    - exp (expiration): when token expires
    
    Args:
        data: Dict with data to encode (usually {"sub": user_id})
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token string
        
    Example:
        >>> create_access_token({"sub": "123"})
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    # Add expiration to payload
    to_encode.update({"exp": expire})
    
    # Create token
    # jwt.encode(payload, secret_key, algorithm)
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decode and verify a JWT token.
    
    Checks:
    1. Token is valid (proper format)
    2. Signature matches (not tampered)
    3. Not expired
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
        
    Example:
        >>> token = create_access_token({"sub": "123"})
        >>> decode_token(token)
        {'sub': '123', 'exp': 1699999999}
        >>> decode_token("invalid_token")
        None
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        # Token is invalid, expired, or tampered
        return None


# ============================================
# 3. User Authentication
# ============================================
async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> User | None:
    """
    Authenticate user with email and password.
    
    Steps:
    1. Find user by email
    2. Check if user exists
    3. Check if user has password (not Google-only)
    4. Verify password matches
    
    Args:
        db: Database session
        email: User's email
        password: Plain text password
        
    Returns:
        User object if authenticated, None otherwise
        
    Example:
        user = await authenticate_user(db, "john@school.edu", "password123")
        if user:
            print("Login successful!")
        else:
            print("Invalid credentials")
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    
    # User not found
    if not user:
        return None
    
    # User exists but has no password (Google-only user)
    if not user.hashed_password:
        return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        return None
    
    return user