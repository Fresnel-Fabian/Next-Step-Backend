# Deployment Guide

A scenario-driven guide for getting the Next-Step backend running outside the managed-cloud path: Docker on a server you control, no Docker at all, SQLite instead of Postgres, exposing the API on a LAN or the public internet.

If you're deploying to a managed host (Render, Fly.io, Railway, AWS/GCP) for a real school, read [**DEPLOYMENT.md**](../DEPLOYMENT.md) at the repo root instead — it covers FERPA, backups, observability, and sub-processors. The two guides are complementary.

---

## Which scenario fits you?

| You want to… | Go to |
|---|---|
| Try the app locally with a real database | [Scenario A — Docker + Postgres](#scenario-a--docker--postgres) |
| Run on a small VM/Pi with no separate DB service | [Scenario B — Docker + SQLite](#scenario-b--docker--sqlite) |
| Install directly on a Linux host without Docker | [Scenario C — Bare-metal](#scenario-c--bare-metal) |
| Make the API reachable from another machine | [Scenario D — Exposing the service](#scenario-d--exposing-the-service) |
| Deploy to a managed cloud for production | [`../DEPLOYMENT.md`](../DEPLOYMENT.md) |

---

## Prerequisites

| Tool | Used for | Install |
|---|---|---|
| Python 3.12+ | Bare-metal scenarios | system package manager |
| [uv](https://docs.astral.sh/uv/) | Dependency management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker + Compose v2 | Container scenarios | https://docs.docker.com/engine/install/ |

Generate a `SECRET_KEY` once (every environment gets its own):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

A starter `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_db
SECRET_KEY=<paste-the-32-byte-hex-here>
DEBUG=false
```

The minimum required vars are `DATABASE_URL` and `SECRET_KEY`. Everything else has a default in `app/config.py`.

---

## Scenario A — Docker + Postgres

The default path. Uses the project's `Dockerfile` and `docker-compose.yml`.

### 1. Start Postgres

```bash
docker compose up -d db
```

This brings up `postgres:16-alpine` on `localhost:5432` with user/password `postgres/postgres` and database `school_db`. Data persists in the named volume `postgres_data`.

### 2. Configure `.env`

```bash
cp .env.example .env
# edit .env: set SECRET_KEY (see Prerequisites)
```

The default `DATABASE_URL` in `.env.example` already points at the compose-managed Postgres.

### 3. Build the API image

```bash
docker build -t next-step-backend .
```

The multi-stage Dockerfile produces a ~150 MB image with a non-root user (`uid 1000`), a built-in `HEALTHCHECK`, and uvicorn with 2 workers.

### 4. Run the API

```bash
docker run --rm -p 8000:8000 \
  --env-file .env \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL='postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/school_db' \
  next-step-backend
```

`host.docker.internal` lets the container reach Postgres on the host. On Linux, the `--add-host` flag enables it.

(If you'd rather run both on the same Docker network, add the API to `docker-compose.yml` as a second service — that's a follow-up exercise, not covered here.)

### 5. Smoke test

```bash
curl http://localhost:8000/health     # {"status":"healthy","version":"1.0.0"}
curl http://localhost:8000/           # root JSON
open http://localhost:8000/api/docs   # interactive Swagger UI
```

### 6. Migrations

The app's lifespan currently runs `Base.metadata.create_all` on startup, so a **fresh empty database is populated automatically** — no Alembic step needed for greenfield. For schema changes against an existing DB, use Alembic:

```bash
docker run --rm --env-file .env next-step-backend uv run alembic upgrade head
```

---

## Scenario B — Docker + SQLite

For demos, single-server low-traffic deployments, internal tools — anywhere you don't want to run a separate Postgres process.

`aiosqlite` is already in `pyproject.toml`, so the standard Docker image works as-is.

### 1. Configure `.env`

```bash
DATABASE_URL=sqlite+aiosqlite:////data/app.db
SECRET_KEY=<paste-the-32-byte-hex-here>
DEBUG=false
```

Note the **four slashes** in `sqlite+aiosqlite:////data/app.db` — three for the URL scheme separator and one because the path is absolute (`/data/app.db`).

### 2. Run with persistent volumes

```bash
docker volume create school-data
docker volume create school-uploads

docker run --rm -p 8000:8000 \
  --env-file .env \
  -v school-data:/data \
  -v school-uploads:/app/uploads \
  next-step-backend
```

Two volumes:
- `school-data` holds the SQLite file. **Without this, the database is lost on every restart.**
- `school-uploads` holds user-uploaded documents. Same story.

On first boot, the app creates `app.db` and all tables (via `Base.metadata.create_all` in `app/main.py`).

### 3. Smoke test

Same as Scenario A: `curl http://localhost:8000/health`.

### Migration caveat

The project's `alembic/env.py` doesn't set `render_as_batch=True`. SQLite can't `ALTER TABLE` for most column changes, so any Alembic migration that alters an existing column will **fail on SQLite**.

In practice:
- **Greenfield deploys (you control when the schema changes):** rely on `Base.metadata.create_all`. It runs on every startup and is idempotent for new tables — no Alembic needed.
- **You want to use Alembic on SQLite:** edit `alembic/env.py` to pass `render_as_batch=True` to `context.configure(...)`. Out of scope for this guide.

### Trade-offs

| | Postgres | SQLite |
|---|---|---|
| Concurrent writers | Yes | Single writer (serialized) |
| Backup | Managed snapshot or `pg_dump` | Copy the file |
| Connection pool | Real | Mostly a no-op |
| Max practical size | Hundreds of GB | A few GB before pain |
| Operator burden | Postgres process to monitor | Just a file |

Switch to Postgres once you have multiple users hitting writes at once. Until then, SQLite is fine.

---

## Scenario C — Bare-metal

For a home server, Raspberry Pi, or any host where Docker isn't an option.

### 1. Install

```bash
sudo useradd --create-home --shell /bin/bash app
sudo -u app -i

# as the app user:
git clone https://github.com/Fresnel-Fabian/Next-Step-Backend ~/next-step
cd ~/next-step
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --no-dev
```

### 2. Configure

```bash
cp .env.example .env
# edit .env: SECRET_KEY, DATABASE_URL
```

For SQLite on bare-metal, use a path you own:

```
DATABASE_URL=sqlite+aiosqlite:////home/app/next-step/data/app.db
```

Create the dir: `mkdir -p ~/next-step/data ~/next-step/uploads`.

For Postgres on bare-metal:

```bash
sudo apt install postgresql
sudo -u postgres createuser --pwprompt app
sudo -u postgres createdb -O app school_db
# then in .env:
# DATABASE_URL=postgresql+asyncpg://app:<password>@localhost:5432/school_db
```

### 3. Run (foreground, for testing)

```bash
uv run uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --workers 2 \
  --proxy-headers --forwarded-allow-ips '*'
```

These flags mirror the Dockerfile `CMD` exactly. The `--proxy-headers` pair is required when fronting with a reverse proxy (Scenario D).

### 4. Run as a systemd service

Create `/etc/systemd/system/next-step.service`:

```ini
[Unit]
Description=Next-Step Backend
After=network.target

[Service]
Type=simple
User=app
Group=app
WorkingDirectory=/home/app/next-step
EnvironmentFile=/home/app/next-step/.env
ExecStart=/home/app/.local/bin/uv run uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --workers 2 --proxy-headers --forwarded-allow-ips '*'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now next-step
sudo systemctl status next-step
sudo journalctl -u next-step -f         # follow logs
```

---

## Scenario D — Exposing the service

The app binds to `0.0.0.0:8000` in all three scenarios above, so it's already reachable from anywhere your network reaches the host. Below is how to make that safe and intentional.

### LAN access only

1. Find the host IP: `ip -4 addr show` (Linux) or `ipconfig` (Windows) or `ifconfig` (macOS). Typically something like `192.168.1.42`.
2. Open the port through the host firewall:

   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp    # Ubuntu/Debian
   sudo firewall-cmd --add-port=8000/tcp --permanent && sudo firewall-cmd --reload   # Fedora/RHEL
   ```
3. From another machine on the same LAN: `curl http://192.168.1.42:8000/health`.

### CORS — important

`ALLOWED_ORIGINS` is currently **hardcoded** in `app/main.py` to:

```
http://localhost:8081, http://127.0.0.1:8081,
http://localhost:19006, http://127.0.0.1:19006
```

If your frontend runs on a different origin (e.g., `http://192.168.1.42:8081`), the browser will block the request even though the API responds. Edit `app/main.py` and add your origin to the `ALLOWED_ORIGINS` list, then redeploy.

(A future change will read this from `.env` — until then, it's a code edit.)

### Public internet via reverse proxy + TLS (Caddy)

**Do not expose port 8000 directly to the internet.** Run behind a reverse proxy that terminates TLS.

Caddy is the lowest-friction option — it auto-provisions Let's Encrypt certificates.

```bash
sudo apt install caddy   # or: brew install caddy / dnf install caddy
```

Create `/etc/caddy/Caddyfile`:

```caddy
api.school.example.com {
    reverse_proxy localhost:8000
}
```

Reload:

```bash
sudo systemctl reload caddy
```

Caddy will fetch a certificate the first time `api.school.example.com` is hit. Make sure:
- DNS A record points at your server's public IP.
- Router forwards ports **80 and 443** to the server (Caddy uses both — 80 for the ACME challenge, 443 for HTTPS).
- Host firewall allows 80 and 443.

### Public internet via reverse proxy + TLS (nginx)

If you'd rather use nginx, the equivalent is:

```nginx
server {
    listen 443 ssl http2;
    server_name api.school.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.school.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.school.example.com/privkey.pem;

    client_max_body_size 50M;   # uploads endpoint accepts files

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Issue the certificate with `certbot --nginx -d api.school.example.com`.

### Firewall baseline (Ubuntu / `ufw`)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # SSH — consider restricting to your IP
sudo ufw allow 80/tcp        # HTTP (ACME challenge)
sudo ufw allow 443/tcp       # HTTPS
sudo ufw enable
```

Don't expose 8000 publicly — let only the reverse proxy reach it on `localhost`. Consider `fail2ban` for SSH.

### Trusted proxy headers

The Dockerfile already starts uvicorn with `--proxy-headers --forwarded-allow-ips '*'`. With those flags, FastAPI honors `X-Forwarded-For` and `X-Forwarded-Proto` from the reverse proxy. The systemd unit in Scenario C includes the same flags.

---

## Health check & smoke testing

```bash
curl http://<host>:8000/health    # {"status":"healthy","version":"1.0.0"}
curl http://<host>:8000/          # {"message":"School Management API","version":"1.0.0","docs":"/api/docs"}
```

**Important:** `/health` currently checks only that the FastAPI process is up — **it does not verify the database is reachable**. The Docker `HEALTHCHECK` will still report healthy if Postgres is down. For real availability monitoring, check that a simple authenticated endpoint (e.g., `/api/v1/dashboard/stats` after logging in) returns 200.

---

## Common configuration

A minimal `.env` for each scenario:

| Variable | A: Docker + Postgres | B: Docker + SQLite | C: Bare-metal |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` | `sqlite+aiosqlite:////data/app.db` | either |
| `SECRET_KEY` | required | required | required |
| `DEBUG` | `false` | `false` | `false` |
| `REDIS_URL` | only if using Celery | only if using Celery | only if using Celery |
| `GOOGLE_*` | if using Google login | if using Google login | if using Google login |
| `MAIL_*` | if sending email | if sending email | if sending email |

`DEBUG=true` echoes every SQL statement to stdout (via SQLAlchemy `echo=`) — useful for development, **noisy and a log-volume cost in production**. Keep it off in any shared environment.

For the full table of env vars (Sentry, mail, frontend URL, etc.), see [`../DEPLOYMENT.md` §2](../DEPLOYMENT.md#2-environment-variables).

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError` on boot | `uv sync` not run / Docker image stale → rebuild |
| `connection refused` to Postgres | Wrong host in `DATABASE_URL`; from a container, use `host.docker.internal` or attach to the same network |
| `sqlite3.OperationalError: unable to open database file` | The path in `DATABASE_URL` isn't writable by uid 1000 in the container, or the volume isn't mounted |
| Browser shows CORS error, but `curl` works | Your frontend origin isn't in the hardcoded `ALLOWED_ORIGINS` (see Scenario D) |
| 401s on every request after a restart | `SECRET_KEY` changed → all JWTs invalid → users must re-login |
| Permission denied writing `uploads/` | Volume not owned by uid 1000 (the `app` user in the Dockerfile); `chown -R 1000:1000` the volume contents |
| Healthcheck green but the app errors on every request | `/health` doesn't check the DB — see the note above |

---

## When to move to the production guide

Switch to [`../DEPLOYMENT.md`](../DEPLOYMENT.md) once you're hosting real student data. It covers what this guide deliberately doesn't: managed-cloud setup, FERPA compliance, encrypted-at-rest backups, observability with Sentry, sub-processor disclosure, and the pre-launch checklist.
