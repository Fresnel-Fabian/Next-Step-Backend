# Deployment

Production deployment guide for the Next-Step backend. Audience: whoever (you or a future maintainer) is responsible for standing up staging or production.

This document is **opinionated, not exhaustive**. It assumes a managed container host (Render, Fly.io, Railway, AWS App Runner, GCP Cloud Run, or similar). If you're going to self-host on a VPS, sections on TLS, backups, and process supervision are on you to expand.

---

## Contents

1. [Architecture overview](#1-architecture-overview)
2. [Environment variables](#2-environment-variables)
3. [Secrets management](#3-secrets-management)
4. [Database & migrations](#4-database--migrations)
5. [File storage (uploads/)](#5-file-storage-uploads)
6. [Build & run with Docker](#6-build--run-with-docker)
7. [Health checks](#7-health-checks)
8. [Observability: Sentry & logs](#8-observability-sentry--logs)
9. [Backups & disaster recovery](#9-backups--disaster-recovery)
10. [FERPA & data handling](#10-ferpa--data-handling)
11. [Pre-launch checklist](#11-pre-launch-checklist)

---

## 1. Architecture overview

```text
                       ┌─────────────┐
   Expo app (iOS/      │  Frontend   │
   Android/web)  ─────▶│ (Next-Step- │
                       │  Frontend)  │
                       └──────┬──────┘
                              │ HTTPS
                              ▼
                       ┌─────────────┐    ┌──────────────┐
                       │  FastAPI    │───▶│  Postgres    │
                       │  (this app) │    │  (managed)   │
                       └──────┬──────┘    └──────────────┘
                              │
                              ├──▶ Redis (Celery broker)
                              ├──▶ Sentry (errors)
                              └──▶ Object storage (uploads) — see §5
```

Components you need running in production:

| Component  | Required? | Notes |
|------------|-----------|-------|
| FastAPI    | ✅ | This service. 2+ uvicorn workers, behind a TLS-terminating proxy. |
| Postgres   | ✅ | Managed (recommended): Supabase, Neon, Render Postgres, RDS. |
| Redis      | ⚠️ Optional today | Required if/when Celery tasks are introduced. Currently `app/tasks/` is empty. |
| Object storage | ⚠️ Recommended | S3 / R2 / GCS for `uploads/`. See §5. |
| Sentry     | ⚠️ Recommended | Free tier is enough to start. |

---

## 2. Environment variables

Full list with examples in [`.env.example`](.env.example). Production overrides:

| Variable | Required | Production value |
|---|---|---|
| `DEBUG` | ✅ | `false` |
| `ENVIRONMENT` | ✅ | `production` (or `staging`) |
| `DATABASE_URL` | ✅ | Managed Postgres URL with `postgresql+asyncpg://` scheme |
| `SECRET_KEY` | ✅ | 32+ bytes hex, **unique per environment** |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated frontend origins, e.g. `https://app.school.edu,https://admin.school.edu` |
| `REDIS_URL` | If using Celery | Managed Redis URL |
| `SENTRY_DSN` | Recommended | From sentry.io project settings |
| `SENTRY_TRACES_SAMPLE_RATE` | Optional | `0.1` is a sane start; raise to `1.0` only during incident debugging |
| `GOOGLE_WEB_CLIENT_ID` / `GOOGLE_CLIENT_IDS` | If using Google login | Comma-separated list of all OAuth client IDs (web, iOS, Android) |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | If sending email | Use a service account, not a personal Gmail |
| `FRONTEND_URL` | If sending email | Public URL used to build invite/reset links |

### Generating `SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate a new one for each environment. **Rotating `SECRET_KEY` invalidates all issued JWTs** — plan accordingly.

---

## 3. Secrets management

**Do not commit `.env`.** Hand secrets to the host via its native mechanism:

| Host | How |
|---|---|
| Render | Dashboard → Service → Environment → Add Secret |
| Fly.io | `fly secrets set SECRET_KEY=... DATABASE_URL=...` |
| Railway | Dashboard → Variables (mark as sealed) |
| AWS App Runner / ECS | AWS Secrets Manager; inject via task definition |
| GCP Cloud Run | Google Secret Manager; reference via `--update-secrets` |

### Handover checklist

When handing the application to the school's IT team:

- [ ] Generate a **fresh** `SECRET_KEY` for their environment — never share the dev one.
- [ ] Generate a separate Google OAuth client ID for their domain (`apps.googleusercontent.com`); do not share the dev client.
- [ ] Create a dedicated Sentry project for them; give them the DSN, not the dev DSN.
- [ ] Give them a `.env.example` (in the repo) — not a populated `.env`.
- [ ] Document who has access to which secret store, and how to rotate each secret.

### What to do if a secret leaks

1. Rotate the affected secret immediately on the host (or in Secret Manager).
2. For `SECRET_KEY`: every issued JWT is now invalid; users must re-login. This is acceptable damage compared to the leak continuing.
3. For `DATABASE_URL` with credentials: rotate the Postgres password; update the URL.
4. If the leak hit Git history, scrub with `git filter-repo` or BFG and force-push (coordinate with all collaborators).

---

## 4. Database & migrations

### Migrations are run via Alembic, not auto-create

The app **no longer auto-creates tables in production**. `Base.metadata.create_all` runs only when `DEBUG=true`. In staging and production, run migrations explicitly:

```bash
alembic upgrade head
```

### Deploy ordering

1. Apply migrations (`alembic upgrade head`) — separate step, before traffic cuts over.
2. Roll new container image.
3. Smoke-test `/health` returns 200 with `db: ok`.
4. Promote traffic.

On most hosts, run migrations as a **pre-deploy command** (Render's "Pre-Deploy Command", Fly's `release_command`, etc.) so the deploy fails if migrations fail — better than a half-rolled deploy.

### Connection pool sizing

Default SQLAlchemy pool: 5 connections + 10 overflow per worker. With 2 uvicorn workers → up to 30 connections. Make sure your Postgres plan allows that. Most managed Postgres tiers have a connection cap (Supabase free = 60, Neon free = 100).

---

## 5. File storage (uploads/)

**Current state:** `app/main.py` mounts `uploads/` as a static directory. Files land on the container's local filesystem.

**Why this breaks in production:** containers are ephemeral. Every redeploy, restart, or scale-out loses everything in `uploads/`. This is fine for local dev, **not safe for a school app where uploaded documents (lesson plans, student work, transcripts) are expected to persist**.

### Options, in increasing order of "right"

| Option | When to use | Trade-offs |
|---|---|---|
| **Persistent volume** (Render Disk, Fly Volume) | MVP / single-instance only | Can't scale to multiple instances; backups are manual; cheap |
| **S3-compatible object storage** (AWS S3, Cloudflare R2, Backblaze B2) | Production | Right answer. Costs ~$0.015/GB/mo. Requires code change to upload via presigned URLs. |
| **Per-tenant encrypted bucket** | Multi-school SaaS | Overkill for one client; consider only if expanding. |

### If you go with S3/R2 (recommended)

Outline of the code change required (not yet implemented):

1. Add `boto3` (or `aioboto3`) to deps.
2. Add env vars: `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT_URL` (for R2/B2).
3. In `app/routers/documents.py`, replace `open(path, 'wb')` writes with `s3.put_object(...)` and serve downloads via **presigned URLs** that expire in minutes — never proxy through your app.
4. Remove the `app.mount("/uploads", ...)` static mount.
5. Keep `uploads/` in `.gitignore` and `.dockerignore`.

### FERPA implication

See §10. If files contain student PII, the bucket must be private (no public-read ACL), access logged, and the storage region documented.

---

## 6. Build & run with Docker

A production-grade `Dockerfile` is at the repo root. It's a multi-stage build (~150 MB final image) with a non-root user and a built-in `HEALTHCHECK`.

### Build & run locally

```bash
docker build -t next-step-backend .
docker run --rm -p 8000:8000 --env-file .env next-step-backend
```

### Run migrations against a running container

```bash
docker run --rm --env-file .env next-step-backend alembic upgrade head
```

### On a managed host

Most hosts just need:
- **Build command:** `docker build .` (or auto-detected from Dockerfile)
- **Start command:** unset (the Dockerfile `CMD` is correct)
- **Port:** `8000`
- **Pre-deploy:** `alembic upgrade head`
- **Health check path:** `/health`

---

## 7. Health checks

`GET /health` returns:
- `200 {"status": "healthy", "db": "ok", "version": "1.0.0"}` when the API process is up **and** Postgres is reachable.
- `503 {"status": "unhealthy", "db": "unreachable"}` when Postgres is down — the load balancer will stop routing to this instance.

Wire your host's health check to `/health`, not `/`. Tune timing so brief Postgres hiccups don't depool every instance:

- Interval: 30s
- Timeout: 5s
- Unhealthy threshold: 3 consecutive failures (≈90s)
- Healthy threshold: 2 consecutive successes

---

## 8. Observability: Sentry & logs

### Sentry

Set `SENTRY_DSN` to enable. The app already initializes Sentry with the FastAPI integration when the DSN is present. No code changes needed.

- `ENVIRONMENT` is passed to Sentry — keep `development` / `staging` / `production` distinct so you can filter.
- `SENTRY_TRACES_SAMPLE_RATE=0.1` collects performance traces on 10% of requests. Drop to `0.01` for cost; raise to `1.0` during incident triage.
- `send_default_pii=False` is set explicitly — Sentry will not collect request bodies or user IDs unless explicitly attached. **Important for FERPA** (§10).

### Logs

The app logs to stdout in a simple format. Managed hosts capture stdout automatically. For aggregation:

- **Render / Fly / Railway**: dashboard log viewer is enough to start. Stream to Logtail / Better Stack / Datadog when volume justifies.
- **Self-hosted**: pipe to `journald`, ship via Vector or Fluent Bit.

If you switch to structured (JSON) logs later, FastAPI works fine with `python-json-logger` — single dependency, replace `logging.basicConfig`.

---

## 9. Backups & disaster recovery

### Postgres

| Host | Backup behavior | Action required |
|---|---|---|
| Supabase | Daily snapshots, 7-day retention (free) → 30-day (Pro) | Verify in dashboard; nothing to set up |
| Neon | Point-in-time recovery (7 days, free) | Verify branch + restore steps |
| Render Postgres | Daily snapshots, 7-day retention | Verify; consider longer retention plan |
| Self-hosted | None unless you set it up | `pg_dump | gzip | aws s3 cp -` on cron |

**Test the restore.** Untested backups are not backups. Once per quarter:
1. Spin up a fresh Postgres instance.
2. Restore the latest snapshot.
3. Point a copy of the app at it; verify it boots and `/health` is green.

### Uploads

If on local disk: snapshot the volume daily.
If on S3/R2: enable versioning on the bucket; consider cross-region replication for a school's archival needs.

### Disaster recovery RTO/RPO

State these targets explicitly when handing over:
- **RPO** (data loss tolerance): "Up to 24 hours" (matches daily snapshot).
- **RTO** (time to restore): "Up to 2 hours" assuming the host is operational.

If the school requires tighter numbers, the answer is point-in-time recovery (Neon, RDS, Aurora) and an automated restore runbook.

---

## 10. FERPA & data handling

This app stores student personally identifiable information (PII): names, school emails, schedules, documents, possibly grade-adjacent data. In the US, this is **education records under FERPA** (20 U.S.C. § 1232g; 34 CFR Part 99).

> Disclaimer: this section is a starting point, not legal advice. The school's general counsel or compliance officer is the authority. Treat this as a checklist of things you need to be able to answer when they ask.

### Minimum bar to meet

| Requirement | How this app addresses it | Gaps to close before launch |
|---|---|---|
| **Data minimization** — store only what's needed for the educational purpose | Schemas store name, email, role, department only | Audit `documents/` — what's actually uploaded? Lock down file types/sizes. |
| **Access controls** — only authorized users access records | JWT auth + role checks (ADMIN/TEACHER/STUDENT) | Verify every router enforces role checks; audit `documents.py` access logic |
| **Audit logging** — who accessed what, when | ❌ Not implemented | Add access log table or use a structured log sink; required for FERPA disclosure tracking |
| **Encryption in transit** | TLS via host (managed) | Confirm host enforces HTTPS-only; HSTS header set |
| **Encryption at rest** | Managed Postgres providers do this by default | Confirm with chosen host (Supabase ✅, Neon ✅, Render ✅) |
| **Breach notification** | ❌ Not implemented | Document who is notified, how, within what timeframe — typically 60 days (state law varies) |
| **Data location / sovereignty** | Depends on host region | Pin Postgres + object storage to a US region; document this |
| **Retention & deletion** | ❌ No retention policy | Define: how long records kept after a student leaves; how a deletion request is honored |
| **Sub-processors** | Sentry, mail provider, OAuth provider, hosting | List all in a DPA (data processing agreement) with the school |

### Concrete things this app must do before serving real students

1. **Set `send_default_pii=False` in Sentry** — already done in `app/main.py`. Verify it stays that way.
2. **Don't log full request bodies or user emails at INFO level** — those go to log aggregators which may be outside the school's control. The current `app/main.py` logs validation errors and unhandled exceptions; review what those payloads contain.
3. **Document sub-processors**: hosting company, Sentry, mail provider, Google OAuth. The school will need this for their FERPA disclosure obligations.
4. **Implement an "export my data" and "delete my data" path** — typically admin-only endpoints. Not required day one, but required to honor parent/student requests.
5. **Region pinning**: choose a US region for Postgres and object storage (assuming a US school). Avoid hosts that move data without notice.

### Subscription / parental consent (if you serve under-13)

If the school enrolls students under 13, COPPA also applies. The standard pattern is: the **school** signs a written agreement that the app acts as a "school official" with a "legitimate educational interest" under FERPA — that allows the school to consent on behalf of parents.

Get this in writing **before** onboarding a school. Without it, you (or the school) carry direct COPPA liability.

---

## 11. Pre-launch checklist

Walk this once before pointing a real school at the app.

### Code/config

- [ ] `DEBUG=false` and `ENVIRONMENT=production` set
- [ ] `SECRET_KEY` is unique and not the dev value
- [ ] `ALLOWED_ORIGINS` lists only the real frontend URL(s) — no localhost
- [ ] `alembic upgrade head` runs cleanly against the production DB
- [ ] `Base.metadata.create_all` is gated by `DEBUG` (verify in `app/main.py`)
- [ ] `/health` returns 200 with `db: ok` against the prod DB
- [ ] Sentry receives a test event (`raise Exception("test")` from a non-prod build)
- [ ] `.gitignore` is valid and `uploads/` files are not in git history (run `git ls-files | grep uploads`)
- [ ] No `.env` file in git history

### Infrastructure

- [ ] Managed Postgres in a documented region
- [ ] Backups confirmed running and **restore tested**
- [ ] Object storage configured for `uploads/` (or persistent volume documented as a known limitation)
- [ ] TLS / HTTPS enforced at the edge
- [ ] Custom domain configured (if applicable)
- [ ] Pre-deploy command runs `alembic upgrade head`

### Operational

- [ ] Runbook for: "API is down" / "DB is full" / "Sentry showing error spike"
- [ ] On-call contact documented (who gets paged)
- [ ] Rollback procedure documented (redeploy previous image tag)
- [ ] Secret rotation procedure documented for `SECRET_KEY`, `DATABASE_URL`, mail/OAuth creds

### FERPA / legal

- [ ] Written agreement with the school designating the app as a "school official" under FERPA
- [ ] Privacy policy reviewed by school counsel
- [ ] Sub-processor list maintained and current
- [ ] Breach notification policy documented (who, when, how)
- [ ] Data retention and deletion procedure documented

### Frontend (separate repo — out of scope here, but listed for handoff completeness)

- [ ] `API_BASE_URL` points to production backend, not localhost
- [ ] EAS Build profiles configured (`development` / `preview` / `production`)
- [ ] App Store / Play Store listings prepared
- [ ] Push notification credentials (if used) in place

---

## Appendix: deciding the host

When the client agrees on hosting, the three realistic paths:

| Path | Best for | Watch out for |
|---|---|---|
| **Render** | Lowest friction, beginner-friendly | Cold starts on free tier; egress costs add up |
| **Fly.io** | Multi-region, persistent volumes built-in | More moving parts; Fly's Postgres is unmanaged (you back it up) |
| **AWS / GCP** | School IT department already uses it | Steeper learning curve; cost optimization is a real job |

For a single school client, **Render or Fly is the right starting point.** Migrate to a hyperscaler only if procurement requires it or scale demands it.
