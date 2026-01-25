# app/config.py
"""
Configuration Management using Pydantic Settings.

This module loads environment variables from .env file and validates them.
Why Pydantic Settings?
- Type validation (ensures DATABASE_URL is a string, not accidentally a number)
- Auto-loads from .env file
- Provides defaults
- Raises errors if required variables are missing
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Info
    app_name: str = "Next Step API"
    debug: bool = False  # False by default for safety
    
    # Database Configuration
    # Format: postgresql+asyncpg://user:password@host:port/database_name
    # asyncpg = async driver for PostgreSQL (faster than psycopg2)
    database_url: str
    
    # Redis Configuration (for Celery message broker)
    # Format: redis://host:port/database_number
    # Database 0 is default, you can use 1, 2, etc. for separation
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT (JSON Web Token) Configuration
    secret_key: str  # Used to sign JWT tokens - MUST be secret!
    algorithm: str = "HS256"  # Hashing algorithm for JWT
    access_token_expire_minutes: int = 1440  # 24 hours (1440 minutes)
    
    # Google OAuth Configuration
    # Get this from: https://console.cloud.google.com/apis/credentials
    google_client_ids: list[str] = [
        "111-web.apps.googleusercontent.com",
        "222-ios.apps.googleusercontent.com", 
        "333-android.apps.googleusercontent.com"
    ]
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"  # Load from .env file
        env_file_encoding = "utf-8"
        case_sensitive = False  # DATABASE_URL or database_url both work


@lru_cache  # Cache the settings so we don't re-read .env every time
def get_settings() -> Settings:
    """
    Get application settings (cached).
    
    Why @lru_cache?
    - Reads .env file only once
    - Subsequent calls return cached instance
    - Improves performance
    
    Returns:
        Settings: Application configuration
    """
    return Settings()


# Example usage in other files:
# from app.config import get_settings
# settings = get_settings()
# print(settings.database_url)