# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from app.database import engine, Base
from app.config import get_settings
from app.routers import (
    auth,
    users,
    dashboard,
    schedules,
    schedule_events,
    documents,
    polls,
    notifications,
    announcements,
    invitations    
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:19006",
    "http://127.0.0.1:19006",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")

    os.makedirs("uploads", exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created/verified")

    yield

    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="School Management API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# 1. Middleware (must be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# 2. Exception handlers
def cors_headers(request):
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=cors_headers(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("VALIDATION ERROR:", exc.errors())
    errors = []
    for e in exc.errors():
        errors.append({
            "loc": list(e.get("loc", [])),
            "msg": str(e.get("msg", "")),
            "type": str(e.get("type", "")),
        })
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
        headers=cors_headers(request),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=cors_headers(request),
    )


# 3. Static mounts
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 4. Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(schedules.router)
app.include_router(schedule_events.router)
app.include_router(documents.router)
app.include_router(polls.router)
app.include_router(notifications.router)
app.include_router(announcements.router)
app.include_router(invitations.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    return {"message": "School Management API", "version": "1.0.0", "docs": "/api/docs"}