# app/database.py
"""
Database connection and session management.

This module sets up the async SQLAlchemy engine and provides
database session management for dependency injection.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# ============================================
# 1. Create Async Engine
# ============================================
# Think of the engine as a "connection factory"
# It manages a pool of database connections
engine = create_async_engine(
    settings.database_url,
    # Echo SQL queries to console (only in debug mode)
    # Helpful for learning what SQLAlchemy is doing
    echo=settings.debug,
    # Connection Pool Settings
    # Pool = reusable connections (faster than creating new ones each time)
    pool_size=20,  # Keep 20 connections ready
    max_overflow=10,  # Can create 10 more if needed (total 30 max)
    # Connection timeout
    pool_pre_ping=True,  # Check if connection is alive before using
)

# ============================================
# 2. Create Session Factory
# ============================================
# Session = a workspace for database operations
# Like opening Excel, making changes, then saving/closing
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,  # We manually commit (safer)
    autoflush=False,  # We manually flush (more control)
)


# ============================================
# 3. Create Base Class for Models
# ============================================
# All our database models will inherit from this
class Base(DeclarativeBase):
    """
    Base class for all database models.

    SQLAlchemy uses this to:
    - Track all models
    - Generate CREATE TABLE statements
    - Manage relationships between tables
    """

    pass


# ============================================
# 4. Dependency Injection for FastAPI
# ============================================
async def get_db():
    """
    Dependency that provides a database session.

    Usage in routes:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Use db here

    Why this pattern?
    - Automatic session management
    - Always closes connection (even if error occurs)
    - Automatic commit on success, rollback on error
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # Provide session to route
            await session.commit()  # Commit if no errors
        except Exception:
            await session.rollback()  # Undo changes if error
            raise  # Re-raise the exception
        finally:
            await session.close()  # Always close connection
