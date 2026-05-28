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

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Info
    app_name: str = "Next Step API"
    debug: bool = False  # False by default for safety
    environment: Literal["development", "staging", "production"] = "development"

    # CORS — comma-separated list of allowed frontend origins.
    # Example: "https://app.example.com,https://admin.example.com"
    allowed_origins: str = (
        "http://localhost:8081,http://127.0.0.1:8081,"
        "http://localhost:19006,http://127.0.0.1:19006"
    )

    # Sentry — leave empty to disable error tracking (e.g. local dev).
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

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
        "333-android.apps.googleusercontent.com",
    ]
    google_web_client_id: str = ""
    google_client_secret: str = ""

    # Email (Gmail SMTP) Configuration
    # mail_username: your Gmail address
    # mail_password: your Gmail App Password (not your regular password)
    # mail_from: sender address (defaults to mail_username if left empty)
    # mail_from_name: display name shown in the email client
    # frontend_url: base URL used to build invite links in emails
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""  # defaults to mail_username if empty
    mail_from_name: str = "Next Step"
    frontend_url: str = "http://localhost:8081"

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
