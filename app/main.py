# app/main.py
"""
FastAPI Application Entry Point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import engine, Base
from app.config import get_settings
from app.routers import auth, users, dashboard, schedules, documents, polls, notifications

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    logger.info("Starting application...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")
    
    yield
    
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="School Management API - Staff scheduling, documents, polls, and notifications",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Include ALL Routers =====
app.include_router(auth.router)           # /api/v1/auth/*
app.include_router(users.router)          # /api/v1/users/*
app.include_router(dashboard.router)      # /api/v1/dashboard/*
app.include_router(schedules.router)      # /api/v1/schedules/*
app.include_router(documents.router)      # /api/v1/documents/*
app.include_router(polls.router)          # /api/v1/polls/*
app.include_router(notifications.router)  # /api/v1/notifications/*


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "School Management API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }