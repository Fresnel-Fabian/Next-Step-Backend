# test_config.py
"""Quick test to verify configuration is loaded correctly."""

from app.config import get_settings


def test_config():
    settings = get_settings()

    print("✓ Configuration loaded successfully!")
    print(f"  App Name: {settings.app_name}")
    print(f"  Debug Mode: {settings.debug}")
    print(f"  Database: {settings.database_url.split('@')[1]}")  # Don't print password
    print(f"  Redis: {settings.redis_url}")
    print(f"  Google Client ID: {settings.google_client_id[:20]}...")  # First 20 chars
    print(f"  Token Expiry: {settings.access_token_expire_minutes} minutes")


if __name__ == "__main__":
    test_config()
