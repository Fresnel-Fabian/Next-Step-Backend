# test_api.py
"""Interactive API testing script."""

import httpx
import asyncio

BASE_URL = "http://localhost:8000"


async def test_api():
    async with httpx.AsyncClient() as client:
        # 1. Health Check
        print("\n1. Health Check")
        r = await client.get(f"{BASE_URL}/health")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # 2. Register
        print("\n2. Register User")
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "name": "Test User",
                "email": "test@school.edu",
                "password": "testpass123",
                "department": "Testing",
            },
        )
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # 3. Login
        print("\n3. Login")
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "test@school.edu", "password": "testpass123"},
        )
        print(f"   Status: {r.status_code}")
        data = r.json()
        token = data.get("token")
        print(f"   Token: {token[:50]}...")

        # 4. Get Me
        print("\n4. Get Current User")
        r = await client.get(
            f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        # 5. Update Profile
        print("\n5. Update Profile")
        r = await client.put(
            f"{BASE_URL}/api/v1/users/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Updated Name"},
        )
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")

        print("\n✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_api())
