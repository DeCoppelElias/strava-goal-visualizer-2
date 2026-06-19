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
- Run `make ci` first to surface latent lint/type issues before starting — especially after a quiet period (commit hooks only check changed files). See `docs/learnings.md`
- **Skill:** invoke `brainstorming` before planning any new feature or non-trivial change
- Read only the relevant task from `docs/epics/backlog.md` (not the whole file)
- Consult `docs/design.md` when architecture decisions are needed
- Consult `docs/design/style.md` when front-end design desicions are made
- Identify scope, gaps, and questions
- **Skill:** invoke `writing-plans` to produce the structured implementation plan
- **STOP if any uncertainty exists — ask before proceeding**

### 2. EXEC MODE
- Only after explicit approval from user ("yes", "looks good", "go ahead", etc.)
- **Skill:** invoke `test-driven-development` before writing implementation code
- Implement minimal solution — no scope expansion, no silent refactors
- If something broken is found outside scope: flag it and ask — never fix silently
- **Skill:** invoke `systematic-debugging` when any bug or unexpected behaviour is encountered

### 3. VALIDATION MODE
- **Skill:** invoke `verification-before-completion` before marking a task `✅` or committing
- Explain changes made
- Provide test steps
- List edge cases
- **Learning notes:** summarize the non-obvious technical additions with a brief
  explanation of *why*, so the reviewer keeps learning while working with Claude
- **Out-of-scope flags:** surface any build errors or unrelated red herrings spotted
  during the work so they can be addressed later — flag, don't fix silently

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
- **Test fixtures:** `tests/conftest.py` — session-scoped Postgres container + per-test `db` `AsyncSession` for integration tests

## Key Design Constraints

- Only `sport_type = 'Run'` activities are stored — filtered at ingest time. Strava returns all activity types; the sync engine discards non-running activities before any DB write. All stored activities are runs.
- Tokens are never logged anywhere
- **Logging convention:** use a module-level `logger = logging.getLogger(__name__)`; `info` for normal lifecycle, `warning` for recoverable/expected external failures (e.g. Strava 429), `error` for unexpected failures. The per-request `request_id` is injected automatically by `RequestIdMiddleware` + `RequestIdFilter` (`backend/shared/logging.py`) — never pass it manually. Never log tokens or secrets.
- **Rate limiting via `slowapi` on every endpoint without exception.** Every new route must carry a `@limiter.limit(...)` decorator. See `docs/design.md` §6.0.3 for the approved limit per endpoint.
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`; rotated on every login
- CORS: strict allowlist to `settings.frontend_origin` only
- **DB access:** Use the ORM for all CRUD on modelled tables — `db.add()` for inserts, `db.execute(select(...))` + `.scalar_one_or_none()` for reads, `db.delete(obj)` for deletes. Reserve `text()` for complex aggregates or window functions only

---

## Testing Convention

Data-access logic is verified with **integration tests against a real PostgreSQL**, not mocks. A throwaway Postgres starts automatically via `testcontainers` (Docker must be running); use the `db` fixture in `tests/conftest.py` to get a per-test `AsyncSession` against a fresh schema.

- **Write an integration test** (use the `db` fixture) whenever the code emits SQL: Core DML (`insert`/`delete`/`on_conflict_*`), ORM persistence (`db.add` + flush), or aggregate/window queries. Assert on **actual row state read back from the DB** — never on `db.execute.call_count`.
- **A mock-based unit test is appropriate** only for pure logic with no SQL semantics (e.g. cooldown math, the `sport_type == "Run"` filter).
- The container starts once per test session; each test gets an isolated schema, so tests need no manual cleanup.

---

## Commands

All Python commands use `uv run`; frontend commands use `npm` from `frontend/`.

### Setup

```bash
# 1. Copy env template and fill in required values (Strava keys, secrets)
cp .env.example .env

# 2. Install all dependencies (backend + frontend + dev tooling)
make install-dev

# 3. Generate secret keys (run once, paste into .env)
python -c "import secrets; print(secrets.token_hex(32))"                         # SESSION_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # TOKEN_ENCRYPTION_KEY
```

### Database

```bash
# Start Postgres only (detached)
docker compose up db -d

# Run all pending migrations
uv run alembic upgrade head

# Create a new migration after changing models
uv run alembic revision --autogenerate -m "describe change"

# Downgrade one step
uv run alembic downgrade -1
```

### Backend (local, hot-reload)

```bash
# Requires Postgres running and .env present
uv run uvicorn backend.main:app --reload --port 8000

# API docs available at:
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)
# http://localhost:8000/health (health check)
```

### Frontend (local, hot-reload)

```bash
cd frontend
npm run dev       # starts Vite dev server at http://localhost:5173
npm run build     # production build (outputs to frontend/dist)
npm run preview   # serve the production build locally
```

### Full Stack (Docker Compose)

```bash
# Build and start all services (db, backend, frontend)
docker compose up --build

# Start in background
docker compose up --build -d

# Tail logs
docker compose logs -f

# Stop everything
docker compose down

# Stop and wipe the database volume
docker compose down -v
```

### Tests

```bash
make test                          # full suite with coverage
uv run pytest tests/               # same
uv run pytest tests/backend/auth/  # run a specific directory
uv run pytest -k "test_sync"       # filter by name
uv run pytest -x                   # stop on first failure
uv run pytest -v                   # verbose output
```

### Code Quality

```bash
make lint          # ruff linter
make format        # ruff formatter (writes changes)
make format-check  # formatter check only (no writes, used in CI)
make typecheck     # mypy strict type checking
make ci            # full CI suite: pre-commit + lint + format-check + typecheck
make pre-commit-run  # run all pre-commit hooks against all files
```

> **Run `make ci` at the start of a task and after any quiet period.** Commit
> hooks only check the files in each commit, so latent lint/type issues in
> untouched files won't surface until they block an unrelated commit. `make ci`
> re-checks the whole repo against current rules. See `docs/learnings.md`.

---

## Where to Find Things

- **Backlog + task status:** `docs/epics/backlog.md`
- **Design decisions:** `docs/design.md`
- **Workflow rules:** `docs/workflow.md`
- **Project learnings:** `docs/learnings.md`
- **Front-end style** `docs/design/style.md`
- **Env var schema:** `.env.example`
- **Test DB harness:** `tests/conftest.py`
