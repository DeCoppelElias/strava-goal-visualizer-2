# Strava Goal Visualizer — MVP Backlog

_Generated: May 2, 2026_

---

## Testing Convention

Data-access tasks are verified with integration tests against a real PostgreSQL via the `db` fixture in `tests/conftest.py` (introduced in TASK-6.2.1). Testability criteria below that read like "after sync, the table contains…" assume this harness — assert on real row state, not mock call counts.

---

## EPICS

---

### EPIC-1 — System Skeleton

**Purpose:** Get a runnable FastAPI backend and Streamlit frontend wired together with basic communication verified.

**Why it exists (system evolution order):** Nothing else can be tested or integrated until both processes are running and can talk to each other. This is the earliest possible working system.

**Included:**
- FastAPI app bootstrapped with CORS and a health endpoint
- Streamlit app bootstrapped and able to call the FastAPI health endpoint
- PostgreSQL connection verified from the backend
- Project structure, dependency management, environment variable schema
- Docker Compose for local development

**Excluded:**
- Any authentication
- Any Strava API calls
- Any business logic

---

### EPIC-1.5 — Architecture Foundation

**Purpose:** Establish domain-driven folder structure, per-domain APIRouters, Pydantic response schemas, and documented conventions before any real feature code is written.

**Why it exists (system evolution order):** EPIC-1 produced a working skeleton with a layer-based structure. Locking in the right patterns before EPIC-2 feature work is far cheaper than refactoring mid-development. Every subsequent epic builds on these conventions.

**Included:**
- Domain-based folder structure (`auth/`, `sync/`, `goals/`, `clubs/`, `privacy/`, `shared/`)
- APIRouter per domain; `main.py` becomes a pure assembly file
- Pydantic response schemas on all existing endpoints
- DI convention, schema convention, and domain structure documented in `CLAUDE.md` and `design.md`

**Excluded:**
- Any new features or business logic
- Repository pattern (excluded by design decision — services call SQLAlchemy directly)
- Custom exception hierarchy

---

### EPIC-2 — OAuth Authentication

**Purpose:** Implement the full Strava OAuth flow end-to-end: login, callback, session cookie issuance, session validation, and logout.

**Why it exists (system evolution order):** All product features require an authenticated user. This epic makes it possible to have a real user identity in the system. It must come before any data work.

**Included:**
- State token generation and server-side storage (10-minute TTL)
- Strava OAuth redirect and callback handling
- Token exchange and encrypted storage at rest
- User record creation/update on login
- Secure HTTP-only session cookie issuance (Secure, HttpOnly, SameSite=Lax)
- `GET /session/me` endpoint
- `POST /session/logout` endpoint
- `POST /oauth/revoke` endpoint
- `POST /oauth/authorize` endpoint
- CORS origin allowlist enforcement
- Per-IP rate limiting on auth endpoints
- Streamlit login page that initiates OAuth flow and reads session state
- Failure modes: state mismatch, token expired, partial scope, Strava error

**Excluded:**
- Activity sync
- Goals
- Clubs

---

### EPIC-3 — Activity Sync and Raw Data Display

**Purpose:** Fetch activities from Strava and display raw data in Streamlit. Proves the full vertical slice from Strava → backend → frontend works.

**Why it exists (system evolution order):** Before building any product UI, the core data pipeline must be proven end-to-end with real data. This is the earliest moment the system has actual value.

**Included:**
- `POST /sync` endpoint (triggers full activity fetch for authenticated user's own data, with cooldown enforcement)
- Activity fetch from Strava API (current-year activities only, paginated, full fetch — no incremental logic)
- Activity upsert into PostgreSQL (by Strava activity ID) — only `sport_type = 'Run'` activities are stored; non-running activities are discarded at ingest before any DB write (data minimization)
- Per-user cooldown enforcement: 10-minute cooldown, `429 Too Many Requests` + `Retry-After` on violation
- `last_sync_completed_at` timestamp stored per user
- Streamlit page that triggers sync and shows raw activity list

**Excluded:**
- Incremental or cursor-based sync
- Retry logic or backoff
- Sync status endpoint
- Auto-trigger on dashboard open
- Goals
- Club views

---



---

### EPIC-5 — Personal Goal Dashboard

**Purpose:** Let users set a yearly running goal and see their current-year progress visualized against it.

**Why it exists (system evolution order):** This is the core product value. It can only be built once real activity data is flowing (Epic 3+4) and the user is authenticated (Epic 2).

**Included:**
- `GET /goals` endpoint
- `PUT /goals` endpoint (validation: min 1 km, max 100,000 km, default 365 km)
- Goal stored per user in PostgreSQL
- Personal progress computation (current-year **running** distance vs. goal; only `sport_type = 'Run'` activities counted)
- Progress chart in Streamlit (distance to date, pace-to-goal line, goal line)
- Goal edit UI in Streamlit (immediate recalculation on save)
- Empty-state handling: no activities yet / sync pending

**Excluded:**
- Club views
- Privacy

---

### EPIC-6 — Club Progress View

**Purpose:** Show club members' progress against their individual goals, visible only to app-authorized club members.

**Why it exists (system evolution order):** Secondary product feature. Requires authenticated users, synced activities, and goals to all exist before club views are meaningful.

**Included:**
- `GET /clubs` endpoint (returns user's Strava clubs)
- `GET /dashboard/club/{club_id}` endpoint (returns progress for app-authorized members of that club who are also members)
- Club membership fetch from Strava API and storage
- Club membership refresh on each sync
- Authorization check: user must be a member of the club they query
- Club switcher UI in Streamlit
- Per-member progress display (each member's own goal used for their percentage; distance computed from **running activities only**, `sport_type = 'Run'`)
- Persistent non-competitive disclaimer on every club view
- Empty-state: user is only authorized member

**Excluded:**
- Cross-club aggregation
- Club-admin permission system

#### TASK-6.6 ✅

**Name:** Club progress chart

**Goal:** Add a multi-line progress chart to the club view showing each member's cumulative running distance over the current year on a shared axis with a linear pace reference line.

**Context:** Follow-up to TASK-6.5. Progress bars show current totals; the chart reveals how members' progress evolved over time. Requires backend changes to supply per-member daily series data efficiently in a single round trip.

**Input:** `GET /dashboard/club/{club_id}` (to be extended). `DashboardService` in `backend/dashboard/dashboard_service.py`. `ClubsPage.tsx` from TASK-6.5.

**Output:**
- `backend/dashboard/dashboard_service.py` — extract `_build_daily_series(activities: list[Activity]) -> list[DailyDistancePoint]` private helper from `get_personal_dashboard`; `get_club_dashboard` fetches all current-year activities for all club members in a single `WHERE user_id IN (...)` query, groups by `user_id` in Python, calls `_build_daily_series` per member
- `backend/dashboard/schemas.py` — add `daily_series: list[DailyDistancePoint]` to `MemberProgressResponse`
- `frontend/src/api/client.ts` — add `daily_series: DailyDistancePoint[]` to `MemberProgress`
- `frontend/src/components/ClubPaceChart.tsx` — new Recharts component: one `<Line>` per member (using `--accent` and derived palette), shared X-axis (day of year 1–365/366), Y-axis in km, linear pace reference line, legend with display names
- `frontend/src/pages/ClubsPage.tsx` — render `<ClubPaceChart>` above the member list when `clubDashboard.members.length > 0`

**Dependencies:** TASK-6.5

**Complexity:** Medium

**Testability:** Integration test: seed two users with known activity histories in same club → `GET /dashboard/club/{id}` returns correct `daily_series` per member with accurate cumulative values. Frontend: chart renders with one line per member; switching clubs re-renders with new data.

---

#### TASK-6.7 ✅

**Name:** Align personal and club chart styles

**Goal:** Make the personal dashboard chart visually consistent with the club chart — same line-draw animation, a dot at the end of each club member line, and a progress bar on the personal dashboard.

**Context:** TASK-6.6 delivered the club pace chart. The personal dashboard uses a different Recharts composition (`ComposedChart` + `Area`) which animates faster and looks different. The user prefers the club chart's slower line-draw feel and wants parity between the two views. All data is already available; this is frontend-only.

**Input:** `frontend/src/components/PaceChart.tsx`, `frontend/src/components/ClubPaceChart.tsx`, `frontend/src/pages/DashboardPage.tsx`

**Output:**
- `frontend/src/components/PaceChart.tsx` — replace `ComposedChart` + `Area` with `LineChart` + `Line` for the actual-km series. Recharts `Line` animates as a path draw (the same animation `ClubPaceChart` uses); `Area` in `ComposedChart` animates differently, causing the speed mismatch. Y-axis stays in km. The dot + km label at the last actual data point is preserved.
- `frontend/src/components/ClubPaceChart.tsx` — update `renderEndLabel` to also render a filled circle (`<circle>`) at the last data point of each member line, alongside the existing name text label.
- `frontend/src/pages/DashboardPage.tsx` — add a horizontal progress bar below the pace chart card, same markup pattern as `member-row__bar-track` / `member-row__bar-fill` in `ClubsPage.tsx`. Display: bar fill at `progress_pct%`, label showing `{progress_pct.toFixed(1)}% · {distance_to_date_km.toFixed(1)} / {goal_km} km`. Data already available in `PersonalDashboard`.

**Dependencies:** TASK-6.6

**Complexity:** Small

**Testability:** Frontend-only. Verify: personal chart line draws at the same speed as a club member line; a dot appears at the tip of each club member line; personal dashboard shows a filled progress bar with correct percentage and km values.

---

### EPIC-7 — Privacy and Account Deletion

**Purpose:** Provide self-service data export and full account deletion, and handle Strava's deauthorization callback with full data erasure.

**Why it exists (system evolution order):** Required by Strava's platform requirements and GDPR before any real users are onboarded to production.

**Included:**
- `POST /privacy/export` endpoint (generates and returns all user data)
- `POST /privacy/delete` endpoint (full erasure: user, tokens, activities, memberships; minimal audit log entry; session invalidation)
- `POST /strava/deauth` endpoint (Strava signature verification, full erasure, session invalidation, error logging)
- Privacy actions UI in Streamlit: export button, delete button with confirmation step
- Per-IP rate limiting on privacy endpoints
- Persistent GDPR document links visible on all pages (privacy policy, terms of service, data deletion info)

**Excluded:**
- Automated retention cleanup
- DSAR event log beyond minimal deletion event

---

### EPIC-8 — Operations & Observability

**Purpose:** Give the operator the two cheapest, highest-value production capabilities for a ~100–1000 user deployment on Fly.io: traceable logs with visibility at real failure points, and a documented way to read usage statistics from PostgreSQL.

**Why it exists (system evolution order):** Before onboarding real users, the operator needs to answer "what is going wrong?" and "how is the service doing?" without standing up a heavyweight observability stack.

**Included:**
- Plain-text logging refined with a per-request correlation id (request-id middleware + contextvar + logging filter)
- Explicit failure-point logging: Strava 429 rate limits, OAuth token-refresh failures, deauth webhook
- `docs/ops/db-statistics.md` — connect instructions (local + Fly) and a query catalogue
- `scripts/stats.sql` curated summary, run via documented local/Fly commands

**Excluded:**
- JSON / structured logging and log shipping (deferred; format isolated for an easy later switch)
- Error-tracking service (e.g. Sentry)
- `last_seen_at` column / real WAU–DAU metrics (deferred to a future task)
- Admin UI or admin endpoint

---

### EPIC-9 — Security & Privacy Hardening

**Purpose:** Close the findings from the pre-launch security/privacy audit (June 19, 2026). Scope is a small public personal project (~few hundred users); fixes are proportionate, not enterprise-grade.

**Why it exists (system evolution order):** The app is otherwise launch-ready — auth, access control, token encryption, and GDPR posture are all sound. These tasks resolve the specific gaps the audit flagged, ordered by severity. TASK-9.1 (HIGH) should land before public launch.

**Included:**
- `Secure` flag on the session cookie + privacy-policy accuracy (HIGH)
- Reducing forged-deletion risk on the unauthenticated Strava deauth webhook via a `subscription_id` filter + documented residual risk (LOW)
- Correct client-IP resolution behind the Fly.io proxy for rate limiting + logs (LOW)
- Squaring the deletion audit log with the "permanent erasure" privacy-policy claim (LOW)

**Excluded:**
- Verifying deauth events by calling Strava with the stored token before deleting (rejected — inverts the safe default; a transient Strava failure during a genuine deauth would skip a required erasure)
- Disabling `/docs` in production (INFO — endpoints are auth-gated; no action)
- Binding OAuth `state` to the browser session (INFO — random single-use token already provides CSRF protection)

**Open-source readiness check (June 2026):** This repo + its docs are intended to be published publicly under a license, so the audit also reviewed what publication exposes. Reusable checklist for future projects, with this project's outcome:

- **Secrets in tree _and_ in git history** — `git log --diff-filter=A -- '*.env' .env` must be empty; scan tracked files for key-shaped strings. _Result:_ clean — `.env` never committed, only a blank `.env.example` ships; matches were npm SRI hashes (public) and a fake test value. ✓
- **Infra details in docs/scripts** — ops docs must use placeholders, not real hostnames/app names/credentials. _Result:_ `docs/ops/db-statistics.md` + `scripts/stats.sql` use `<db-app>`/`<db-name>`/`<password>` and illustrative numbers. ✓
- **Security-by-design, not by-obscurity** — confirm real protections key off `.env` secrets so source disclosure doesn't weaken them. _Result:_ signed sessions, Fernet token encryption, and OAuth state all depend on env secrets; the only obscurity-dependent mechanism (`subscription_id`, TASK-9.2) is documented as a speed bump, not a boundary. ✓
- **Personal data in tree** — names/emails baked into source. _Result:_ operator's real name in `LICENSE` + `config/site.ts` is *required* (copyright + GDPR controller disclosure); personal email appears in no tracked file; public-facing contact is the dedicated `goalvisualizer.support@gmail.com`. ✓
- **Personal data in commit metadata** — author name/email is exposed verbatim on publish and only scrubbable via history rewrite (`git filter-repo --mailmap`), much cheaper before the first public push. _Result:_ commit-author email is the operator's existing public GitHub identity → acceptable, no rewrite needed. A leftover `Ike@<hostname>` author on 4 commits is an auto-generated machine identity (not a routable address) → harmless; optional tidy only.
- **Public backlog advertises unfixed weaknesses** — an open security backlog is fine to publish, but land the highest-severity, currently-exploitable item first so the public repo isn't a pointer to a live gap. _Result:_ ship **TASK-9.1 (Secure cookie)** before/at publication; the remaining LOW items are fine to be public.

---

### EPIC-10 — Documentation Finishing

**Purpose:** Complete all public-facing and operator-facing documentation so the repo stands on its own after the app goes offline — a visitor or future operator can understand what was built, run it locally, and deploy it without guessing.

**Why it exists (system evolution order):** The app is feature-complete and hardened. What's missing is a coherent public face: the README has no description of what the app is, production deployment is undocumented, and the webhook registration doc is a loose orphan. This epic wraps that up before the repo is published and the app potentially goes offline.

**Included:**
- README overhaul: app description, feature list, screenshots, tech stack, corrected Node version requirement (22), docs index
- `docs/ops/deployment.md` — authoritative production deployment guide that absorbs `docs/ops/webhook-registration.md` (webhook registration becomes a section within the deployment guide)

**Excluded:**
- Infrastructure provisioning (Fly.io account setup, database creation) — operator responsibility
- CI/CD pipeline automation
- CONTRIBUTING.md — not expected to attract external contributors

---

---

## TASK BREAKDOWN

---

### EPIC-1 — System Skeleton

---

#### TASK-1.1 ✅

**Name:** Initialize project structure and dependency management

**Goal:** Create a clean, reproducible project layout with all dependencies declared.

**Context:** Establishes the base all other tasks build on. Should take 10 minutes for any developer to get a running local environment.

**Input:** `pyproject.toml` skeleton already exists in the repo root.

**Output:**
- `pyproject.toml` updated with: `fastapi`, `uvicorn`, `streamlit`, `psycopg2-binary` (or `asyncpg`), `sqlalchemy`, `cryptography`, `httpx`, `python-dotenv`
- `.env.example` file documenting all required environment variables: `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`, `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`, `FRONTEND_ORIGIN`, `SESSION_SECRET`
- `backend/` directory with `main.py`
- `frontend/` directory with `app.py`
- `README.md` local-dev quickstart section

**Dependencies:** None

**Complexity:** Small

**Testability:** `uv run uvicorn backend.main:app` starts without error. `uv run streamlit run frontend/app.py` starts without error.

---

#### TASK-1.2 ✅

**Name:** Bootstrap FastAPI app with health endpoint

**Goal:** FastAPI app starts, serves a health check, and is CORS-configured for the Streamlit origin.

**Context:** Needed before any frontend ↔ backend communication can be tested.

**Input:** `backend/main.py` skeleton from TASK-1.1.

**Output:**
- `GET /health` returns `{"status": "ok"}`
- CORS middleware configured with `FRONTEND_ORIGIN` from environment
- Structured logging initialized (plain text)
- App reads all required env vars on startup and fails fast with a clear error if any are missing

**Dependencies:** TASK-1.1

**Complexity:** Small

**Testability:** `curl http://localhost:8000/health` returns `{"status": "ok"}`. Startup with missing env vars prints a clear error and exits non-zero.

---

#### TASK-1.3 ✅ _(ad-hoc)_

**Name:** Extract backend config module

**Goal:** All environment variable loading is centralised in `backend/config.py` and imported by the rest of the backend. `backend/main.py` contains no env-loading logic.

**Context:** Added ad-hoc after TASK-1.2 because inline env loading in `main.py` does not scale as more modules need access to config values. Establishing the pattern now avoids a larger refactor later.

**Input:** `backend/main.py` from TASK-1.2.

**Output:**
- `backend/config.py` — loads `.env` via `python-dotenv`, defines a `Settings` dataclass with all currently required vars, fails fast on missing values with a clear error, exposes a module-level `settings` singleton. Comment marks where future required vars should be added.
- `backend/main.py` — imports `settings` from `backend.config`; all inline env logic removed.

**Dependencies:** TASK-1.2

**Complexity:** Small

**Testability:** `backend/main.py` imports without error when all vars are set. Missing a required var prints a clear error and exits 1.

---

#### TASK-1.4 ✅

**Name:** Bootstrap Streamlit app with health-check call

**Goal:** Streamlit app starts, displays an app title, and calls the FastAPI health endpoint to confirm backend connectivity.

**Context:** Validates that the frontend can reach the backend. First end-to-end communication check.

**Input:** `frontend/app.py` skeleton from TASK-1.1.

**Output:**
- Streamlit page titled "Strava Goal Visualizer"
- On load, calls `GET /health` via `httpx` (or `requests`)
- Shows "Backend: connected ✓" or "Backend: unreachable ✗" based on response
- `BACKEND_URL` read from environment

**Dependencies:** TASK-1.2

**Complexity:** Small

**Testability:** Both processes running locally. Streamlit page shows "Backend: connected ✓". Stop the backend; page shows "Backend: unreachable ✗".

---

#### TASK-1.5 ✅

**Name:** Set up PostgreSQL connection and verify from backend

**Goal:** Backend successfully connects to PostgreSQL on startup and exposes a `/health/db` endpoint confirming the connection.

**Context:** All subsequent epics require a working database connection. Fail-fast DB validation prevents silent misconfiguration.

**Input:** `DATABASE_URL` environment variable. FastAPI app from TASK-1.2.

**Output:**
- SQLAlchemy engine or `asyncpg` pool initialized on startup
- `GET /health/db` executes `SELECT 1` and returns `{"db": "ok"}` or `{"db": "error", "detail": "..."}` (no raw exception exposed)
- Startup fails with a clear error if `DATABASE_URL` is not set

**Dependencies:** TASK-1.2

**Complexity:** Small

**Testability:** `curl http://localhost:8000/health/db` returns `{"db": "ok"}` with a running PostgreSQL. With no DB, returns `{"db": "error"}` and startup logs the reason.

---

#### TASK-1.6 ✅

**Name:** Docker Compose for local development

**Goal:** `docker compose up` starts FastAPI, Streamlit, and PostgreSQL together with correct environment wiring.

**Context:** Removes local PostgreSQL setup friction for all future tasks. Every developer and CI step uses this.

**Input:** `backend/` and `frontend/` from prior tasks. `.env.example`.

**Output:**
- `docker-compose.yml` with services: `db` (postgres:16), `backend` (FastAPI), `frontend` (Streamlit)
- `.env` file (gitignored) sourced by Compose
- Health checks on all services
- Volume for PostgreSQL data persistence

**Dependencies:** TASK-1.4, TASK-1.5

**Complexity:** Small

**Testability:** `docker compose up` → all three containers healthy. `curl http://localhost:8000/health/db` returns ok. Streamlit shows "Backend: connected ✓".

---

### EPIC-1.5 — Architecture Foundation

---

#### TASK-1.5.1 ✅

**Name:** Restructure backend into domain folders

**Goal:** Move existing backend files into a domain-driven directory layout without changing any behavior.

**Context:** The current layer-based structure (`services/`, `helpers/`, `db/`) works for a skeleton but doesn't scale across multiple epics. Each business domain owns its code. `shared/` holds cross-cutting concerns. This is a pure refactor — all existing tests must pass unchanged after the move.

**Input:** Existing `backend/` structure from EPIC-1 and EPIC-2 tasks 2.1–2.4.

**Output:**
- `backend/shared/` — `config.py`, `crypto.py`, `db.py`, `models.py` (moved from `helpers/` and `db/`)
- `backend/auth/` — `state_token_service.py`, `strava_oauth_service.py` (moved from `services/`)
- `backend/dependencies.py` — all import paths updated to new locations
- `backend/main.py` — all import paths updated to new locations
- All existing tests pass with no changes to test files

**Dependencies:** TASK-1.3, TASK-2.4

**Complexity:** Small

**Testability:** `pytest` reports all 15 tests passing. `uvicorn backend.main:app` starts without import errors.

---

#### TASK-1.5.2 ✅

**Name:** Introduce APIRouter per domain and Pydantic response schemas

**Goal:** Move existing routes into domain-specific APIRouters and add Pydantic response models to all existing endpoints.

**Context:** All routes currently live directly on `app` in `main.py`. With the domain structure from TASK-1.5.1, each domain owns its routes via `APIRouter`. Pydantic response models give FastAPI the information it needs to generate correct OpenAPI docs and enforce response shape. This is a zero-behavior-change refactor — no new endpoints.

**Input:** Domain structure from TASK-1.5.1. Existing endpoints: `GET /health`, `GET /health/db`, `POST /oauth/authorize`.

**Output:**
- `backend/auth/router.py` — `APIRouter` containing `POST /oauth/authorize`
- `backend/auth/schemas.py` — `AuthorizeResponse(BaseModel)` with `authorization_url: str`
- `backend/main.py` — health endpoints with inline `HealthResponse` and `DbHealthResponse` schemas; includes auth router via `app.include_router()`; no inline route logic for auth
- All existing tests pass; `GET /docs` reflects correct response shapes for all endpoints

**Dependencies:** TASK-1.5.1

**Complexity:** Small

**Testability:** `pytest` reports all 15 tests passing. `GET /docs` shows `AuthorizeResponse` schema with `authorization_url` field. `POST /oauth/authorize` returns `{"authorization_url": "..."}` identically to before.

---

#### TASK-1.5.3 ✅

**Name:** Document architectural conventions in CLAUDE.md and design.md

**Goal:** Write down the domain structure, DI, and Pydantic schema conventions so every future task follows them without re-deriving the rules.

**Context:** Patterns that aren't written down don't get followed consistently. This task makes the conventions durable across all remaining epics. No code changes — documentation only.

**Input:** Refactored codebase from TASK-1.5.1 and TASK-1.5.2.

**Output:**
- `CLAUDE.md` updated:
  - Domain folder map with one-line purpose per domain
  - DI convention: factory functions in `dependencies.py`; singletons at module level; endpoints never instantiate services directly
  - Pydantic convention: every endpoint has a named response model; schemas live in `<domain>/schemas.py`
- `design.md` updated: new "Architecture Patterns" section covering domain structure, DI, and Pydantic schema conventions

**Dependencies:** TASK-1.5.2

**Complexity:** Small

**Testability:** `CLAUDE.md` and `design.md` reviewed against the four architectural decisions: domain folders ✓, APIRouter ✓, Pydantic schemas ✓, DI convention ✓.

---

#### TASK-1.5.4 ✅ _(ad-hoc)_

**Name:** Standardize database access to ORM pattern

**Goal:** All database operations on modelled tables use the SQLAlchemy ORM API; raw `text()` SQL is reserved for complex queries with no ORM equivalent.

**Context:** `StateTokenService` was using raw `text()` SQL for INSERT, SELECT, and DELETE on `oauth_state_tokens` despite `OAuthStateToken` being defined in `shared/models.py`. Discovered during TASK-2.7 implementation review.

**Input:** `StateTokenService` using raw SQL. `OAuthStateToken` model already in `shared/models.py`.

**Output:**
- `backend/auth/state_token_service.py` rewritten to use `db.add()`, `db.execute(select(...))`, `db.delete()`
- `tests/backend/auth/test_state_token_service.py` rewritten to test ORM behaviour (no SQL-string assertions)
- `docs/design.md` §6.0.4 documents the ORM access convention with the `text()` fallback rule
- `CLAUDE.md` updated with the database access rule

**Dependencies:** TASK-1.5.3

**Complexity:** Small

**Testability:** All 33 existing tests pass unchanged after the rewrite.

---

### EPIC-2 — OAuth Authentication

---

#### TASK-2.1 ✅

**Name:** Create users and OAuth credentials database schema

**Goal:** PostgreSQL tables for users and OAuth tokens exist with correct constraints.

**Context:** Required before any OAuth flow can persist data. Schema must enforce strict athlete-ID-based identity.

**Input:** SQLAlchemy setup from TASK-1.4.

**Output:**
- `users` table: `id` (PK), `strava_athlete_id` (unique, not null), `created_at`, `updated_at`
- `oauth_credentials` table: `id` (PK), `user_id` (FK → users, unique), `access_token_encrypted` (text), `refresh_token_encrypted` (text), `token_expires_at` (timestamptz), `scope` (text), `created_at`, `updated_at`
- `oauth_state_tokens` table: `token` (PK), `created_at`, `expires_at`
- Alembic (or equivalent) migration file
- All migrations applied automatically on backend startup in development

**Dependencies:** TASK-1.4

**Complexity:** Small

**Testability:** `\d users`, `\d oauth_credentials`, `\d oauth_state_tokens` in `psql` show correct schemas. Backend starts without migration errors.

---

#### TASK-2.2 ✅

**Name:** Implement token encryption utility

**Goal:** Provide encrypt/decrypt helpers for Strava tokens using `TOKEN_ENCRYPTION_KEY`.

**Context:** Tokens must be encrypted at rest before the OAuth flow stores anything. This utility is used by all token persistence code.

**Input:** `TOKEN_ENCRYPTION_KEY` env var (Fernet key or AES-256 key).

**Output:**
- `backend/shared/crypto.py` — `Crypto` class with `encrypt(plaintext: str) -> str` and `decrypt(ciphertext: str) -> str`; instantiated as a singleton in `backend/dependencies.py`
- Uses `cryptography` library (Fernet symmetric encryption)
- Raises a clear error on startup if `TOKEN_ENCRYPTION_KEY` is missing or invalid
- Tokens are never logged in this module

**Dependencies:** TASK-1.1

**Complexity:** Small

**Testability:** Unit test: `decrypt(encrypt(token)) == token`. Missing key raises on import. Encrypted value is not the plaintext.

---

#### TASK-2.3 ✅

**Name:** Implement OAuth state token generation and validation

**Goal:** Generate a signed, server-side state token with a 10-minute TTL and validate it on callback.

**Context:** CSRF protection for the OAuth flow. State tokens must be stored server-side and single-use.

**Input:** `oauth_state_tokens` table from TASK-2.1.

**Output:**
- `backend/auth/state_token_service.py` — `StateTokenService` class with:
  - `create_state_token(db) -> str`: inserts a new token with `expires_at = now() + 10min`, returns the token string
  - `validate_and_consume_state_token(db, token: str) -> bool`: checks existence and TTL, deletes the token on success, returns `False` on mismatch or expiry
- Token is a cryptographically random URL-safe string (32+ bytes)

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Unit tests: valid token returns `True` and is deleted. Expired token returns `False`. Unknown token returns `False`. Replay of consumed token returns `False`.

---

#### TASK-2.4 ✅

**Name:** Implement `POST /oauth/authorize` endpoint

**Goal:** Generate a state token, build the Strava OAuth URL, and return it to the frontend.

**Context:** Entry point for the login flow. Frontend redirects the browser to the returned URL.

**Input:** `STRAVA_CLIENT_ID`, `STRAVA_REDIRECT_URI` env vars. State token module from TASK-2.3.

**Output:**
- `POST /oauth/authorize` returns `{"authorization_url": "<strava_url>"}` with state embedded
- Required scopes: `activity:read_all,profile:read_all`
- No authentication required on this endpoint
- Per-IP rate limiting applied

**Dependencies:** TASK-2.3

**Complexity:** Small

**Testability:** `POST /oauth/authorize` returns a valid Strava authorization URL containing `state=`, `client_id=`, and `scope=activity:read_all,profile:read_all`. New state token row exists in DB.

---

#### TASK-2.5 ✅

**Name:** Implement `GET /oauth/callback` endpoint

**Goal:** Exchange the OAuth code for tokens, store encrypted tokens, create/update the user record, and issue a session cookie.

**Context:** Completes the OAuth flow. After this endpoint, the user is authenticated and has a session.

**Input:** `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` env vars. State token module. Encryption utility. Users + credentials tables.

**Output:**
- `backend/shared/config.py` — add `strava_client_secret: str` and `session_secret_key: str` to `Settings`; uncomment from `_REQUIRED_ENV_VARS`
- `backend/main.py` — add `SessionMiddleware` with `session_secret_key`, `https_only=True`, `same_site="lax"`
- `backend/auth/router.py` — `GET /oauth/callback` route (no JSON response schema; returns `RedirectResponse`)
- Validates `state` parameter using `validate_and_consume_state_token`; logs state mismatch as potential CSRF
- Exchanges `code` with Strava token endpoint
- Checks that both `activity:read_all` and `profile:read_all` scopes are present in the token response; rejects with re-consent redirect if either is missing
- Upserts user record by `strava_athlete_id`
- Stores encrypted tokens in `oauth_credentials`
- Issues a session via `request.session["user_id"] = user.id` (Starlette `SessionMiddleware` signs the cookie automatically)
- Session cookie is rotated (new value) on every successful login
- Redirects to Streamlit frontend on success
- Failure modes: state mismatch (log as potential CSRF), state expired, Strava error response, token exchange failure — each returns a clear error redirect

**Dependencies:** TASK-2.3, TASK-2.2, TASK-2.1, TASK-2.4

**Complexity:** Medium

**Testability:** End-to-end: complete Strava OAuth flow in browser → redirected to Streamlit → session cookie present in browser devtools → `GET /session/me` returns user profile.

---

#### TASK-2.6 ✅

**Name:** Implement session middleware and `GET /session/me`

**Goal:** Read the session cookie on every request, resolve the authenticated user, and expose a `/session/me` endpoint.

**Context:** All authenticated endpoints depend on this. Must be in place before any protected routes are built.

**Input:** Session cookie issued in TASK-2.5. Users table.

**Output:**
- `backend/dependencies.py` — `get_current_user(request, db) -> User` reads `request.session["user_id"]`, looks up user, raises `401` if missing/invalid
- `backend/auth/schemas.py` — `SessionMeResponse(BaseModel)` with `strava_athlete_id: int`, `created_at: datetime`
- `backend/auth/router.py` — `GET /session/me` returns `SessionMeResponse`; requires `get_current_user`
- No PII beyond athlete ID and timestamps returned

**Dependencies:** TASK-2.5

**Complexity:** Small

**Testability:** Authenticated request to `/session/me` returns user data. Request without cookie returns `401`. Request with tampered cookie returns `401`.

---

#### TASK-2.7 ✅

**Name:** Implement `POST /session/logout` and `POST /oauth/revoke`

**Goal:** Allow users to log out (clear session) and optionally revoke Strava tokens.

**Context:** Logout is required before the login flow can be considered complete. Revoke is needed for clean Strava token lifecycle.

**Input:** Session middleware from TASK-2.6. OAuth credentials table.

**Output:**
- `backend/auth/schemas.py` — `LogoutResponse(BaseModel)` with `ok: bool`; `RevokeResponse(BaseModel)` with `ok: bool`
- `backend/auth/router.py` — `POST /session/logout` clears `request.session`, returns `LogoutResponse`
- `backend/auth/router.py` — `POST /oauth/revoke` calls Strava revoke endpoint, deletes `oauth_credentials` row, clears `request.session`, returns `RevokeResponse`
- Both require authentication via `get_current_user`
- Tokens are never logged

**Dependencies:** TASK-2.6

**Complexity:** Small

**Testability:** After logout, `GET /session/me` returns `401`. After revoke, tokens are gone from DB. Calling logout twice is idempotent (second call returns `200`).

---

#### TASK-2.7.1 ✅ _(ad-hoc)_

**Name:** Add missing rate limits to `GET /session/me` and `POST /session/logout`

**Goal:** Apply the approved rate limits to the two implemented auth endpoints that were added without `@limiter.limit` decorators.

**Context:** TASK-2.6 and TASK-2.7 were implemented before the project-wide rate-limiting policy was formalised. Both endpoints are missing their decorators. All endpoints must carry a rate limit per `docs/design.md` §6.0.3.

**Input:** `backend/auth/router.py`.

**Output:**
- `GET /session/me` decorated with `@limiter.limit("60/minute")`
- `POST /session/logout` decorated with `@limiter.limit("10/minute")`
- Both route signatures gain a `request: Request` parameter (required by slowapi)
- Existing tests updated if the `request` parameter changes the call signature

**Dependencies:** TASK-2.7

**Complexity:** Small

**Testability:** `uv run pytest` passes. Both endpoints return `429` after exceeding their respective limits in a test.

---

#### TASK-2.8 ✅

**Name:** React login page and session state

**Goal:** React app displays a login page for unauthenticated users and a home page for authenticated users, using the session cookie set by the backend.

**Context:** Without a frontend login flow, the OAuth backend cannot be tested by a real user through the UI. React uses `fetch(..., { credentials: 'include' })` so the browser handles the session cookie natively — no workarounds needed.

**Input:** FastAPI OAuth endpoints from TASK-2.4 and TASK-2.5. Session endpoint from TASK-2.6.

**Output:**
- `frontend/src/api/client.ts` — `fetch` wrapper with `credentials: 'include'` on every call; typed functions: `getSessionMe()`, `postOAuthAuthorize()`, `postSessionLogout()`
- `frontend/src/App.tsx` — reads and clears `?error=` query param on mount; calls `getSessionMe()` on load; renders `LoginPage` or `HomePage` based on auth state
- `frontend/src/pages/LoginPage.tsx` — displays OAuth error messages; "Connect with Strava" button calls `postOAuthAuthorize()` then sets `window.location.href`
- `frontend/src/pages/HomePage.tsx` — shows athlete ID; "Logout" button calls `postSessionLogout()` then resets auth state
- `frontend/src/components/GdprFooter.tsx` — GDPR placeholder links rendered on all pages

**Dependencies:** TASK-2.6, TASK-2.7

**Complexity:** Small

**Testability:** Full browser flow: click "Connect with Strava" → complete OAuth → redirected back → React shows authenticated state with athlete ID → click Logout → returns to login page. Hard-refresh while logged in → still authenticated (cookie persists).

---

### EPIC-3 — Minimal Activity Sync and Raw Data Display

---

#### TASK-3.1 ✅

**Name:** Create activities and sync state database schema

**Goal:** PostgreSQL tables for activities and per-user sync state exist with correct constraints.

**Context:** Required before any sync logic can persist data.

**Input:** SQLAlchemy setup from TASK-1.4. Users table from TASK-2.1.

**Output:**
- `backend/shared/models.py` — `Activity` and `SyncState` ORM models added
- `activities` table: `id` (PK), `user_id` (FK → users), `strava_activity_id` (bigint, unique per user), `name` (text), `sport_type` (text), `distance_meters` (numeric), `moving_time_seconds` (int), `start_date` (timestamptz), `created_at`, `updated_at`
- Unique constraint on `(user_id, strava_activity_id)`
- `sync_state` table: `user_id` (PK, FK → users), `last_sync_completed_at` (timestamptz, nullable)
- Alembic migration file in `backend/db/migrations/versions/`

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Tables visible in `psql`. Backend starts without migration errors.

---

#### TASK-3.2 ✅

**Name:** Implement Strava API client (activity fetch)

**Goal:** A thin HTTP client that fetches activities for an authenticated user from the Strava API, handling pagination.

**Context:** Core I/O primitive for the sync engine. Used by all sync tasks. No retry logic.

**Input:** Strava access token (decrypted). `STRAVA_CLIENT_ID` env var.

**Output:**
- `backend/sync/strava_client.py` — `fetch_activities(access_token: str, page: int = 1) -> list[dict]`
- Fetches `GET https://www.strava.com/api/v3/athlete/activities` with bearer token
- Supports pagination via `page` and `per_page=200`
- Returns raw activity dicts (no transformation)
- Logs request count (not token)
- Raises typed exceptions for HTTP 401 and other HTTP errors

**Dependencies:** TASK-2.2

**Complexity:** Small

**Testability:** Integration test against Strava sandbox or real token: `fetch_activities(token)` returns a list of dicts. HTTP 401 raises the correct exception type.

---

#### TASK-3.3 ✅

**Name:** Implement token refresh utility

**Goal:** Silently refresh an expired Strava access token using the stored refresh token.

**Context:** Access tokens expire in 6 hours. All sync calls must ensure the token is valid before use.

**Input:** Encryption utility from TASK-2.2. `oauth_credentials` table. Strava token refresh endpoint.

**Output:**
- `backend/auth/token_refresh.py` — `ensure_fresh_token(db, user_id: int) -> str`:
  - Returns decrypted access token if not expired
  - If expired, calls Strava refresh endpoint, updates `oauth_credentials` with new encrypted tokens, returns new access token
  - If refresh fails (401 from Strava), raises `TokenRefreshError` (caller is responsible for session invalidation)
- Tokens are never logged

**Dependencies:** TASK-2.2, TASK-2.1

**Complexity:** Small

**Testability:** Unit test with mocked Strava: fresh token returned without refresh call. Expired token triggers refresh and DB update. Refresh failure raises `TokenRefreshError`.

---

#### TASK-3.3.1 ✅ _(ad-hoc)_

**Name:** Fix `token_expires_at` missing timezone on `OAuthCredentials`

**Goal:** Make `OAuthCredentials.token_expires_at` timezone-aware so that `ensure_fresh_token` does not crash on every call in production.

**Context:** `OAuthCredentials.token_expires_at` is declared as `mapped_column()` with no `DateTime(timezone=True)`. PostgreSQL therefore stores and returns a naive datetime. `ensure_fresh_token` subtracts `datetime.now(UTC)` (an aware datetime) from this naive value, which raises `TypeError: can't subtract offset-naive and offset-aware datetimes` on every invocation. By contrast, `Activity.start_date` and `SyncState.last_sync_completed_at` already correctly use `DateTime(timezone=True)`. This is a pre-production crash that blocks TASK-3.4.

**Input:** `backend/shared/models.py`. Alembic migration history in `backend/db/migrations/versions/`.

**Output:**
- `backend/shared/models.py` — `OAuthCredentials.token_expires_at` changed to `mapped_column(DateTime(timezone=True))`
- New Alembic migration that `ALTER COLUMN token_expires_at TYPE TIMESTAMPTZ USING token_expires_at AT TIME ZONE 'UTC'`
- `OAuthStateToken.expires_at` audited for the same issue and fixed if affected

**Dependencies:** TASK-3.3

**Complexity:** Small

**Testability:** `uv run pytest` passes. `ensure_fresh_token` called with a fresh-from-DB `OAuthCredentials` row does not raise `TypeError`. Migration applies cleanly against the existing schema.

---

#### TASK-3.3.2 ✅ _(ad-hoc)_

**Name:** Wrap httpx network errors in domain exceptions

**Goal:** Network-level failures (`ConnectError`, `TimeoutException`, etc.) from httpx are caught and re-raised as the correct domain exception in both `ensure_fresh_token` and `fetch_activities`, instead of propagating as raw `httpx.RequestError`.

**Context:** Both methods only catch `httpx.HTTPStatusError` (raised by `raise_for_status()`). A DNS failure, connection timeout, or TLS error raises `httpx.RequestError`, which is not a subclass of `HTTPStatusError` and therefore escapes all error handling, surfacing as an unhandled 500. Callers that catch `TokenRefreshError` or `StravaAPIError` to degrade gracefully will miss these failures entirely.

**Input:** `backend/auth/strava_oauth_service.py` — `ensure_fresh_token`. `backend/sync/strava_client.py` — `fetch_activities`.

**Output:**
- `ensure_fresh_token`: the entire `async with httpx.AsyncClient()` block wrapped in an outer `try/except httpx.RequestError` that raises `TokenRefreshError`
- `fetch_activities`: the same outer guard, raising `StravaAPIError`
- Tests added for both: mock `httpx.ConnectError` → correct domain exception raised

**Dependencies:** TASK-3.3, TASK-3.2

**Complexity:** Small

**Testability:** Unit tests: patching `httpx.AsyncClient` to raise `httpx.ConnectError` → `ensure_fresh_token` raises `TokenRefreshError`; `fetch_activities` raises `StravaAPIError`. Existing tests continue to pass.

---

#### TASK-3.3.3 ✅ _(ad-hoc)_

**Name:** Guard against malformed Strava token responses

**Goal:** Prevent unhandled `KeyError` when Strava returns an unexpected 200 OK body in `ensure_fresh_token`.

**Context:** After a successful HTTP POST to the token endpoint, `ensure_fresh_token` accesses `token_data["access_token"]`, `token_data["refresh_token"]`, and `token_data["expires_at"]` directly. These key lookups are outside the `try/except HTTPStatusError` block, so a 200 OK response with an unexpected body (e.g. Strava API change, rate-limit response shaped like success) raises an unhandled `KeyError` instead of a `TokenRefreshError`. Callers have no way to catch this.

**Input:** `backend/auth/strava_oauth_service.py` — `ensure_fresh_token`, specifically the block after `response.raise_for_status()`.

**Output:**
- The three key accesses wrapped in a `try/except KeyError` that raises `TokenRefreshError("Strava token response missing expected fields")`
- Test added: mock a 200 response with `{}` body → `TokenRefreshError` raised
- `# type: ignore[no-any-return]` on the final return replaced with an explicit `cast(str, ...)`

**Dependencies:** TASK-3.3

**Complexity:** Small

**Testability:** Unit test: patch `httpx.AsyncClient` to return `httpx.Response(200, json={})` → `ensure_fresh_token` raises `TokenRefreshError`. Existing passing tests unchanged.

---

#### TASK-3.3.4 ✅ _(ad-hoc)_

**Name:** Consolidate duplicate `StravaAPIError` class

**Goal:** Remove the two independent `StravaAPIError` definitions so callers can catch a single type for all Strava HTTP errors.

**Context:** `backend/auth/exceptions.py` and `backend/sync/exceptions.py` each define a `class StravaAPIError(Exception): pass`. These are separate Python types. A caller that imports `StravaAPIError` from one module will silently miss errors raised by code that imports from the other. Per the `shared/` rule ("a module belongs in `shared/` only if imported by two or more domains"), a single `StravaAPIError` belongs in `backend/shared/exceptions.py`. A combined error handler registered in `main.py` cannot currently catch both with one `except` clause.

**Input:** `backend/auth/exceptions.py`. `backend/sync/exceptions.py`. All call sites importing either class.

**Output:**
- New `backend/shared/exceptions.py` with a single `StravaAPIError(Exception)` base class
- `backend/auth/exceptions.py` — removes its local `StravaAPIError`; imports it from `backend.shared.exceptions`
- `backend/sync/exceptions.py` — removes its local `StravaAPIError`; imports it from `backend.shared.exceptions`
- All existing import paths updated across the codebase
- No behavior change; all existing tests pass

**Dependencies:** TASK-3.2, TASK-3.3

**Complexity:** Small

**Testability:** `from backend.auth.exceptions import StravaAPIError` and `from backend.sync.exceptions import StravaAPIError` resolve to the same class. `pytest` passes. `except StravaAPIError` in a single handler catches errors from both `fetch_activities` and `ensure_fresh_token`.

---

#### TASK-3.3.5 ✅ _(ad-hoc)_

**Name:** Add `fetch_all_activities` pagination helper

**Goal:** Prevent silent data loss for users with more than 200 activities by providing a single call that handles full pagination internally.

**Context:** `fetch_activities` fetches one page only. The TASK-3.4 sync engine is supposed to fetch all pages, but a bare `fetch_activities(token)` call looks complete, making it easy to write sync code that silently drops all activities beyond the first 200. Adding a `fetch_all_activities` helper that loops internally eliminates this footgun. TASK-3.4 should call `fetch_all_activities`, not `fetch_activities`, for the full sync.

**Input:** `backend/sync/strava_client.py`.

**Output:**
- `backend/sync/strava_client.py` — new `async def fetch_all_activities(access_token: str, *, after: int | None = None) -> list[dict[str, Any]]` that calls `fetch_activities` in a loop, incrementing `page`, and stops when a page returns fewer than `per_page` results
- `fetch_activities` kept as-is for single-page use and testability
- Tests: empty last page stops the loop; single full page + empty second page returns correct total; a user with exactly 200 activities (one full page) does not trigger a second unnecessary request

**Dependencies:** TASK-3.2

**Complexity:** Small

**Testability:** Unit tests using `respx`: 2 full pages + 1 empty page → correct combined list returned; 0 activities → empty list; exactly 200 activities (one full page, then empty) → only 2 requests made.

---

#### TASK-3.3.6 ✅ _(ad-hoc)_

**Name:** Define transaction ownership convention and fix service-level commits

**Goal:** Prevent service methods from committing an outer session they do not own, which would silently flush a caller's pending ORM state mid-operation.

**Context:** `ensure_fresh_token` calls `await db.commit()` after writing refreshed tokens. When TASK-3.4 implements the sync engine, it will likely stage ORM objects (e.g. a new `SyncState` row) on the same `AsyncSession` before calling `ensure_fresh_token` to get a token. The commit inside `ensure_fresh_token` would flush that partially-built state before the caller has validated or completed it, leaving the DB in an inconsistent state. `revoke_tokens` has the same pattern but is only called from a dedicated endpoint and is lower risk. The fix is for `ensure_fresh_token` to use a nested savepoint or require the caller to own the commit; the simplest option is to drop the commit from `ensure_fresh_token` and document that callers are responsible for committing the session.

**Input:** `backend/auth/strava_oauth_service.py` — `ensure_fresh_token`. `docs/design.md`.

**Output:**
- `ensure_fresh_token` drops its `await db.commit()` call; the method only modifies `creds.*` fields on the ORM object and returns the plaintext token
- All callers updated to commit after calling `ensure_fresh_token` (currently none outside tests)
- `docs/design.md` — new subsection under service conventions: "Transaction ownership: service methods mutate ORM objects but do not commit. The router or calling service owns `db.commit()`." (consistent with how `_upsert_credentials` in the same file already behaves)
- Tests updated: `db.commit.assert_not_called()` on the token-still-valid path stays; the refresh path now asserts the session was dirtied but commit is left to the caller

**Dependencies:** TASK-3.3

**Complexity:** Small

**Testability:** Unit tests pass. Calling `ensure_fresh_token` with an expired token updates `creds.*` fields but does NOT call `db.commit()`. The caller controls when to flush.

---

#### TASK-3.4 ✅

**Name:** Implement `POST /sync` endpoint

**Goal:** Trigger a full current-year activity sync for the authenticated user, with cooldown enforcement.

**Context:** Core sync endpoint. Fetches all current-year activities, upserts them, and records completion timestamp. Single synchronous operation with no state machine.

**Input:** Strava client from TASK-3.2. Token refresh from TASK-3.3. Activities + sync state tables from TASK-3.1. Auth middleware from TASK-2.6.

**Output:**
- `backend/sync/schemas.py` — `SyncResponse(BaseModel)` with `synced_activities: int`, `last_sync_completed_at: datetime`
- `backend/sync/router.py` — `POST /sync` route with `response_model=SyncResponse`; rate limited; requires `get_current_user`
- Validates ownership (own athlete ID only)
- Checks `last_sync_completed_at`; if within the last 10 minutes, returns `429 Too Many Requests` with `Retry-After: <seconds_until_eligible>` header
- Fetches all pages of current-year activities from Strava
- Filters fetched activities to `sport_type = 'Run'` before any DB write — non-running activities are discarded at ingest
- Upserts into `activities` table by `(user_id, strava_activity_id)` — only running activities stored
- On success: sets `last_sync_completed_at = now()`
- On failure: surfaces error directly; `last_sync_completed_at` is not updated
- Requires authentication; runs synchronously in-process

**Dependencies:** TASK-3.2, TASK-3.3, TASK-3.1, TASK-2.6

**Complexity:** Medium

**Testability:** Authenticated `POST /sync` returns 200 and `last_sync_completed_at` is set in DB. Activities rows present matching Strava data. Running sync twice in quick succession → second call returns `429` with `Retry-After` header. Running sync twice with mocked time gap → both succeed with no duplicate rows.

---

#### TASK-3.5 ✅

**Name:** React sync trigger page

**Goal:** React page allows the authenticated user to trigger a sync and see a confirmation of how many runs were synced.

**Context:** First moment the full vertical slice (Strava → backend → frontend) is visible to a user. Proves the entire pipeline works. Raw activity list is intentionally excluded — the dashboard (TASK-5.4) is where data is visualized.

**Input:** Sync endpoints from TASK-3.4. Auth state from TASK-2.8.

**Output:**
- `frontend/src/api/client.ts` extended with `postSync()` returning `{ synced_activities: number, last_sync_completed_at: string }`
- `frontend/src/pages/SyncPage.tsx` — "Sync Activities" button calls `POST /sync`; shows synced run count ("N runs synced") and last sync timestamp on success; cooldown error shown on 429 ("Sync unavailable — try again in X minutes")
- Authenticated app shell with navigation (`frontend/src/pages/HomePage.tsx` updated) to host current and future pages

**Dependencies:** TASK-3.4, TASK-2.8

**Complexity:** Small

**Testability:** Click "Sync Activities" → count and last sync timestamp appear. Clicking sync again within 10 minutes shows cooldown message with remaining time.

---

> **Note:** EPIC-4 was intentionally omitted. No tasks are missing.

---

### EPIC-5 — Personal Goal Dashboard

---

#### TASK-5.1 ✅

**Name:** Create goals database schema

**Goal:** PostgreSQL table for user goals exists with correct constraints and default value.

**Context:** Required before goal endpoints can persist data.

**Input:** Users table from TASK-2.1.

**Output:**
- `backend/shared/models.py` — `Goal` ORM model added
- `goals` table: `user_id` (PK, FK → users), `yearly_distance_km` (numeric, not null, default 365, check > 0 and <= 100000), `updated_at`
- Row auto-created on user creation (default 365 km)
- Alembic migration in `backend/db/migrations/versions/`

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** New user has a goal row with `yearly_distance_km = 365` after OAuth login. `psql` confirms constraint enforcement.

---

#### TASK-5.2 ✅

**Name:** Implement `GET /goals` and `PUT /goals` endpoints

**Goal:** Authenticated user can read and update their own yearly goal.

**Context:** Required for goal-based progress computation in the dashboard.

**Input:** Goals table from TASK-5.1. Auth middleware from TASK-2.6.

**Output:**
- `backend/goals/schemas.py` — `GoalResponse(BaseModel)` with `yearly_running_goal_km: float`; `UpdateGoalRequest(BaseModel)` with `yearly_running_goal_km: float`
- `backend/goals/router.py` — `GET /goals` (30/minute) returns `GoalResponse`; `PUT /goals` (10/minute) accepts `UpdateGoalRequest`, returns `GoalResponse`; both require `get_current_user`
- Both return `403` if user attempts to set another user's goal (enforced by `get_current_user`)

**Dependencies:** TASK-5.1, TASK-2.6

**Complexity:** Small

**Testability:** `GET /goals` returns default 365 for new user. `PUT /goals {"yearly_running_goal_km": 500}` → `GET /goals` returns 500. Values outside range return `422`.

---

#### TASK-5.3 ✅

**Name:** Implement personal progress computation

**Goal:** Backend computes current-year running distance and progress percentage against the user's goal.

**Context:** Core computation that powers the personal dashboard view.

**Input:** Activities table. Goals table. Auth middleware.

**Output:**
- `backend/goals/schemas.py` — `PersonalDashboardResponse(BaseModel)` with `goal_km`, `distance_to_date_km`, `progress_pct`, `on_pace`, `expected_pct`, `last_sync_completed_at` fields
- `backend/goals/router.py` — `GET /dashboard/personal` (30/minute) returns `PersonalDashboardResponse`; requires `get_current_user`
- Response shape:
  ```json
  {
    "goal_km": 365,
    "distance_to_date_km": 142.5,
    "progress_pct": 39.04,
    "on_pace": true,
    "expected_pct": 38.2,
    "last_sync_completed_at": "..."
  }
  ```
- Filters activities by `user_id` and `start_date` in current calendar year — all stored activities are already runs, no `sport_type` filter needed at query time
- `on_pace`: `distance_to_date_km >= expected_km_by_today` (linear pace model)
- Only own data returned (enforced by `get_current_user`)
- **No sync yet:** if `SyncState` row does not exist for the user, return `404` with `detail: "not_synced"`. This is distinct from a user who has synced but has zero running activities (returns 200 with `distance_to_date_km: 0`).

**Dependencies:** TASK-5.2, TASK-3.4

**Complexity:** Small

**Testability:** Seed known activities → call `GET /dashboard/personal` → verify computed values match manual calculation. Ensure another user's activities are not included. Verify 404 is returned when no SyncState exists.

---

#### AD-HOC ✅

**Name:** Move personal dashboard into `dashboard/` domain

**Goal:** Separate cross-domain dashboard logic from `GoalService` so goal CRUD stays clean and `/dashboard/*` routes have a dedicated home ahead of the club dashboard.

**Changes:** Created `backend/dashboard/` domain (`schemas.py`, `dashboard_service.py`, `router.py`). Removed `get_personal_dashboard` and `PersonalDashboardResponse` from goals domain. Updated `dependencies.py` and `main.py`. Moved all dashboard tests to `tests/backend/dashboard/`.

---

#### TASK-5.4 ✅

**Name:** Personal goal dashboard page

**Goal:** Extend the existing DashboardPage with goal progress chart, key stats, and goal edit control.

**Context:** Core product UI. First moment the app looks like an actual product. `DashboardPage.tsx` already exists from TASK-3.5 (sync button + result); this task adds the goal content below it.

**Input:** `GET /dashboard/personal`. `PUT /goals`. Sync button already in `DashboardPage.tsx` from TASK-3.5.

**Output:**
- `frontend/src/api/client.ts` extended with `getPersonalDashboard()` and `putGoal(km: number)`
- `frontend/src/pages/DashboardPage.tsx` extended with: progress bar (distance to date vs goal); pace line chart using Recharts (cumulative distance over year vs linear goal pace); key stats (total km, % complete, on-pace indicator); goal edit: number input + save button; last sync timestamp; empty state: "No running activities found — sync your data to get started"; GDPR links visible

**Dependencies:** TASK-5.3, TASK-3.5

**Complexity:** Medium

**Testability:** With synced data → dashboard shows correct distance and %. Update goal → progress % changes. Empty state shown for new user with no synced activities.

---

#### TASK-5.4.1 ✅ _(ad-hoc)_

**Name:** Fix PaceChart light-mode fill and leap-year domain

**Goal:** Two bugs in `PaceChart.tsx`: the area fill is hardcoded to the dark-mode rgba value so it doesn't adapt to light mode; and the X-axis domain hardcodes 365 (wrong in leap years).

**Context:** Discovered during post-implementation frontend review against `docs/design/style.md`. Both are self-contained fixes in a single file.

**Input:** `frontend/src/components/PaceChart.tsx`

**Output:**
- `buildChartData` returns `{ data, daysInYear }` so the caller can use the correct value
- `PaceChart` reads `--accent-dim` via `getComputedStyle` (alongside the already-read `--accent`) and passes it as the `<Area fill>`
- `<XAxis domain>` uses the returned `daysInYear` instead of the literal `365`

**Dependencies:** TASK-5.4

**Complexity:** Small

**Testability:** In light mode, chart area fill visually matches the light-mode accent-dim. In leap years, the X-axis extends to day 366.

---

#### TASK-5.4.2 ✅ _(ad-hoc)_

**Name:** Align dashboard CSS to style spec: section gap and page title size

**Goal:** Two CSS values deviate from `docs/design/style.md`: `.dashboard-page` gap is 24px (spec: 48px) and `.page-title` is 22px (spec: 24px).

**Context:** Discovered during post-implementation frontend review.

**Input:** `frontend/src/index.css`

**Output:**
- `.dashboard-page { gap: 48px }` (was 24px)
- `.page-title { font-size: 24px }` (was 22px)

**Dependencies:** TASK-5.4

**Complexity:** Small

**Testability:** Dashboard cards have noticeably more breathing room between sections. Page title renders at 24px.

---

#### TASK-5.4.3 ✅ _(ad-hoc)_

**Name:** Spinner consistency: rename class and add logout spinner

**Goal:** `.sync-btn__spinner` is used in both the sync and goal-save buttons — the name is misleading. Rename to `.btn__spinner`. The logout button shows `"…"` without a spinner, inconsistent with other loading states.

**Context:** Discovered during post-implementation frontend review.

**Input:** `frontend/src/index.css`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/pages/HomePage.tsx`

**Output:**
- `index.css`: `.sync-btn__spinner` renamed to `.btn__spinner`
- `DashboardPage.tsx`: both `sync-btn__spinner` references updated to `btn__spinner`
- `HomePage.tsx`: logout button renders `<span className="btn__spinner" aria-hidden="true" /> Logging out…` while `loggingOut` is true

**Dependencies:** TASK-5.4

**Complexity:** Small

**Testability:** Clicking "Log out" shows a spinner during the request. Sync and Save buttons show no visual regression.

---

#### TASK-5.4.4 ✅ _(ad-hoc)_

**Name:** Replace raw athlete ID in page subtitle

**Goal:** The page subtitle shows `Athlete #12345678` — a raw internal ID meaningless to users. Replace with the current year and goal context.

**Context:** Discovered during post-implementation frontend review.

**Input:** `frontend/src/pages/DashboardPage.tsx`

**Output:**
- Page subtitle changed from `` Athlete #{athleteId} `` to `` {new Date().getFullYear()} · Running Goal ``
- `athleteId` prop is retained (used by the parent for data-fetching) but no longer displayed

**Dependencies:** TASK-5.4

**Complexity:** Small

**Testability:** Dashboard subtitle reads `2026 · Running Goal` (or the current year).

---

#### TASK-5.4.5 ✅ _(ad-hoc)_

**Name:** CSS micro-polish: unit label color and page fade-in

**Goal:** Two small polish items: the "km" unit label next to the goal input uses `--text-3` (barely visible — `--text-2` is correct here), and the style guide specifies a 200ms page-level fade-in that is not yet implemented anywhere.

**Context:** Discovered during post-implementation frontend review against `docs/design/style.md`.

**Input:** `frontend/src/index.css`

**Output:**
- `.goal-input__unit { color: var(--text-2) }` (was `--text-3`)
- `@keyframes fade-in { from { opacity: 0 } to { opacity: 1 } }` added to global CSS
- `.app-shell` and `.login-center` both receive `animation: fade-in 200ms ease forwards`

**Dependencies:** TASK-5.4

**Complexity:** Small

**Testability:** "km" label is clearly readable in both themes. Authenticated shell and login page both fade in on mount.

---

### EPIC-6 — Club Progress View

---

#### TASK-6.1 ✅

**Name:** Create clubs and club membership database schema

**Goal:** PostgreSQL tables for clubs and club memberships exist.

**Context:** Required before club data can be stored.

**Input:** Users table from TASK-2.1.

**Output:**
- `backend/shared/models.py` — `Club` and `ClubMembership` ORM models added
- `clubs` table: `id` (PK, Strava club ID as bigint), `name` (text), `updated_at`
- `club_memberships` table: `user_id` (FK → users), `club_id` (FK → clubs), `synced_at` (timestamptz); PK on `(user_id, club_id)`
- Alembic migration in `backend/db/migrations/versions/`

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Tables visible in `psql`. Migration applies cleanly.

---

#### TASK-6.2 ✅

Potentially think about whether syncing should immediatly remove all current memberships, so club membership stays accurate after every sync.

**Name:** Fetch and store club memberships during sync

**Goal:** During each sync, fetch the user's Strava clubs and upsert club membership rows.

**Context:** Club views depend on membership data being current. Membership is refreshed on each sync.

**Input:** Strava API client. Sync flow from TASK-3.4.

**Output:**
- `backend/sync/strava_client.py` extended with `fetch_athlete_clubs(access_token: str) -> list[dict]`
- During `POST /sync`: fetch clubs, upsert `clubs` rows, upsert `club_memberships` rows (no deletion of old memberships in v1 — stale memberships visible until next sync)
- Membership rows include `synced_at = now()`

**Dependencies:** TASK-3.4, TASK-6.1

**Complexity:** Small

**Testability:** After sync, `club_memberships` table contains rows matching the user's Strava clubs. Running sync twice produces no duplicates.

---

#### TASK-6.2.1 ✅

**Name:** Set up integration test database infrastructure

**Goal:** Provide pytest fixtures that spin up a real PostgreSQL container via testcontainers and expose a per-test async session with automatic rollback. Replace the current mock-based `db.execute.call_count` assertions in `test_sync_service.py` with proper integration tests that verify actual DB state.

**Context:** The current sync service tests mock `db.execute` and only count how many times it was called, which does not verify that the correct SQL ran or that data landed in the right columns. A real test DB enables assertions like "after `_sync_clubs`, the `club_memberships` table contains exactly these rows." This infrastructure will be used by all future data-access tests.

**Input:** Existing test suite. Docker (already a project dependency).

**Output:**
- `testcontainers[postgresql]` added to dev dependencies in `pyproject.toml`
- `tests/conftest.py` — three session/function-scoped async fixtures: `postgres_container`, `async_engine` (creates all tables once), `db` (yields `AsyncSession`, rolls back after each test)
- `tests/backend/sync/test_sync_service.py` — `test_sync_clubs_*` tests rewritten as integration tests asserting real DB row state; mock-counting tests removed
- All existing tests continue to pass

**Dependencies:** TASK-6.2

**Complexity:** Small

**Testability:** `uv run pytest tests/backend/sync/test_sync_service.py -k "clubs" -v` passes without a running local DB (testcontainers starts one automatically).

---

#### TASK-6.3 ✅

**Name:** Implement `GET /clubs` endpoint

**Goal:** Return the authenticated user's Strava clubs.

**Context:** Required for the club switcher UI.

**Input:** `club_memberships` and `clubs` tables. Auth middleware.

**Output:**
- `backend/clubs/schemas.py` — `ClubResponse(BaseModel)` with `id: int`, `name: str`; endpoint returns `list[ClubResponse]`
- `backend/clubs/router.py` — `GET /clubs` (30/minute) returns `list[ClubResponse]`; requires `get_current_user`
- Returns `[]` if no clubs or no sync has occurred
- Only own memberships returned

**Dependencies:** TASK-6.2, TASK-2.6

**Complexity:** Small

**Testability:** After sync, `GET /clubs` returns correct clubs. Unauthenticated call returns `401`. User B cannot see User A's clubs.

---

#### TASK-6.4 ✅

**Name:** Implement `GET /dashboard/club/{club_id}` endpoint

**Goal:** Return per-member progress for all app-authorized members of a club, visible only to members of that club.

**Context:** Core club feature. Authorization check is critical: only club members can query a club's progress. Implemented in `DashboardService` alongside `get_personal_dashboard` for consistency.

**Input:** `clubs`, `club_memberships`, `activities`, `goals`, `users` tables. Auth middleware.

**Output:**
- `backend/shared/models.py` — `display_name: Mapped[str]` added to `User`
- `backend/db/migrations/versions/0005_add_user_display_name.py` — Alembic migration
- `backend/auth/strava_oauth_service.py` — `_build_display_name` helper; `_upsert_user` now stores `display_name` as "Firstname L."
- `backend/dashboard/schemas.py` — `MemberProgressResponse(BaseModel)` with `strava_athlete_id: int`, `display_name: str`, `distance_to_date_km: float`, `goal_km: float`, `progress_pct: float`; `ClubDashboardResponse` with `club_id: int`, `club_name: str`, `members: list[MemberProgressResponse]`
- `backend/dashboard/router.py` — `GET /dashboard/club/{club_id}` (30/minute) returns `ClubDashboardResponse`; requires `get_current_user`
- `backend/dashboard/dashboard_service.py` — `get_club_dashboard` method
- Validates that the authenticated user is a member of `club_id`; returns `403` otherwise
- Returns progress for all club members who have authorized the app:
  ```json
  {"club_id": 42, "club_name": "Road Runners", "members": [
    {"strava_athlete_id": ..., "display_name": "Alice A.", "distance_to_date_km": ..., "goal_km": ..., "progress_pct": ...}
  ]}
  ```
- Uses each member's own goal for their percentage; members without a goal are omitted
- Filters to current-year activities per member

**Dependencies:** TASK-6.3, TASK-5.3

**Complexity:** Medium

**Testability:** Two users both in same club both authorize app → User A calls `GET /dashboard/club/{id}` → sees both users' progress. User not in club returns `403`. User only in club sees only members with app authorized.

---

#### TASK-6.5 ✅

**Name:** Streamlit club progress view

**Goal:** Render the club switcher and per-member progress bar list in Streamlit.

**Context:** Second major product feature UI.

**Input:** `GET /clubs`. `GET /dashboard/club/{club_id}`.

**Output:**
- `frontend/src/api/client.ts` extended with `getClubs()` and `getClubDashboard(clubId: number)`
- `frontend/src/pages/ClubsPage.tsx` — club select dropdown from `GET /clubs`; per-member progress bar list for selected club; persistent disclaimer: "This club view shows members who have connected this app. It is a progress visualization, not a competition leaderboard."; empty state: "No other members of this club have connected the app yet."; GDPR links visible

**Dependencies:** TASK-6.4, TASK-2.8

**Complexity:** Small

**Testability:** With two authorized club members → club view shows both with correct percentages. Single member sees empty-state message. Non-member club not in dropdown.

---

### EPIC-7 — Privacy and Account Deletion

---

#### TASK-7.1 ✅

**Name:** Create deletion audit log schema

**Goal:** A minimal deletion event log table for recording deletion events without PII.

**Context:** Required by design spec before any deletion logic is implemented.

**Input:** Database setup.

**Output:**
- `backend/shared/models.py` — `DeletionEvent` ORM model added
- `deletion_events` table: `id` (PK), `user_id` (bigint, not FK — preserved after user deletion), `reason` (text: `user_initiated` / `strava_deauth`), `deleted_at` (timestamptz)
- No PII columns
- Alembic migration in `backend/db/migrations/versions/`

**Dependencies:** TASK-1.4

**Complexity:** Small

**Testability:** Migration applies. Row inserted manually verifiable in `psql`.

---

#### TASK-7.2 ✅

**Name:** Implement user data deletion service

**Goal:** A reusable service function that deletes all data for a user and writes a deletion event log entry.

**Context:** Used by both `POST /privacy/delete` and `POST /strava/deauth`. Centralizing deletion prevents inconsistency.

**Input:** All user-related tables. Deletion audit log from TASK-7.1.

**Output:**
- `backend/privacy/deletion_service.py` — `delete_user_data(db, user_id: int, reason: str)`:
  - Deletes: `activities`, `club_memberships`, `oauth_credentials`, `sync_state`, `goals`
  - Deletes: `users` row
  - Inserts: `deletion_events` row with `user_id` (Strava athlete ID), `reason`, `deleted_at`
  - All deletions in a single database transaction
  - Logs completion (no PII)

**Dependencies:** TASK-7.1, TASK-3.1, TASK-6.1, TASK-5.1

**Complexity:** Small

**Testability:** Unit test: seed a user with activities, goals, clubs → call `delete_user_data` → all rows gone → `deletion_events` has one entry → re-running is idempotent (no error on missing rows).

---

#### TASK-7.3 ✅

**Name:** Implement `POST /privacy/export` endpoint

**Goal:** Return all stored data for the authenticated user as a downloadable JSON payload.

**Context:** DSAR self-service requirement.

**Input:** All user-related tables. Auth middleware.

**Output:**
- `backend/privacy/router.py` — `POST /privacy/export` (5/hour) returns a `Response` with `Content-Disposition: attachment; filename="strava-export.json"` (file download, not a JSON schema response); requires `get_current_user`
- Export payload contains: user record (athlete ID, created_at), goal, all activities (all fields except internal PKs), club memberships, sync state
- Tokens are NEVER included in the export

**Dependencies:** TASK-2.6, TASK-3.1, TASK-5.1, TASK-6.1

**Complexity:** Small

**Testability:** Authenticated `POST /privacy/export` returns JSON containing own activities and goal. No tokens in response. Unauthenticated call returns `401`.

---

#### TASK-7.4 ✅

**Name:** Implement `POST /privacy/delete` endpoint

**Goal:** Allow authenticated user to delete their own account and all data.

**Context:** DSAR self-service and GDPR right to erasure.

**Input:** Deletion service from TASK-7.2. Auth middleware.

**Output:**
- `backend/privacy/schemas.py` — `DeleteResponse(BaseModel)` with `deleted: bool`
- `backend/privacy/router.py` — `POST /privacy/delete` (5/hour) calls `delete_user_data`, clears `request.session`, returns `DeleteResponse(deleted=True)`; requires `get_current_user`

**Dependencies:** TASK-7.2, TASK-2.6

**Complexity:** Small

**Testability:** Authenticated user calls `POST /privacy/delete` → `200` returned → all DB rows gone → `deletion_events` has entry → subsequent `GET /session/me` returns `401`.

---

#### TASK-7.5 ✅

**Name:** Implement `POST /strava/deauth` endpoint

**Goal:** Handle Strava's deauthorization webhook: verify Strava signature, erase all user data, invalidate session.

**Context:** Required by Strava's platform terms. Must be implemented before going to production.

**Input:** Deletion service from TASK-7.2. Strava deauth payload and signature scheme.

**Output:**
- `backend/privacy/router.py` — `POST /strava/deauth` (20/minute; no auth required — Strava server call; verified by signature instead)
- Verifies the request using Strava's `client_secret`-based signature (or Strava-specified verification method)
- Looks up user by `strava_athlete_id` from payload
- Calls `delete_user_data(db, user_id, reason="strava_deauth")`
- Attempts to invalidate any active session for that user
- On any failure: logs error with user ID for manual operator resolution, returns `200` (per Strava's requirement)
- Returns `200` on success

**Dependencies:** TASK-7.2

**Complexity:** Small

**Testability:** POST with valid Strava-signed payload → user data deleted → `deletion_events` has `strava_deauth` entry. Invalid signature → `403` returned. Unknown athlete ID → logs warning, returns `200`.

---

#### TASK-7.6 ✅

**Name:** Streamlit privacy page

**Goal:** Provide self-service data export and account deletion UI in Streamlit.

**Context:** Required for user-facing GDPR compliance before real users are onboarded.

**Input:** `POST /privacy/export`. `POST /privacy/delete`. Auth state.

**Output:**
- `frontend/src/pages/PrivacyPage.tsx` — "Download My Data" button calls `POST /privacy/export` and triggers a browser file download; "Delete My Account" button shows a confirmation step ("This will permanently delete all your data. This cannot be undone.") then calls `POST /privacy/delete` and redirects to the login page; GDPR document links visible

**Dependencies:** TASK-7.3, TASK-7.4, TASK-2.8

**Complexity:** Small

**Testability:** Click "Download My Data" → JSON file downloaded containing own activities. Click "Delete My Account" → confirm → redirected to login → all data gone from DB.

---

#### TASK-7.7 ✅

**Name:** Privacy Policy and Terms of Service pages

**Goal:** Publish publicly accessible Privacy Policy and Terms of Service pages as React routes, and wire them into the GDPR footer. Required by Strava's API review process before expanded access can be granted.

**Context:** `GdprFooter` already renders "Privacy Policy" and "Terms of Service" links pointing to `#`. This task replaces those with real routes and writes the full content for both pages. The app has no React Router — routing is done via conditional rendering in `App.tsx`. The same pattern applies here: check `window.location.pathname` before the auth check so both pages are publicly accessible without login. Vite dev server already serves `index.html` for all paths, so no server config change is needed.

**Operator details:** Elias De Coppel · goalvisualizer.support@gmail.com · Governing law: Belgium

**Input:** `frontend/src/App.tsx`, `frontend/src/components/GdprFooter.tsx`

**Output:**

- `frontend/src/pages/PrivacyPolicyPage.tsx` — static page with the following sections:
  1. **Who we are** — operated by Elias De Coppel (goalvisualizer.support@gmail.com), individual developer
  2. **What we collect** — Strava athlete ID; running activities (name, distance, date — only `sport_type = 'Run'`; all other activity types are discarded at ingest and never stored); yearly running goal; Strava club memberships (names and IDs); one session cookie for authentication only
  3. **What we never collect** — OAuth tokens are encrypted at rest (Fernet) and never stored in readable form or logged; heart rate, GPS routes, power, cadence, or any health metrics; analytics or advertising cookies; any data not listed above
  4. **Why we collect it (legal basis)** — you explicitly authorized this app via Strava OAuth; purpose is solely to visualize your running goal progress and club member progress
  5. **How long we keep it** — until you delete your account (immediate erasure); or until you revoke app access in Strava settings (automatic erasure via deauth webhook)
  6. **Your rights** — download all your data via the Export button on the Privacy page; delete all your data permanently via Delete Account; withdraw consent by revoking in Strava connected apps settings
  7. **Security** — tokens encrypted at rest with Fernet; session cookies are HttpOnly, Secure, SameSite=Lax; no user data transmitted to any third party other than described below
  8. **Third parties** — Strava Inc. only (data source and OAuth provider); no advertising networks, analytics providers, or data brokers; we do not sell, rent, or share your data
  9. **Contact** — goalvisualizer.support@gmail.com
  10. **Changes** — "Last updated" date updated on any change; continued use constitutes acceptance
  - Page includes a "← Back to app" link (`window.history.back()`)

- `frontend/src/pages/TermsPage.tsx` — static page with the following sections:
  1. **About this service** — a personal running goal tracker reading authorized Strava data; operated by Elias De Coppel as an individual developer; not affiliated with, endorsed by, or a product of Strava Inc.; "Strava" is a registered trademark of Strava Inc.
  2. **Eligibility** — must have a Strava account; must be old enough to consent to data processing in your country of residence
  3. **What you authorize** — read access to activities and profile via Strava OAuth (scopes: `activity:read_all`, `profile:read_all`); revocable at any time in Strava settings, which triggers automatic data deletion
  4. **Acceptable use** — personal use only; do not attempt to access other users' data; do not circumvent rate limits, reverse-engineer the service, or use it for any unlawful purpose
  5. **No warranty** — provided "as-is" with no guarantee of uptime, accuracy, or fitness for any purpose; progress figures may differ from Strava's own metrics; the service may be discontinued at any time without notice
  6. **Limitation of liability** — developer not liable for any direct, indirect, or consequential damages; as this is a free service, maximum liability is €0
  7. **Termination** — you can delete your account and all data at any time via the Privacy page; we reserve the right to revoke access for ToS violations; we reserve the right to shut down the service permanently at any time, in which case all stored user data will be deleted
  8. **Governing law** — laws of Belgium
  9. **Contact and changes** — goalvisualizer.support@gmail.com; "Last updated" date updated on any change; continued use after changes constitutes acceptance
  - Page includes a "← Back to app" link (`window.history.back()`)

- `frontend/src/App.tsx` — add path checks at the top of the component, before the auth state check:
  ```tsx
  const path = window.location.pathname
  if (path === '/privacy-policy') return <PrivacyPolicyPage />
  if (path === '/terms') return <TermsPage />
  ```

- `frontend/src/components/GdprFooter.tsx` — replace `href="#"` on the Privacy Policy link with `href="/privacy-policy"` and on the Terms of Service link with `href="/terms"`; the "Data Deletion Info" link/button behaviour is unchanged

**Dependencies:** TASK-7.6

**Complexity:** Small

**Testability:** Navigate directly to `/privacy-policy` without being logged in → page renders with all sections. Navigate directly to `/terms` without being logged in → page renders with all sections. Click "Privacy Policy" in the GDPR footer → navigates to `/privacy-policy`. Click "Terms of Service" in the GDPR footer → navigates to `/terms`. Click "← Back to app" → returns to previous page. Both URLs are publicly accessible (no redirect to login).

---

#### TASK-7.8 _(ad-hoc)_

**Name:** User icon dropdown + expose display_name in session

**Goal:** Replace the standalone "Log out" button with a user icon in the top-right nav. Clicking it opens a dropdown showing the user's display name, an "Account" link (navigates to the privacy/data page), and "Log out". Simplify GdprFooter to only the two public legal links. Also expose `display_name` from `/session/me` so the frontend can show the user's name.

**Context:** The `PrivacyPage` was only reachable via "Data Deletion Info" in the footer. The "Log out" button occupied nav space that is better used by a user icon following standard UX convention. `display_name` is already stored on the `User` model and populated at login — it just wasn't included in the session response. The "← Back to app" button on the legal pages was also changed from `window.history.back()` to navigate to `/` directly, to avoid landing on another legal page when the user has navigated between them.

**Input:** `backend/auth/schemas.py`, `backend/auth/router.py`, `tests/backend/auth/test_session_me.py`, `frontend/src/api/client.ts`, `frontend/src/pages/HomePage.tsx`, `frontend/src/components/GdprFooter.tsx`, `frontend/src/index.css`

**Output:**
- `backend/auth/schemas.py` — add `display_name: str` to `SessionMeResponse`
- `backend/auth/router.py` — pass `display_name=current_user.display_name` in the `session_me` response
- `tests/backend/auth/test_session_me.py` — assert `display_name` is present and correct in the session response test
- `frontend/src/api/client.ts` — add `display_name: string` to `SessionUser`
- `frontend/src/pages/HomePage.tsx` — add `'account'` to `Page` type; replace the "Log out" button with a user icon (`UserIcon` SVG) + dropdown (`user-menu`/`user-menu__panel`) containing display name, "Account" button (`setPage('account')`), and "Log out"; click-outside dismissal via `useRef` + `useEffect`; render `<PrivacyPage>` when `page === 'account'`; pass no props to `<GdprFooter>`
- `frontend/src/components/GdprFooter.tsx` — remove `Props` interface and `onPrivacyClick`; render only "Privacy Policy · Terms of Service"
- `frontend/src/index.css` — add `.user-menu`, `.user-menu__panel`, `.user-menu__name`, `.user-menu__item` styles; remove dead `.gdpr-footer button` styles

**Dependencies:** TASK-7.6, TASK-7.7

**Complexity:** Small–Medium

**Testability:** Clicking the user icon opens a dropdown with the user's display name. Clicking "Account" navigates to the privacy/data page with the nav bar visible; dropdown closes. Clicking "Log out" triggers the logout flow. Clicking outside the dropdown closes it. GdprFooter shows only "Privacy Policy · Terms of Service". Legal pages render correctly and "← Back to app" navigates to `/`.

---

### EPIC-8 — Operations & Observability

---

#### TASK-8.1 ✅ _(ad-hoc)_

**Name:** Achievement Badges

**Goal:** Display four milestone achievement badges on the personal dashboard when year-to-date distance crosses 10 / 100 / 365 / 1,000 km. Badge state derives from `distance_to_date_km` — no backend changes required.

**Context:** Pure frontend feature. Shield + running shoe SVG badges with progressive detail per tier. Earned badges render in tier color; unearned in `--text-3` (`#3d4358`). Design spec: `docs/superpowers/specs/2026-06-16-achievement-badges-design.md`.

**Input:** `frontend/src/pages/DashboardPage.tsx`, `frontend/src/index.css`

**Output:**
- `frontend/src/components/BadgeIcon.tsx` — SVG badge component (shield + shoe, 4 tier variants)
- `frontend/src/components/BadgeRow.tsx` — Badge row card with earned-state logic
- `frontend/src/pages/DashboardPage.tsx` — Render `<BadgeRow>` between Stats and Pace chart cards
- `frontend/src/index.css` — Add `.badge-row`, `.badge-item`, `.badge-item__name`, `.badge-item__threshold`

**Dependencies:** TASK-5.x (personal dashboard `distance_to_date_km`)

**Complexity:** Small

**Testability:** Badges card visible on Dashboard, not on Clubs page. Earned badges show tier color; unearned show dark grey. All four tiers render at the correct threshold.

**Refinement (2026-06-17):** Enlarged header badges 40×48 → 60×72 px (150%) and replaced the slow native `title` tooltip with a custom CSS hover/focus tooltip (`.header-badges__tooltip`) that appears instantly below each badge. Keyboard-accessible via `tabIndex` + `:focus-visible`. Replaced the hardcoded unearned color (`#3d4358`, dark-mode only — looked solid in light mode and silver-ish in dark) with a theme-adaptive `--badge-locked` token; `BadgeIcon` now paints via `currentColor`.

---

#### TASK-8.2 ✅

**Name:** Refine application logging (request-id correlation + failure-point logs)

**Goal:** Make production logs traceable to a single request and emit explicit, actionable records at the real failure points. Plain-text output is kept (per-request correlation id, consistent format), isolated so a later switch to JSON is a small change. Add explicit logging for Strava 429 rate limits, OAuth token-refresh failures, and the deauth webhook.

**Context:** Heading to production on Fly.io (~100–1000 users). A full observability stack is overkill; `fly logs` captures stdout. Logging today is an inline `basicConfig` in `main.py` with no correlation id. Design spec: `docs/superpowers/specs/2026-06-18-observability-basics-design.md`.

**Input:** `backend/main.py`, `backend/sync/strava_client.py`, `backend/auth/strava_oauth_service.py`, `backend/privacy/` (router/service), `CLAUDE.md`

**Output:**
- `backend/shared/logging.py` — new: `request_id_var` contextvar, `RequestIdFilter`, `configure_logging()` with format `%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s`
- `backend/shared/request_id.py` — new: `BaseHTTPMiddleware` that reads/generates `X-Request-ID`, sets the contextvar, echoes the response header
- `backend/main.py` — call `configure_logging()`, register the middleware, remove inline `basicConfig`
- `backend/sync/strava_client.py` — `warning` log on Strava 429 (with `Retry-After`) in `fetch_activities` and `fetch_athlete_clubs`
- `backend/auth/strava_oauth_service.py` — `error` log on token-refresh failure (never the token)
- `backend/privacy/` — `info` on deauth webhook receipt, `error` on processing failure
- `CLAUDE.md` — logging convention note (module logger, level guidance, automatic request id, never log tokens)
- `tests/backend/...` — request returns/echoes `X-Request-ID`; `caplog` shows records carry `request_id`; mocked 429 emits warning; mocked refresh failure emits error

**Dependencies:** TASK-7.x (deauth webhook), EPIC-3 (sync client)

**Complexity:** Medium

**Testability:** A response carries an `X-Request-ID` header; a supplied id is echoed unchanged. Log records emitted during a request include a non-default `request_id`. A simulated Strava 429 emits a warning; a simulated token-refresh failure emits an error. No tokens appear in any log. Existing suite still passes.

---

#### TASK-8.3 ✅

**Name:** Document DB statistics queries

**Goal:** Provide a reference doc for reading usage statistics from PostgreSQL — total/recent users, engagement, clubs, content volume — that works locally and against the deployed Fly database, plus a `scripts/stats.sql` curated summary run via documented commands. Existing data only; no schema changes.

**Context:** The operator wants to know "how is the service doing?" without an admin UI. Sessions are signed cookies (no "currently online" count) and there is no `last_seen_at` column (no real WAU/DAU) — the doc documents the available proxies and notes the limitation. Design spec: `docs/superpowers/specs/2026-06-18-observability-basics-design.md`.

**Input:** `docs/ops/webhook-registration.md` (sibling reference for style), `backend/shared/models.py` (column names)

**Output:**
- `docs/ops/db-statistics.md` — new: run instructions for the curated summary (local `docker compose exec`; Fly `fly postgres connect ... < scripts/stats.sql`), interactive connect instructions (local + Fly proxy), read-only role recommendation, `fly logs` cross-reference, grouped query catalogue (users, engagement, clubs, content volume), and a caveat box (no `last_seen_at`, no server-side session store)
- `scripts/stats.sql` — new: curated subset (users, signups last 7 days, users synced, users with a goal, total activities, total distance, clubs)

**Dependencies:** None (reads existing schema)

**Complexity:** Small

**Testability:** Every query in the doc runs without error against a populated local DB and returns the described shape. `scripts/stats.sql` prints the summary locally via `docker compose exec`; documented Fly invocations match Fly's CLI. Documentation/tooling task — no automated tests.

---

Also consider meta tools, how can I as an admin know how many clubs/people are connected? How the service is doing? _(addressed by EPIC-8 — TASK-8.2 / TASK-8.3)_

Also consider changing the email to a dedicated support email

---

#### TASK-8.4 ✅

**Name:** Production Dockerfile (multi-stage)

**Goal:** A single multi-stage `Dockerfile` at the repo root that builds the React frontend and packages it with the FastAPI backend so Fly.io deploys one container serving both the API and the static frontend.

**Context:** Fly.io deploys a single Docker image. The existing `backend/Dockerfile` only runs the Python backend; `frontend/Dockerfile` runs a dev server. This new root Dockerfile has two stages: Node 22 builds `frontend/dist/` with `VITE_API_BASE_URL=""` (relative API calls); Python copies the built files in and runs uvicorn. Local dev (docker-compose) is unchanged — it keeps using the two existing Dockerfiles.

**Input:** `backend/Dockerfile` (reference for the Python stage), `frontend/Dockerfile` (reference for prod build), `pyproject.toml`

**Output:**
- `Dockerfile` (repo root) — two-stage build: Node 22 frontend build, Python 3.12-slim backend runtime with `frontend/dist/` copied in
- `pyproject.toml` — add `aiofiles>=24.0` to `backend` group, `types-aiofiles>=24.0` to `dev` group
- `backend/main.py` — mount `/assets` as `StaticFiles`; catch-all `GET /{full_path:path}` returns `frontend/dist/index.html` (guarded by `if _DIST.is_dir()` so local dev is unaffected)

**Dependencies:** None

**Complexity:** Small

**Testability:** `docker build -t sgv-prod-test .` completes. Running the image with the compose DB: `curl localhost:8001/health` → `{"status":"ok"}`; `curl localhost:8001/` → React app HTML; `curl localhost:8001/any-unknown-path` → same HTML (SPA fallback). `make ci` passes.

---

#### TASK-8.5 ✅

**Name:** Fly.io app configuration (`fly.toml`)

**Goal:** A `fly.toml` at the repo root so `fly deploy` can build and deploy the app without any manual Fly.io dashboard configuration.

**Context:** `fly launch --no-deploy` generates a scaffold; this task documents and commits the customised version with correct health check path (`/health`), machine sizing (256 MB shared CPU), HTTPS enforcement, and the non-secret env vars (`SESSION_COOKIE_SECURE=true`, `FRONTEND_ORIGIN`). The file uses `<app-name>` placeholders — operator replaces with their chosen Fly app name before deploying.

**Input:** Fly.io v2 machines format reference

**Output:**
- `fly.toml` (repo root) — `[build]`, `[env]` (non-secrets only), `[http_service]` on port 8000 with HTTPS forced and health check at `/health`, `[[vm]]` 256 MB shared CPU

**Dependencies:** TASK-8.4

**Complexity:** Small

**Testability:** `fly deploy` succeeds and the app is reachable. `curl https://<app-name>.fly.dev/health` returns `{"status":"ok"}`.

---

### EPIC-9 — Security & Privacy Hardening

---

#### TASK-9.1

**Name:** Mark session cookie `Secure` in production

**Goal:** The session cookie carries the `Secure` attribute in production so it is never sent over plaintext HTTP, matching the claim already made in the privacy policy.

**Context:** `backend/main.py` configures `SessionMiddleware(https_only=False)`, so the auth cookie lacks `Secure`. The published privacy policy states "Session cookies are HttpOnly, Secure, and SameSite=Lax" — so the code currently contradicts a stated safeguard. The cookie *is* the authentication credential; without `Secure`, a browser attaches it to any `http://` request to the domain. Local dev runs over HTTP and still needs `https_only=False`, so the value must be configurable. Audit severity: HIGH.

**Input:** `backend/main.py`, `backend/shared/config.py`, `.env.example`

**Output:**
- `backend/shared/config.py` — add `session_cookie_secure: bool` to `Settings`, defaulting to `True`; read from optional env var `SESSION_COOKIE_SECURE` (parse `"false"`/`"0"` as `False`)
- `backend/main.py` — `SessionMiddleware(..., https_only=settings.session_cookie_secure)`
- `.env.example` — document `SESSION_COOKIE_SECURE` with a comment that it must be `false` only for local HTTP development and `true` (the default) in production

**Dependencies:** TASK-2.5

**Complexity:** Small

**Testability:** With `SESSION_COOKIE_SECURE` unset (default), the `Set-Cookie` header on the OAuth callback redirect includes `Secure`. With `SESSION_COOKIE_SECURE=false`, it does not. Existing auth tests still pass.

---

#### TASK-9.2

**Name:** Reduce forged-deletion risk on the deauth webhook (`subscription_id` filter + documented residual risk)

**Goal:** Reject naive forged `POST /strava/deauth` requests with a cheap `subscription_id` check, and document the residual risk that cannot be fully eliminated.

**Context:** `backend/privacy/router.py` deletes all of a user's data based solely on the `owner_id` in an unauthenticated request body. Strava does **not** sign webhook events — there is no HMAC or per-event secret, only the one-time `hub.challenge` / `verify_token` handshake at subscription time (confirmed against Strava's docs + developer community). A user's `strava_athlete_id` is not secret (it is returned in the club dashboard via `MemberProgressResponse.strava_athlete_id` and visible on Strava), so a fellow club member could POST `{"object_type":"athlete","updates":{"authorized":"false"},"owner_id":<victim>}` to wipe that user's activities, goal, memberships, and tokens. The data is re-syncable from Strava (no theft, fully recoverable on next login), and the realistic attacker is narrow (someone who knows the victim uses this app and their athlete ID), so this is **LOW**, downgraded from the audit's MEDIUM.

The chosen mitigation is a `subscription_id` filter: every genuine Strava event carries the `subscription_id` of our one push subscription (returned as `{"id": ...}` at registration). We reject events whose `subscription_id` doesn't match ours. This is a free speed bump with no external call and no risk to the genuine-deauth path — **not** a real authentication boundary, since `subscription_id` is a guessable incrementing integer. A determined attacker who guesses it is the documented residual risk. (The rejected alternative — verifying the deauth by calling Strava with the stored token before deleting — was dropped because it inverts the safe default: a transient Strava failure during a *genuine* deauth would skip a required erasure, a worse GDPR/platform-compliance outcome than deleting on a forged event.)

The configured subscription ID is **optional**: the value only exists after the webhook is registered in production, so when `STRAVA_WEBHOOK_SUBSCRIPTION_ID` is unset the filter is skipped entirely and the endpoint behaves exactly as it does today (no chicken-and-egg at first boot, no behaviour change for local/dev). The filter activates only once the operator sets the value post-registration.

**Input:** `backend/privacy/schemas.py`, `backend/privacy/router.py`, `backend/shared/config.py`, `.env.example`, `docs/ops/webhook-registration.md`, `docs/design.md`, `tests/backend/privacy/test_deauth_integration.py`, `tests/backend/privacy/test_privacy_router.py`

**Output:**
- `backend/privacy/schemas.py` — add `subscription_id: int | None = None` to `StravaWebhookPayload` (optional, tolerant of payload-shape variation)
- `backend/shared/config.py` — add `strava_webhook_subscription_id: int | None` to `Settings`, read from optional env `STRAVA_WEBHOOK_SUBSCRIPTION_ID` (parse to `int` when present, `None` when unset); **do not** add it to `_REQUIRED_ENV_VARS`
- `backend/privacy/router.py` — in `strava_deauth_webhook`, before any lookup/deletion: only apply the filter when `settings.strava_webhook_subscription_id is not None`; if set and `payload.subscription_id != settings.strava_webhook_subscription_id`, log a `warning` and return `DeauthResponse()` (still `200`, per Strava's webhook contract). When the setting is unset, skip the check entirely. Keep all existing info/error logging and the existing `object_type`/`authorized` guards.
- `.env.example` — add commented-out `# STRAVA_WEBHOOK_SUBSCRIPTION_ID=` with a note that it is the `id` Strava returns when the webhook subscription is registered (see ops doc), is only known after registration, and that leaving it unset disables the filter
- `docs/ops/webhook-registration.md` — after Step 1, add an explicit instruction to copy the returned subscription `id` into `STRAVA_WEBHOOK_SUBSCRIPTION_ID` in the production environment, and note that the deauth endpoint will ignore (200) any event whose `subscription_id` doesn't match; cross-reference Step 2's GET as the way to recover the ID if lost
- `docs/design.md` — short note under the privacy/deauth section recording the residual risk and why the token-verification alternative was rejected

**Dependencies:** TASK-7.5

**Complexity:** Small

**Testability:** Integration tests (mocked, `tests/backend/privacy/`):
- Filter active (`STRAVA_WEBHOOK_SUBSCRIPTION_ID` set), genuine deauth — matching `subscription_id`, `authorized:false`, known athlete → user rows deleted, `deletion_events` has a `strava_deauth` row, returns `200`.
- Filter active, forged deauth — **mismatched** `subscription_id`, known athlete → no rows deleted, warning logged, returns `200`.
- Filter active, payload missing `subscription_id` (`None`) → treated as mismatch: no deletion, warning logged, `200`.
- Filter unset (no `STRAVA_WEBHOOK_SUBSCRIPTION_ID`) — genuine deauth deletes regardless of the payload's `subscription_id` (back-compat with today's behaviour).
- Matching `subscription_id` but `object_type != "athlete"` or `authorized != "false"` → no-op `200` (existing guards still hold).
- Unknown athlete with matching `subscription_id` → warning logged, `200`, no change.
- Existing deauth tests continue to pass with the filter unset; add `subscription_id` to payloads only in the filter-active cases.

---

#### TASK-9.3

**Name:** Trust Fly.io proxy headers for client IP

**Goal:** Rate limiting and request logs key off the real client IP rather than the Fly.io proxy's IP.

**Context:** The limiter uses `get_remote_address` (`request.client.host`), but `backend/Dockerfile` starts uvicorn without `--proxy-headers`. Behind Fly's proxy every request appears to come from one IP, so per-IP limits collapse into a shared global bucket (e.g. `2/minute` on `/sync` shared across all users, locking out legitimate users) and logged IPs are wrong. Audit severity: LOW (primarily a correctness issue, not a vulnerability).

**Input:** `backend/Dockerfile`

**Output:**
- `backend/Dockerfile` — add `--proxy-headers` and `--forwarded-allow-ips="*"` to the uvicorn `CMD` (trusting the Fly proxy to set `X-Forwarded-For`).

**Dependencies:** None

**Complexity:** Small

**Testability:** With `X-Forwarded-For` set on a request, `request.client.host` (and thus the rate-limit key / logged IP) reflects the forwarded client address rather than the immediate peer. Two different forwarded IPs get independent rate-limit buckets.

---

#### TASK-9.4

**Name:** Reconcile deletion audit log with the "permanent erasure" claim

**Goal:** The retained deletion record no longer contradicts the privacy policy's "all your data is permanently erased" statement.

**Context:** `delete_user_data` writes a `DeletionEvent` row containing the user's `strava_athlete_id`, which persists after erasure. Keeping a minimal deletion record is a legitimate interest (proving a deletion was honored), but the athlete ID is a pseudonymous identifier and the wording "all your data" is then inaccurate. Audit severity: LOW. Pick one of the two fixes below.

**Input:** `frontend/src/pages/PrivacyPolicyPage.tsx` and/or `backend/privacy/privacy_service.py`, `backend/shared/models.py`

**Output (choose one):**
- **Option A (policy wording):** `PrivacyPolicyPage.tsx` — note that a minimal, non-content deletion record (a hashed identifier + timestamp + reason) is retained solely to evidence that the deletion occurred.
- **Option B (pseudonymize):** if the athlete ID is only needed for counts/dedup, store a salted hash instead of the raw `strava_athlete_id` in `DeletionEvent`, and keep the policy wording as-is. Requires a model/migration change.

**Dependencies:** TASK-7.4, TASK-7.7

**Complexity:** Small

**Testability:** Option A — privacy policy text accurately describes the retained deletion record. Option B — after deletion, `deletion_events` contains no raw `strava_athlete_id`; the stored value is a non-reversible hash, and deletion/audit counts still work.

---

### EPIC-10 — Production Deployment Guide

---

#### TASK-10.1 ✅

**Name:** Write production deployment guide

**Goal:** A new operator can deploy the app to production and reach a correctly-configured, live instance by following `docs/ops/deployment.md` alone.

**Context:** Local dev is documented in the README and Docker Compose section. Production deployment has different concerns — production env var values (no localhost URLs, `SESSION_COOKIE_SECURE=true`), running Alembic migrations against the live DB, and Strava webhook registration (including copying `STRAVA_WEBHOOK_SUBSCRIPTION_ID`). These steps are currently undocumented or scattered across `.env.example` and the orphaned `docs/ops/webhook-registration.md`. The webhook registration doc is absorbed into the deployment guide as a section rather than remaining a separate file.

**Input:** `README.md`, `.env.example`, `docs/ops/webhook-registration.md`

**Output:**
- `docs/ops/deployment.md` — end-to-end guide covering: production env var reference (with correct non-localhost defaults), running migrations against the live DB, webhook registration (content moved from `docs/ops/webhook-registration.md`), post-deploy verification steps
- `docs/ops/webhook-registration.md` — replaced by a short redirect stub pointing to `docs/ops/deployment.md` (preserves any existing inbound links/references)

**Dependencies:** TASK-9.1, TASK-9.2 (so `SESSION_COOKIE_SECURE` and `STRAVA_WEBHOOK_SUBSCRIPTION_ID` are already documented in `.env.example` before this guide is written)

**Complexity:** Small

**Testability:** A reader unfamiliar with the project can follow the guide from a fresh environment and reach a live, correctly-configured instance without consulting any other source.

---

#### TASK-10.2 ✅

**Name:** README overhaul

**Goal:** The README gives any visitor — including the author returning after time away — an immediate understanding of what the app is, what it looks like, and where to find everything.

**Context:** The current README jumps straight into prerequisites with no description of the app, no feature list, and no screenshots. The app may go offline after publication, so screenshots baked into the README preserve what it looked like. Node.js version requirement is also wrong (says 18+; requires 22). The README should serve as the single entry point that links to all other docs.

**Input:** `README.md`, `docs/` folder, screenshots saved to `docs/images/` by the operator before going offline

**Output:**
- `docs/images/` — screenshot files provided by operator: `dashboard.png` (personal dashboard with chart, badges, progress bar), `clubs.png` (club progress chart + member bars), optionally `login.png`
- `README.md` rewritten with:
  - **Hero section** — one-line description of the app + dashboard screenshot
  - **Features** — bullet list: personal yearly running goal dashboard, pace chart, achievement badges, club member progress view, Strava OAuth
  - **Tech stack** — FastAPI · React + Vite (TypeScript) · PostgreSQL · Fly.io
  - **Prerequisites** — Node.js requirement corrected to 22; existing Windows instructions kept
  - **Local Development** — existing quickstart cleaned up, unchanged in substance
  - **Documentation** — index linking: `docs/ops/deployment.md`, `docs/ops/db-statistics.md`, `docs/design.md`, `docs/design/style.md`, `docs/workflow.md`, `docs/learnings.md`, `docs/epics/backlog.md`
  - Second screenshot (clubs view) placed near the Features section

**Dependencies:** TASK-10.1 (so the deployment guide link is live before the README points to it); screenshots from operator

**Complexity:** Small

**Testability:** A visitor to the GitHub repo page understands what the app does without reading any code. All doc links resolve. Screenshots render in the GitHub markdown preview.
