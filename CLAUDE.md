# Strava Goal Visualizer — Claude Code Guide

## Project Overview

FastAPI backend + React frontend + PostgreSQL. Strava OAuth for authentication. Users visualize yearly running goals and club progress.

- **Backend:** `backend/` — FastAPI (async), SQLAlchemy async, Alembic migrations, slowapi rate limiting
- **Frontend:** `frontend/` — React + Vite (TypeScript); all API calls via `src/api/client.ts` with `credentials: 'include'`
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

## Domain Structure

Each business domain lives in its own folder under `backend/`. Every domain owns its routes, business logic, and schemas. Cross-cutting infrastructure lives in `shared/`.

```
backend/
  auth/          # OAuth flow, sessions, users, credentials
  sync/          # Activity fetch, upsert, cooldown (EPIC-3)
  goals/         # Goal CRUD, progress computation (EPIC-5)
  clubs/         # Club fetch, membership, progress view (EPIC-6)
  privacy/       # Export, deletion, deauth webhook (EPIC-7)
  shared/        # config, crypto, db, models, rate_limit — used by 2+ domains
  db/            # Alembic migrations only
  dependencies.py
  main.py        # Assembly only: middleware, routers, health endpoints
```

Each domain contains:
- `router.py` — `APIRouter` with all routes for this domain
- `schemas.py` — Pydantic request/response models
- `<name>_service.py` — business logic (no direct FastAPI imports)

**`shared/` rule:** A module belongs in `shared/` only if it is imported by two or more domains. Single-domain utilities live inside that domain.

## Dependency Injection Convention

- **Factory functions** in `backend/dependencies.py` construct service instances.
- **Singletons** (e.g., `_crypto`, `limiter`) are module-level in `dependencies.py` or `shared/`.
- **Endpoints never instantiate services directly** — always use `Depends(factory_fn)`.
- New services: add a factory function; register singletons at module level, not inside the factory.

```python
# dependencies.py — correct pattern
_crypto = Crypto(settings.token_encryption_key)   # singleton

def get_crypto() -> Crypto:
    return _crypto

def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service)
```

## Pydantic Schema Convention

- Every endpoint declares a `response_model=` with a named Pydantic `BaseModel`.
- Request body schemas also use named `BaseModel` classes.
- Schemas live in `<domain>/schemas.py`.
- Endpoints return the schema instance, not a raw dict.

```python
# auth/schemas.py
class AuthorizeResponse(BaseModel):
    authorization_url: str

# auth/router.py
@router.post("/oauth/authorize", response_model=AuthorizeResponse)
async def oauth_authorize(...) -> AuthorizeResponse:
    return AuthorizeResponse(authorization_url=url)
```

## Key Files

- **Config:** `backend/shared/config.py` — `Settings` dataclass + `settings` singleton; add new required vars to `_REQUIRED_ENV_VARS`
- **Crypto:** `backend/shared/crypto.py` — Fernet encrypt/decrypt for OAuth tokens
- **DB session:** `backend/shared/db.py` — async engine + `get_db` async generator
- **ORM models:** `backend/shared/models.py` — SQLAlchemy declarative models
- **Rate limiter:** `backend/shared/rate_limit.py` — shared `limiter` singleton (registered on `app.state`)
- **Migrations:** `backend/db/migrations/versions/` — Alembic migration files

## Key Design Constraints

- Only `sport_type = 'Run'` activities count toward any metric — enforced at query time, never at storage time
- Tokens are never logged anywhere
- Rate limiting via `slowapi` on all auth, sync, and privacy endpoints
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`; rotated on every login
- CORS: strict allowlist to `settings.frontend_origin` only
- **DB access:** Use the ORM for all CRUD on modelled tables — `db.add()` for inserts, `db.execute(select(...))` + `.scalar_one_or_none()` for reads, `db.delete(obj)` for deletes. Reserve `text()` for complex aggregates or window functions only

---

## Where to Find Things

- **Backlog + task status:** `docs/epics/backlog.md`
- **Design decisions:** `docs/design.md`
- **Workflow rules:** `docs/workflow.md`
- **Env var schema:** `.env.example`
