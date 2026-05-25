# Strava Goal Visualizer — Claude Code Guide

## Project Overview

FastAPI backend + Streamlit frontend + PostgreSQL. Strava OAuth for authentication. Users visualize yearly running goals and club progress.

- **Backend:** `backend/` — FastAPI (async), SQLAlchemy async, Alembic migrations, slowapi rate limiting
- **Frontend:** `frontend/` — Streamlit
- **DB:** PostgreSQL via SQLAlchemy async + Alembic
- **Tests:** `tests/`

---

## Mandatory Workflow — Follow Strictly

Every task follows this exact sequence (see `docs/workflow.md` for authoritative version):

### 1. PLAN MODE
- Read only the relevant task from `docs/epics/backlog.md` (not the whole file)
- Consult `docs/design.md` only when architecture decisions are needed
- Identify scope, gaps, and questions
- **STOP if any uncertainty exists — ask before proceeding**

### 2. EXEC MODE
- Only after explicit approval from user ("yes", "looks good", "go ahead", etc.)
- Implement minimal solution — no scope expansion, no silent refactors
- If something broken is found outside scope: flag it and ask — never fix silently

### 3. VALIDATION MODE
- Explain changes made
- Provide test steps
- List edge cases

---

## Task Rules

- **Backlog-first:** Prefer tasks from `docs/epics/backlog.md`
- **Completed tasks:** Mark as `✅` in the task heading (e.g., `#### TASK-1.1 ✅`)
- **Ad-hoc tasks:** Allowed when explicitly requested; update backlog afterward
- **One task = one commit** — no mixing, no hidden refactors

## Commit Format (Conventional Commits)

```
feat(auth): add session cookie issuance on OAuth callback
fix(sync): handle 429 from Strava correctly
chore(deps): add httpx to pyproject.toml
```

---

## Architecture Patterns

- **Services:** `backend/services/` — business logic (e.g., `StateTokenService`, `StravaOAuthService`)
- **Helpers:** `backend/helpers/` — utilities (`config.py`, `crypto.py`)
- **DB models:** `backend/db/models.py` — SQLAlchemy ORM
- **DB session:** `backend/db/db.py` — async engine + `get_db` dependency
- **Dependencies:** `backend/dependencies.py` — FastAPI `Depends()` factories
- **Migrations:** `backend/db/migrations/versions/` — Alembic migration files
- **Config:** `backend/helpers/config.py` — `Settings` dataclass + `settings` singleton; add new required vars to `_REQUIRED_ENV_VARS`
- **Crypto:** `backend/helpers/crypto.py` — Fernet encrypt/decrypt for OAuth tokens

## Key Design Constraints

- Only `sport_type = 'Run'` activities count toward any metric — enforced at query time, never at storage time
- Tokens are never logged anywhere
- Rate limiting via `slowapi` on all auth, sync, and privacy endpoints
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`; rotated on every login
- CORS: strict allowlist to `settings.frontend_origin` only

---

## Where to Find Things

- **Backlog + task status:** `docs/epics/backlog.md`
- **Design decisions:** `docs/design.md`
- **Workflow rules:** `docs/workflow.md`
- **Env var schema:** `.env.example`
