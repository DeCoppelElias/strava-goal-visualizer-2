# Design: Production Deployment Guide + Deploy Readiness Tasks

**Date:** 2026-06-19
**Scope:** TASK-10.1 (deployment guide), TASK-8.3 (production Dockerfile), TASK-8.4 (fly.toml)

---

## Context

The app (FastAPI + React + PostgreSQL) is feature-complete but not yet deployed. No production Dockerfile, no Fly.io config, and no deployment guide exist. This spec covers:

1. Making the code deploy-ready (two new backlog tasks in EPIC-8)
2. Writing the authoritative deployment guide (`docs/ops/deployment.md`)

---

## Architecture Decision: Single Fly.io App (Option B)

The frontend React app is built into static files at deploy time and served by FastAPI alongside the API. This avoids cross-origin session cookie issues that arise when backend and frontend are on separate `*.fly.dev` domains (which are separate registrable domains per the Public Suffix List — `SameSite=Lax` cookies would not be sent on cross-origin fetch calls).

**Production topology:**
- One Fly.io app: FastAPI serves both the API and the built React static files
- One Fly Postgres: managed database, connected via `DATABASE_URL` secret
- Local dev: unchanged — docker-compose runs three containers (backend, Vite dev server, Postgres)

---

## Part 1: New Backlog Tasks (EPIC-8)

### TASK-8.3 — Production Dockerfile (multi-stage)

A new `Dockerfile` at the **repo root** used exclusively by Fly.io. The existing `backend/Dockerfile` and `frontend/Dockerfile` remain untouched for local dev via docker-compose.

**Build stages:**

**Stage 1 — frontend build (Node 22-alpine):**
- `npm ci` in `frontend/`
- `npm run build` with `VITE_API_BASE_URL=""` (empty string → all API calls become relative paths, e.g. `/sync` instead of `http://localhost:8000/sync`)
- Output: `frontend/dist/`

**Stage 2 — backend runtime (python:3.12-slim):**
- Install uv, sync backend dependencies from lockfile
- Copy `backend/`, `alembic.ini`, `frontend/dist/` from Stage 1
- CMD: same as `backend/Dockerfile` (uvicorn with `--proxy-headers --forwarded-allow-ips=*`)

**FastAPI changes (`backend/main.py`):**
- Mount `StaticFiles` at `/assets` pointing to `frontend/dist/assets/` (JS/CSS bundles)
- Add a catch-all `GET /{full_path:path}` route returning `frontend/dist/index.html` for any path not matched by the API — this is required for client-side React Router to work when users navigate directly to a URL or refresh the page
- The catch-all must be registered **after** all API routers so it never shadows an API route

**`FRONTEND_ORIGIN` in production:**
- Set to the same origin as the backend (e.g. `https://<app-name>.fly.dev`) — CORS is effectively a passthrough since frontend and backend share one origin, but the env var must still be set correctly

### TASK-8.4 — `fly.toml`

A `fly.toml` at the repo root configuring the Fly.io app:
- `[build]` — uses the root `Dockerfile`
- `[[services]]` — HTTP on internal port 8000, force HTTPS
- `[services.concurrency]` — sensible defaults for a small personal app
- `[[services.http_checks]]` — health check pointing at `/health`
- `[env]` block — documents non-secret env vars that can be baked in (e.g. `SESSION_COOKIE_SECURE=true`); secret vars (keys, credentials) are set via `fly secrets set` and must not appear here

---

## Part 2: `docs/ops/deployment.md`

The guide is written assuming TASK-8.3 and TASK-8.4 are complete (the production Dockerfile and `fly.toml` exist). It documents deployment from a fresh environment.

### Structure

**1. Architecture**
Brief diagram/description: one Fly.io app + one Fly Postgres. Explains why the single-app approach is used (session cookie same-origin requirement).

**2. Prerequisites**
- `flyctl` installed and authenticated (`fly auth login`)
- Strava app redirect URI updated to `https://<app-name>.fly.dev/oauth/callback` in the Strava developer portal (must be done before first login attempt)
- Docker available locally (needed for `fly deploy` build)

**3. Production env var reference**
Table of all env vars from `.env.example` with production-appropriate values:

| Variable | Production value |
|---|---|
| `DATABASE_URL` | Set automatically when Fly Postgres is attached |
| `STRAVA_CLIENT_ID` | Your Strava app client ID |
| `STRAVA_CLIENT_SECRET` | Your Strava app client secret |
| `STRAVA_REDIRECT_URI` | `https://<app-name>.fly.dev/oauth/callback` |
| `SESSION_SECRET_KEY` | Generated secret (32-byte hex) |
| `SESSION_COOKIE_SECURE` | `true` (default — do not set) |
| `TOKEN_ENCRYPTION_KEY` | Generated Fernet key |
| `VITE_API_BASE_URL` | `""` (empty — baked in at build time, not a runtime secret) |
| `FRONTEND_ORIGIN` | `https://<app-name>.fly.dev` |
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | Generated random string |
| `STRAVA_WEBHOOK_SUBSCRIPTION_ID` | Set after webhook registration (Step 6) |
| `SYNC_COOLDOWN_SECONDS` | Omit (use default: 600) |

**4. Initial setup**
```bash
# Create the Fly.io app
fly launch --no-deploy

# Create and attach Fly Postgres (sets DATABASE_URL secret automatically)
fly postgres create --name <db-app-name>
fly postgres attach <db-app-name>

# Set all remaining secrets in one command
fly secrets set \
  STRAVA_CLIENT_ID=... \
  STRAVA_CLIENT_SECRET=... \
  STRAVA_REDIRECT_URI=https://<app-name>.fly.dev/oauth/callback \
  SESSION_SECRET_KEY=... \
  TOKEN_ENCRYPTION_KEY=... \
  FRONTEND_ORIGIN=https://<app-name>.fly.dev \
  STRAVA_WEBHOOK_VERIFY_TOKEN=...
```

**5. Run migrations**
```bash
fly ssh console -C "alembic upgrade head"
```
Note: the app must be deployed (Step 6) before this works. Alternatively, migrations run automatically on startup via the existing lifespan handler in `main.py` — so this step is only needed if you want to run them manually or verify.

**6. Deploy**
```bash
fly deploy
```
Fly.io builds the multi-stage Dockerfile, pushes the image, and starts the app.

**7. Webhook registration** (absorbed from `docs/ops/webhook-registration.md`)
Full content of the existing webhook-registration.md moved here as a section. Covers: registering the subscription, saving `STRAVA_WEBHOOK_SUBSCRIPTION_ID`, verifying, deleting/rotating.

**8. Post-deploy verification**
```bash
curl https://<app-name>.fly.dev/health      # → {"status":"ok"}
curl https://<app-name>.fly.dev/health/db   # → {"db":"ok"}
```
Then manually: open the app in a browser, complete the Strava OAuth login, trigger a sync, verify the dashboard loads.

### `docs/ops/webhook-registration.md`
Replaced with a one-paragraph redirect stub:
> Webhook registration is documented in [docs/ops/deployment.md — Webhook Registration](deployment.md#webhook-registration).

---

## Implementation Order

1. **TASK-8.3** — production Dockerfile + `main.py` static serving (code changes)
2. **TASK-8.4** — `fly.toml` (config file)
3. **TASK-10.1** — write `docs/ops/deployment.md` + stub out `webhook-registration.md`

TASK-10.1 should be written after 8.3 and 8.4 so the guide can reference exact commands and config that actually exist in the repo.
