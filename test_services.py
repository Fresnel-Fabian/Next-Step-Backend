# test_services.py
"""Test authentication services."""

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_password_hashing():
    """Test password hash and verify."""
    password = "mySecretPass123"

    # Hash the password
    hashed = hash_password(password)
    print(f"Original: {password}")
    print(f"Hashed:   {hashed[:50]}...")

    # Verify correct password
    assert verify_password(password, hashed) == True
    print("✓ Correct password verified")

    # Verify wrong password
    assert verify_password("wrongpassword", hashed) == False
    print("✓ Wrong password rejected")


def test_jwt_tokens():
    """Test JWT creation and decoding."""
    # Create token
    user_id = "123"
    token = create_access_token({"sub": user_id})
    print(f"\nToken: {token[:50]}...")

    # Decode token
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    print(f"✓ Token decoded successfully")
    print(f"  Payload: {payload}")

    # Test invalid token
    invalid = decode_token("invalid.token.here")
    assert invalid is None
    print("✓ Invalid token rejected")


if __name__ == "__main__":
    test_password_hashing()
    test_jwt_tokens()
    print("\n✓ All tests passed!")
