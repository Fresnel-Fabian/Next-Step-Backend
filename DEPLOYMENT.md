# Deployment

Production setup for the Next-Step backend. (Beta -- copied from old documentation, needs to be further developed)

---

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