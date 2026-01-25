# test_models.py
"""Test all database models."""

import asyncio
from app.database import engine, Base
from app.models import (
    User,
    UserRole,
    Schedule,
    Document,
    Poll,
    PollVote,
    Notification,
    Activity,
)


async def test_models():
    """Create all tables and verify."""

    print("Creating database tables...")

    async with engine.begin() as conn:
        # Drop all tables (fresh start)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    # List all tables
    tables = list(Base.metadata.tables.keys())

    print(f"\n✓ Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")

    # Verify table structure
    print("\n✓ Table structures:")
    for table_name, table in Base.metadata.tables.items():
        columns = [col.name for col in table.columns]
        print(f"\n  {table_name}:")
        for col in columns:
            print(f"    - {col}")

    await engine.dispose()
    print("\n✓ All models created successfully!")


if __name__ == "__main__":
    asyncio.run(test_models())
