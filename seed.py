"""
Seed script — creates test users in the database.

Usage:
    uv run python seed.py
"""

import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User, UserRole
from app.services.auth import hash_password

TEST_USERS = [
    {
        "email": "admin@school.edu",
        "name": "Admin User",
        "password": "adminpass123",
        "role": UserRole.ADMIN,
        "department": "Administration",
    },
    {
        "email": "teacher@school.edu",
        "name": "Teacher User",
        "password": "teacherpass123",
        "role": UserRole.TEACHER,
        "department": "Science",
    },
    {
        "email": "student@school.edu",
        "name": "Student User",
        "password": "studentpass123",
        "role": UserRole.STUDENT,
        "department": "Computer Science",
    },
]


async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for u in TEST_USERS:
            result = await session.execute(select(User).where(User.email == u["email"]))
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  Exists: {u['email']} (role={existing.role.value})")
                continue

            user = User(
                email=u["email"],
                name=u["name"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                department=u["department"],
            )
            session.add(user)
            print(f"  Created: {u['email']} (role={u['role'].value})")

        await session.commit()

    print("\nDone. Test credentials:")
    print("  admin@school.edu   / adminpass123")
    print("  teacher@school.edu / teacherpass123")
    print("  student@school.edu / studentpass123")


if __name__ == "__main__":
    asyncio.run(seed())
