# School Management API

A modern, async REST API built with FastAPI for managing school staff, schedules, documents, polls, and notifications.

## Features

- 🔐 **Authentication** - JWT-based auth with Google OAuth support
- 👥 **User Management** - Role-based access control (Admin, Teacher, Staff)
- 📅 **Schedules** - Department schedule management
- 📄 **Documents** - File metadata management with categories
- 📊 **Polls** - Create polls and collect votes
- 🔔 **Notifications** - User notification system
- 📈 **Dashboard** - Statistics and activity feed

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with async support
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT + Google OAuth
- **Package Manager**: uv (fast Python package manager)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### 1. Python 3.11 or higher

```bash
# Check Python version
python --version  # Should be 3.11+

# macOS (using Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv

# Windows
# Download from https://www.python.org/downloads/
```

### 2. uv Package Manager

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS (Homebrew)
brew install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### 3. PostgreSQL Database

#### Option A: Using Docker (Recommended)

```bash
# Install Docker: https://docs.docker.com/get-docker/

# Run PostgreSQL container
docker run --name school_postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=school_db \
  -p 5432:5432 \
  -d postgres:16-alpine

# Verify it's running
docker ps
```

#### Option B: Local PostgreSQL Installation

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# Create database
psql -U postgres -c "CREATE DATABASE school_db;"
```

### 4. Google OAuth Credentials (Optional)

If you want Google Sign-In:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Google+ API"
4. Go to Credentials → Create OAuth 2.0 Client ID
5. Copy the Client ID

---

## Installation

### Step 1: Clone the Repository

```bash
git https://github.com/Fresnel-Fabian/Next-Step-Backend
cd next-step-backend
```

### Step 2: Install Dependencies

```bash
# This creates .venv and installs all packages
uv sync

# Or if starting fresh
uv init
uv add fastapi "uvicorn[standard]"
uv add "sqlalchemy[asyncio]" asyncpg psycopg2-binary alembic
uv add pydantic pydantic-settings
uv add "python-jose[cryptography]" "passlib[bcrypt]" google-auth
uv add python-multipart
```

### Step 3: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
nano .env  # or use any text editor
```

#### `.env` Configuration

```bash
# Database Connection
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_db

# Redis (for Celery - optional for now)
REDIS_URL=redis://localhost:6379/0

# Security - GENERATE A NEW KEY!
# Run: openssl rand -hex 32
SECRET_KEY=your-secret-key-here-generate-with-openssl

# Google OAuth (optional)
GOOGLE_CLIENT_ID=["111-web.apps.googleusercontent.com","222-ios.apps.googleusercontent.com","333-android.apps.googleusercontent.com"]

# Debug Mode (set to false in production)
DEBUG=true
```

#### Generate a Secure SECRET_KEY

```bash
# Linux/macOS
openssl rand -hex 32

# Python alternative
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4: Verify PostgreSQL Connection

```bash
# Verify connection
docker exec -it school_postgres psql -U postgres -d school_db -c "SELECT 1;"
```

### Step 5: Run the Application

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload

# Or specify host and port
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Verify Installation

Open your browser and visit:

- **API Root**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

---

## Quick Start Guide

### 1. Create an Admin User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@school.edu",
    "password": "adminpass123",
    "department": "Administration",
    "role": "ADMIN"
  }'
```

### 2. Login and Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@school.edu",
    "password": "adminpass123"
  }'
```

Save the `token` from the response.

### 3. Use the Token for Authenticated Requests

```bash
# Replace YOUR_TOKEN with the actual token
export TOKEN="your_jwt_token_here"

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Create a schedule (admin only)
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Mathematics",
    "class_count": 12,
    "staff_count": 8,
    "status": "Active"
  }'
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Email/password login |
| POST | `/api/v1/auth/google` | Google OAuth login |
| GET | `/api/v1/auth/me` | Get current user |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/api/v1/users/profile` | Update profile |
| GET | `/api/v1/users` | List users (admin) |
| GET | `/api/v1/users/{id}` | Get user |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/stats` | Get statistics |
| GET | `/api/v1/dashboard/activity` | Activity feed |

### Schedules
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/schedules` | List schedules |
| POST | `/api/v1/schedules` | Create (admin) |
| PUT | `/api/v1/schedules/{id}` | Update (admin) |
| DELETE | `/api/v1/schedules/{id}` | Delete (admin) |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/documents` | List documents |
| POST | `/api/v1/documents` | Upload metadata |
| DELETE | `/api/v1/documents/{id}` | Delete (admin) |

### Polls
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/polls` | List polls |
| POST | `/api/v1/polls` | Create (admin) |
| POST | `/api/v1/polls/{id}/vote` | Cast vote |
| PATCH | `/api/v1/polls/{id}/close` | Close (admin) |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/notifications` | List notifications |
| GET | `/api/v1/notifications/unread-count` | Unread count |
| PATCH | `/api/v1/notifications/{id}/read` | Mark read |
| PATCH | `/api/v1/notifications/read-all` | Mark all read |

---

## Project Structure

```
school-management-api/
├── .env                    # Environment variables (DO NOT COMMIT)
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── pyproject.toml          # Project dependencies
├── uv.lock                 # Locked dependencies
├── README.md               # This file
│
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry
│   ├── config.py           # Configuration management
│   ├── database.py         # Database connection
│   ├── dependencies.py     # Auth dependencies
│   │
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py
│   │   ├── schedule.py
│   │   ├── document.py
│   │   ├── poll.py
│   │   ├── notification.py
│   │   └── activity.py
│   │
│   ├── schemas/            # Pydantic schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── dashboard.py
│   │   ├── schedule.py
│   │   ├── document.py
│   │   ├── poll.py
│   │   └── notification.py
│   │
│   ├── routers/            # API routes
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── dashboard.py
│   │   ├── schedules.py
│   │   ├── documents.py
│   │   ├── polls.py
│   │   └── notifications.py
│   │
│   ├── services/           # Business logic
│   │   ├── auth.py
│   │   ├── google_auth.py
│   │   └── activity.py
│   │
│   └── tasks/              # Background tasks (Celery)
│       └── __init__.py
│
└── tests/                  # Test files
    └── __init__.py
```

---

## Development

### Running in Development Mode

```bash
# With auto-reload (recommended for development)
uv run uvicorn app.main:app --reload

# With specific host/port
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Management

```bash
# Connect to PostgreSQL
docker exec -it school_postgres psql -U postgres -d school_db

# Useful psql commands
\dt                 # List tables
\d users            # Describe users table
SELECT * FROM users;  # Query data
\q                  # Quit
```

### Adding New Dependencies

```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Update all dependencies
uv sync
```

### Code Formatting

```bash
# Install dev tools
uv add --dev black isort

# Format code
uv run black app/
uv run isort app/
```

---

## Troubleshooting

### Common Issues

#### 1. "Connection refused" to PostgreSQL

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if not running
docker start school_postgres

# Check logs
docker logs school_postgres
```

#### 2. "Module not found" errors

```bash
# Reinstall dependencies
uv sync --reinstall
```

#### 3. "Invalid token" errors

- Check that SECRET_KEY in .env matches what was used to create the token
- Tokens expire after 24 hours by default
- Ensure Authorization header format: `Bearer <token>`

#### 4. Database connection errors

```bash
# Verify DATABASE_URL format
# Correct: postgresql+asyncpg://user:pass@host:port/db
# Wrong:   postgres://... (missing +asyncpg)

# Test connection
docker exec -it school_postgres psql -U postgres -d school_db -c "SELECT 1;"
```

#### 5. Google OAuth not working

- Verify GOOGLE_CLIENT_ID matches your Google Cloud Console
- Ensure the Client ID is for the correct application type
- Check that Google+ API is enabled in your project

---

## Production Deployment

### Environment Variables for Production

```bash
DEBUG=false
SECRET_KEY=<generate-strong-key>
DATABASE_URL=postgresql+asyncpg://user:strongpass@db-host:5432/school_db
```

### Running with Multiple Workers

```bash
# Using uvicorn with multiple workers
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or use gunicorn with uvicorn workers
uv add gunicorn
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application
COPY app/ ./app/

# Run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t next-step-backend .
docker run -p 8000:8000 --env-file .env next-step-backend
```

---

## License

MIT License - feel free to use this project for learning or commercial purposes.

---

## Support

If you encounter any issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search existing GitHub issues
3. Create a new issue with:
   - Python version (`python --version`)
   - OS information
   - Error message and stack trace
   - Steps to reproduce