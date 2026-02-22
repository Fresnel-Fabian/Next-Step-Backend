# test_api.py
"""Interactive API testing script.

Run once to create test credentials and run tests.
Credentials are created in DB and printed for use in frontend/manual testing.
"""

import httpx
import asyncio

BASE_URL = "http://localhost:8000"

# Test credentials - created by this script, use for frontend/manual testing
ADMIN = {"email": "admin@school.edu", "password": "adminpass123", "role": "ADMIN"}
USER = {"email": "student@school.edu", "password": "studentpass123", "role": "STUDENT"}


def _register_user(client: httpx.AsyncClient, name: str, email: str, password: str, department: str, role: str):
    return client.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "department": department,
            "role": role,
        },
    )


async def test_api():
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 1. Health Check
        print("\n1. Health Check")
        try:
            r = await client.get(f"{BASE_URL}/health")
        except httpx.ConnectError:
            print(f"   ERROR: Cannot connect to {BASE_URL}")
            print("   Make sure the backend is running:")
            print("   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
            return
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # 2. Register Admin
        print("\n2. Register Admin")
        r = await _register_user(
            client,
            name="Admin User",
            email=ADMIN["email"],
            password=ADMIN["password"],
            department="Administration",
            role=ADMIN["role"],
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 201:
            print(f"   Created: {r.json()}")
        else:
            print(f"   (already exists: {r.json().get('detail', r.json())})")

        # 3. Register User (Student)
        print("\n3. Register User (Student)")
        r = await _register_user(
            client,
            name="Test Student",
            email=USER["email"],
            password=USER["password"],
            department="Science",
            role=USER["role"],
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 201:
            print(f"   Created: {r.json()}")
        else:
            print(f"   (already exists: {r.json().get('detail', r.json())})")

        # 4. Login as Admin
        print("\n4. Login as Admin")
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN["email"], "password": ADMIN["password"]},
        )
        print(f"   Status: {r.status_code}")
        data = r.json()
        admin_token = data.get("token")
        if admin_token:
            print(f"   Token: {admin_token[:50]}...")

        # 5. Login as User
        print("\n5. Login as User")
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": USER["email"], "password": USER["password"]},
        )
        print(f"   Status: {r.status_code}")
        data = r.json()
        user_token = data.get("token")
        if user_token:
            print(f"   Token: {user_token[:50]}...")

        # 6. Get Me (as Admin)
        print("\n6. Get Current User (Admin)")
        r = await client.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # 7. Update Profile (as User)
        print("\n7. Update Profile (User)")
        r = await client.put(
            f"{BASE_URL}/api/v1/users/profile",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "Updated Student Name"},
        )
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # Print credentials for testing
        print("\n" + "=" * 50)
        print("TEST CREDENTIALS (use in frontend or manual testing)")
        print("=" * 50)
        print("Admin:  ", ADMIN["email"], " / ", ADMIN["password"])
        print("User:   ", USER["email"], " / ", USER["password"])
        print("=" * 50)
        print("\n✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_api())
