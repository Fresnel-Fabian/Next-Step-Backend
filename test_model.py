# test_model.py
"""Test User model creation."""

import asyncio
from app.database import engine, Base
from app.models.user import User, UserRole

async def test_model():
    """Create tables and test model."""
    
    # Create all tables
    async with engine.begin() as conn:
        # Drop existing tables (be careful in production!)
        await conn.run_sync(Base.metadata.drop_all)
        # Create new tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Database tables created successfully!")
    print(f"  Tables: {list(Base.metadata.tables.keys())}")
    
    # Close engine
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_model())