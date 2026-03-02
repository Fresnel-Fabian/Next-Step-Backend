# Contributing

Local development setup and workflow. For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Development Setup

### 1. Install Prerequisites

**Python 3.11+**
```bash
# macOS (using Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt update && sudo apt install python3.12 python3.12-venv

# Windows: https://www.python.org/downloads/

# Verify installation
python --version
```

**uv** - package manager
```bash
# macOS (Homebrew)
brew install uv

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

**PostgreSQL** — Docker recommended:
```bash
# Install Docker: https://docs.docker.com/get-docker/

docker run --name school_postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=school_db \
  -p 5432:5432 \
  -d postgres:16-alpine

# Verify it's running
docker ps
```

For a local install without Docker, see the [PostgreSQL docs](https://www.postgresql.org/download/).

---

### 2. Install Dependencies

```bash
uv sync
```

---

### 3. Configure Environment

```bash
cp .env.example .env
```

.env Configuration
```bash
# Async PostgreSQL connection string
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_db

# JWT signing key - GENERATE A NEW KEY!
# Run: openssl rand -hex 32
# python alternative: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here-generate-with-openssl

# Debug Mode (set to false in production)
DEBUG=true

# Google OAuth (optional)
# JSON array of OAuth client IDs for web, iOS, Android
GOOGLE_CLIENT_ID=["111-web.apps.googleusercontent.com","222-ios.apps.googleusercontent.com","333-android.apps.googleusercontent.com"]

# Redis (optional for now)
# Required if using Celery background tasks
REDIS_URL=redis://localhost:6379/0
```
---

### 4. Run Migrations

```bash
alembic upgrade head
```

To create a new migration after changing a model:
```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

### 5. Run the Server

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload

# Or specify host and port
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Verify Installation

Open your browser and visit:

- API Root: http://localhost:8000
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Health Check: http://localhost:8000/health


---

## Daily Development

```bash
# 1. Start the database (optional detached tag to run docker in background)
docker compose up db -d

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Run the server
uvicorn app.main:app --reload
```

### Database Management

```bash
docker exec -it school_postgres psql -U postgres -d school_db

# Useful psql commands
\dt                   # list tables
\d tablename          # describe a table
\q                    # quit
```

### Adding Dependencies

```bash
uv add package-name           # production
uv add --dev package-name     # development only
uv sync                       # sync after changes
```

### Code Formatting

```bash
uv run black app/
uv run isort app/
```

---

## Troubleshooting Common Issues

#### "Connection refused" to PostgreSQL

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if not running
docker start school_postgres

# Check logs
docker logs school_postgres
```

#### "Module not found" errors

```bash
# Reinstall dependencies
uv sync --reinstall
```

#### "Invalid token" errors

- Check that SECRET_KEY in .env matches what was used to create the token
- Tokens expire after 24 hours by default
- Ensure Authorization header format: `Bearer <token>`

#### Database connection errors

```bash
# Verify DATABASE_URL format
# Correct: postgresql+asyncpg://user:pass@host:port/db
# Wrong:   postgres://... (missing +asyncpg)

# Test connection
docker exec -it school_postgres psql -U postgres -d school_db -c "SELECT 1;"
```

#### Google OAuth not working

- Verify GOOGLE_CLIENT_ID matches your Google Cloud Console
- Ensure the Client ID is for the correct application type
- Check that Google+ API is enabled in your project


**Configuration Steps**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Google+ API"
4. Go to Credentials → Create OAuth 2.0 Client ID
5. Copy the Client ID

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
