# Next-Step Backend

Async REST API for managing school staff, schedules, documents, polls, and notifications.

---

## Quick Start

```bash
git clone https://github.com/Fresnel-Fabian/Next-Step-Backend
cd next-step-backend

cp .env.example .env          # add your credentials
uv sync                       # install dependencies
alembic upgrade head          # run migrations

uv run uvicorn app.main:app --reload
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/api/docs`

> **Prerequisites:** Python 3.11+, uv, PostgreSQL (or Docker).
> See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup instructions.

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
| GET | `/api/v1/dashboard/stats` | Statistics |
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
| POST | `/api/v1/documents/from-drive` | Register Drive file |
| GET | `/api/v1/documents/shared-with-me` | Shared With Me |
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
app/
├── main.py             # FastAPI application entry
├── config.py           # Configuration management (.env)
├── database.py         # Database connection
├── dependencies.py     # Auth middleware
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic request/response schemas
├── routers/            # API routes
├── services/           # Business logic
└── tasks/              # Background tasks (Celery)
```

---

## Documentation

- [Contributing & Development Setup](CONTRIBUTING.md)
- [Deployment Guide](docs/deployment.md)
- Interactive API reference at `/api/docs` or `/api/redoc` when running

---

## License

MIT License - feel free to use this project for learning or commercial purposes.