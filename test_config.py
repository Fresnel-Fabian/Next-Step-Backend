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
    first_id = settings.google_client_ids[0] if settings.google_client_ids else "none"
    print(f"  Google Client IDs: {first_id[:20]}...")  # First ID, 20 chars
    print(f"  Token Expiry: {settings.access_token_expire_minutes} minutes")


if __name__ == "__main__":
    test_config()
