# Strava Goal Visualizer — MVP Backlog

_Generated: May 2, 2026_

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
- Activity upsert into PostgreSQL (by Strava activity ID) — all activity types are stored as received from Strava
- Only activities with `sport_type = 'Run'` are used in any business logic or computation; non-running activities are stored but never included in metrics
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
- `GET /clubs/{club_id}/progress` endpoint (returns progress for app-authorized members of that club who are also members)
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
- `backend/crypto.py` with `encrypt(plaintext: str) -> str` and `decrypt(ciphertext: str) -> str`
- Uses `cryptography` library (Fernet symmetric encryption)
- Raises a clear error on startup if `TOKEN_ENCRYPTION_KEY` is missing or invalid
- Tokens are never logged in this module

**Dependencies:** TASK-1.1

**Complexity:** Small

**Testability:** Unit test: `decrypt(encrypt(token)) == token`. Missing key raises on import. Encrypted value is not the plaintext.

---

#### TASK-2.3

**Name:** Implement OAuth state token generation and validation

**Goal:** Generate a signed, server-side state token with a 10-minute TTL and validate it on callback.

**Context:** CSRF protection for the OAuth flow. State tokens must be stored server-side and single-use.

**Input:** `oauth_state_tokens` table from TASK-2.1.

**Output:**
- `backend/oauth_state.py` with:
  - `create_state_token(db) -> str`: inserts a new token with `expires_at = now() + 10min`, returns the token string
  - `validate_and_consume_state_token(db, token: str) -> bool`: checks existence and TTL, deletes the token on success, returns `False` on mismatch or expiry
- Token is a cryptographically random URL-safe string (32+ bytes)

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Unit tests: valid token returns `True` and is deleted. Expired token returns `False`. Unknown token returns `False`. Replay of consumed token returns `False`.

---

#### TASK-2.4

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

#### TASK-2.5

**Name:** Implement `GET /oauth/callback` endpoint

**Goal:** Exchange the OAuth code for tokens, store encrypted tokens, create/update the user record, and issue a session cookie.

**Context:** Completes the OAuth flow. After this endpoint, the user is authenticated and has a session.

**Input:** `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` env vars. State token module. Encryption utility. Users + credentials tables.

**Output:**
- Validates `state` parameter using `validate_and_consume_state_token`
- Exchanges `code` with Strava token endpoint
- Checks that both `activity:read_all` and `profile:read_all` scopes are present in the token response; rejects with re-consent redirect if either is missing
- Upserts user record by `strava_athlete_id`
- Stores encrypted tokens in `oauth_credentials`
- Issues a secure session cookie (`HttpOnly`, `Secure`, `SameSite=Lax`) containing the user ID
- Session cookie is rotated (new value) on every successful login
- Redirects to Streamlit frontend on success
- Failure modes: state mismatch (log as potential CSRF), state expired, Strava error response, token exchange failure — each returns a clear error redirect

**Dependencies:** TASK-2.3, TASK-2.2, TASK-2.1, TASK-2.4

**Complexity:** Medium

**Testability:** End-to-end: complete Strava OAuth flow in browser → redirected to Streamlit → session cookie present in browser devtools → `GET /session/me` returns user profile.

---

#### TASK-2.6

**Name:** Implement session middleware and `GET /session/me`

**Goal:** Read the session cookie on every request, resolve the authenticated user, and expose a `/session/me` endpoint.

**Context:** All authenticated endpoints depend on this. Must be in place before any protected routes are built.

**Input:** Session cookie issued in TASK-2.5. Users table.

**Output:**
- FastAPI dependency `get_current_user(request) -> User` that reads session cookie, looks up user, raises `401` if missing/invalid
- `GET /session/me` returns `{"strava_athlete_id": ..., "created_at": ...}` for the authenticated user
- No PII beyond athlete ID and timestamps returned

**Dependencies:** TASK-2.5

**Complexity:** Small

**Testability:** Authenticated request to `/session/me` returns user data. Request without cookie returns `401`. Request with tampered cookie returns `401`.

---

#### TASK-2.7

**Name:** Implement `POST /session/logout` and `POST /oauth/revoke`

**Goal:** Allow users to log out (clear session) and optionally revoke Strava tokens.

**Context:** Logout is required before the login flow can be considered complete. Revoke is needed for clean Strava token lifecycle.

**Input:** Session middleware from TASK-2.6. OAuth credentials table.

**Output:**
- `POST /session/logout`: clears the session cookie, returns `200`
- `POST /oauth/revoke`: calls Strava revoke endpoint with the user's access token, deletes the `oauth_credentials` row, clears the session cookie
- Both require authentication via `get_current_user`
- Tokens are never logged

**Dependencies:** TASK-2.6

**Complexity:** Small

**Testability:** After logout, `GET /session/me` returns `401`. After revoke, tokens are gone from DB. Calling logout twice is idempotent (second call returns `200`).

---

#### TASK-2.8

**Name:** Streamlit login page and session state

**Goal:** Streamlit displays a login page for unauthenticated users and a logged-in state for authenticated users, using the session cookie set by the backend.

**Context:** Without a Streamlit login flow, the OAuth backend cannot be tested by a real user through the UI.

**Input:** FastAPI OAuth endpoints from TASK-2.4 and TASK-2.5. Session endpoint from TASK-2.6.

**Output:**
- Streamlit calls `GET /session/me` on every page load to determine auth state
- Unauthenticated: shows "Connect with Strava" button that POSTs to `/oauth/authorize` and redirects the browser to the returned URL
- Authenticated: shows athlete ID, "Logout" button that POSTs to `/session/logout`, page reloads to unauthenticated state
- Session cookie is forwarded on all Streamlit → FastAPI calls (same-site browser context)
- GDPR document links visible on all pages (even login page)

**Dependencies:** TASK-2.6, TASK-2.7

**Complexity:** Small

**Testability:** Full browser flow: click "Connect with Strava" → complete OAuth → redirected back → Streamlit shows authenticated state with athlete ID → click Logout → returns to login page.

---

### EPIC-3 — Minimal Activity Sync and Raw Data Display

---

#### TASK-3.1

**Name:** Create activities and sync state database schema

**Goal:** PostgreSQL tables for activities and per-user sync state exist with correct constraints.

**Context:** Required before any sync logic can persist data.

**Input:** SQLAlchemy setup from TASK-1.4. Users table from TASK-2.1.

**Output:**
- `activities` table: `id` (PK), `user_id` (FK → users), `strava_activity_id` (bigint, unique per user), `name` (text), `sport_type` (text), `distance_meters` (numeric), `moving_time_seconds` (int), `start_date` (timestamptz), `created_at`, `updated_at`
- Unique constraint on `(user_id, strava_activity_id)`
- `sync_state` table: `user_id` (PK, FK → users), `last_sync_completed_at` (timestamptz, nullable)
- Alembic migration file

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Tables visible in `psql`. Backend starts without migration errors.

---

#### TASK-3.2

**Name:** Implement Strava API client (activity fetch)

**Goal:** A thin HTTP client that fetches activities for an authenticated user from the Strava API, handling pagination.

**Context:** Core I/O primitive for the sync engine. Used by all sync tasks. No retry logic.

**Input:** Strava access token (decrypted). `STRAVA_CLIENT_ID` env var.

**Output:**
- `backend/strava_client.py` with `fetch_activities(access_token: str, page: int = 1) -> list[dict]`
- Fetches `GET https://www.strava.com/api/v3/athlete/activities` with bearer token
- Supports pagination via `page` and `per_page=200`
- Returns raw activity dicts (no transformation)
- Logs request count (not token)
- Raises typed exceptions for HTTP 401 and other HTTP errors

**Dependencies:** TASK-2.2

**Complexity:** Small

**Testability:** Integration test against Strava sandbox or real token: `fetch_activities(token)` returns a list of dicts. HTTP 401 raises the correct exception type.

---

#### TASK-3.3

**Name:** Implement token refresh utility

**Goal:** Silently refresh an expired Strava access token using the stored refresh token.

**Context:** Access tokens expire in 6 hours. All sync calls must ensure the token is valid before use.

**Input:** Encryption utility from TASK-2.2. `oauth_credentials` table. Strava token refresh endpoint.

**Output:**
- `backend/token_refresh.py` with `ensure_fresh_token(db, user_id: int) -> str`:
  - Returns decrypted access token if not expired
  - If expired, calls Strava refresh endpoint, updates `oauth_credentials` with new encrypted tokens, returns new access token
  - If refresh fails (401 from Strava), raises `TokenRefreshError` (caller is responsible for session invalidation)
- Tokens are never logged

**Dependencies:** TASK-2.2, TASK-2.1

**Complexity:** Small

**Testability:** Unit test with mocked Strava: fresh token returned without refresh call. Expired token triggers refresh and DB update. Refresh failure raises `TokenRefreshError`.

---

#### TASK-3.4

**Name:** Implement `POST /sync` endpoint

**Goal:** Trigger a full current-year activity sync for the authenticated user, with cooldown enforcement.

**Context:** Core sync endpoint. Fetches all current-year activities, upserts them, and records completion timestamp. Single synchronous operation with no state machine.

**Input:** Strava client from TASK-3.2. Token refresh from TASK-3.3. Activities + sync state tables from TASK-3.1. Auth middleware from TASK-2.6.

**Output:**
- `POST /sync`: validates ownership (own athlete ID only)
- Checks `last_sync_completed_at`; if within the last 10 minutes, returns `429 Too Many Requests` with `Retry-After: <seconds_until_eligible>` header
- Fetches all pages of current-year activities from Strava
- Upserts into `activities` table by `(user_id, strava_activity_id)` — all activity types stored as received
- Business logic downstream must filter `sport_type = 'Run'`; the sync endpoint itself does not filter before storage
- On success: sets `last_sync_completed_at = now()`
- On failure: surfaces error directly; `last_sync_completed_at` is not updated
- Requires authentication; runs synchronously in-process

**Dependencies:** TASK-3.2, TASK-3.3, TASK-3.1, TASK-2.6

**Complexity:** Medium

**Testability:** Authenticated `POST /sync` returns 200 and `last_sync_completed_at` is set in DB. Activities rows present matching Strava data. Running sync twice in quick succession → second call returns `429` with `Retry-After` header. Running sync twice with mocked time gap → both succeed with no duplicate rows.

---

#### TASK-3.5

**Name:** Streamlit sync trigger and raw activity list

**Goal:** Streamlit page allows the authenticated user to trigger a sync and see a raw table of their activities.

**Context:** First moment the full vertical slice (Strava → backend → frontend) is visible to a user. Proves the entire pipeline works.

**Input:** Sync endpoints from TASK-3.4. Auth state from TASK-2.8.

**Output:**
- Authenticated Streamlit page: "Sync Activities" button that calls `POST /sync`
- After sync: raw table of activities (name, date, distance, moving time, sport type) — all synced activity types shown for transparency
- Last sync timestamp shown prominently
- Error state shown if sync fails (including "Sync unavailable — try again in X minutes" on 429)

**Dependencies:** TASK-3.4, TASK-2.8

**Complexity:** Small

**Testability:** Click "Sync Activities" → table populates with real Strava activities → last sync timestamp updates. Correct data matches Strava app. Clicking sync again within 10 minutes shows cooldown message.

---



---

### EPIC-5 — Personal Goal Dashboard

---

#### TASK-5.1

**Name:** Create goals database schema

**Goal:** PostgreSQL table for user goals exists with correct constraints and default value.

**Context:** Required before goal endpoints can persist data.

**Input:** Users table from TASK-2.1.

**Output:**
- `goals` table: `user_id` (PK, FK → users), `yearly_distance_km` (numeric, not null, default 365, check > 0 and <= 100000), `updated_at`
- Row auto-created on user creation (default 365 km)
- Alembic migration

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** New user has a goal row with `yearly_distance_km = 365` after OAuth login. `psql` confirms constraint enforcement.

---

#### TASK-5.2

**Name:** Implement `GET /goals` and `PUT /goals` endpoints

**Goal:** Authenticated user can read and update their own yearly goal.

**Context:** Required for goal-based progress computation in the dashboard.

**Input:** Goals table from TASK-5.1. Auth middleware from TASK-2.6.

**Output:**
- `GET /goals` returns `{"yearly_distance_km": <value>}` for the authenticated user
- `PUT /goals` body: `{"yearly_distance_km": <value>}`, validates range (1–100,000), upserts, returns updated value
- Both return `403` if user attempts to set another user's goal (enforced by `get_current_user`)

**Dependencies:** TASK-5.1, TASK-2.6

**Complexity:** Small

**Testability:** `GET /goals` returns default 365 for new user. `PUT /goals {"yearly_distance_km": 500}` → `GET /goals` returns 500. Values outside range return `422`.

---

#### TASK-5.3

**Name:** Implement personal progress computation

**Goal:** Backend computes current-year running distance and progress percentage against the user's goal.

**Context:** Core computation that powers the personal dashboard view.

**Input:** Activities table. Goals table. Auth middleware.

**Output:**
- New endpoint `GET /dashboard/personal` returning:
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
- **Filter by running activities only:** queries must include `WHERE sport_type = 'Run'` (or equivalent ORM condition); non-running activities must not contribute to any of the above values
- Filters activities by `user_id`, `sport_type = 'Run'`, `start_date` in current calendar year
- `on_pace`: `distance_to_date_km >= expected_km_by_today` (linear pace model)
- Only own data returned (enforced by `get_current_user`)

**Dependencies:** TASK-5.2, TASK-3.4

**Complexity:** Small

**Testability:** Seed known activities → call `GET /dashboard/personal` → verify computed values match manual calculation. Ensure another user's activities are not included.

---

#### TASK-5.4

**Name:** Streamlit personal goal dashboard page

**Goal:** Render goal progress chart, key stats, and goal edit control in Streamlit.

**Context:** Core product UI. First moment the app looks like an actual product.

**Input:** `GET /dashboard/personal`. `PUT /goals`. Sync status from TASK-3.5.

**Output:**
- Progress bar: distance to date vs. goal
- Pace line chart: cumulative distance over year vs. linear goal pace
- Key stats: total km, % complete, on-pace indicator
- All displayed metrics are based on running activities only (`sport_type = 'Run'`); non-running activities are never shown in stats or charts
- Goal edit: number input + save button, immediate page refresh on save
- Last sync timestamp shown
- Empty state: "No running activities found — sync your data to get started"
- GDPR links visible on page

**Dependencies:** TASK-5.3, TASK-3.5

**Complexity:** Medium

**Testability:** With synced data → dashboard shows correct distance and %. Update goal → progress % changes. Empty state shown for new user with no synced activities.

---

### EPIC-6 — Club Progress View

---

#### TASK-6.1

**Name:** Create clubs and club membership database schema

**Goal:** PostgreSQL tables for clubs and club memberships exist.

**Context:** Required before club data can be stored.

**Input:** Users table from TASK-2.1.

**Output:**
- `clubs` table: `id` (PK, Strava club ID as bigint), `name` (text), `updated_at`
- `club_memberships` table: `user_id` (FK → users), `club_id` (FK → clubs), `synced_at` (timestamptz); PK on `(user_id, club_id)`
- Alembic migration

**Dependencies:** TASK-2.1

**Complexity:** Small

**Testability:** Tables visible in `psql`. Migration applies cleanly.

---

#### TASK-6.2

**Name:** Fetch and store club memberships during sync

**Goal:** During each sync, fetch the user's Strava clubs and upsert club membership rows.

**Context:** Club views depend on membership data being current. Membership is refreshed on each sync.

**Input:** Strava API client. Sync flow from TASK-3.4.

**Output:**
- `strava_client.py` extended with `fetch_athlete_clubs(access_token: str) -> list[dict]`
- During `POST /sync`: fetch clubs, upsert `clubs` rows, upsert `club_memberships` rows (no deletion of old memberships in v1 — stale memberships visible until next sync)
- Membership rows include `synced_at = now()`

**Dependencies:** TASK-3.4, TASK-6.1

**Complexity:** Small

**Testability:** After sync, `club_memberships` table contains rows matching the user's Strava clubs. Running sync twice produces no duplicates.

---

#### TASK-6.3

**Name:** Implement `GET /clubs` endpoint

**Goal:** Return the authenticated user's Strava clubs.

**Context:** Required for the club switcher UI.

**Input:** `club_memberships` and `clubs` tables. Auth middleware.

**Output:**
- `GET /clubs` returns `[{"id": ..., "name": "..."}]` for clubs the authenticated user is a member of
- Returns `[]` if no clubs or no sync has occurred
- Only own memberships returned

**Dependencies:** TASK-6.2, TASK-2.6

**Complexity:** Small

**Testability:** After sync, `GET /clubs` returns correct clubs. Unauthenticated call returns `401`. User B cannot see User A's clubs.

---

#### TASK-6.4

**Name:** Implement `GET /clubs/{club_id}/progress` endpoint

**Goal:** Return per-member progress for all app-authorized members of a club, visible only to members of that club.

**Context:** Core club feature. Authorization check is critical: only club members can query a club's progress.

**Input:** `clubs`, `club_memberships`, `activities`, `goals` tables. Auth middleware.

**Output:**
- Validates that the authenticated user is a member of `club_id`; returns `403` otherwise
- Returns list of members who are app-authorized AND members of that club:
  ```json
  [
    {"strava_athlete_id": ..., "distance_to_date_km": ..., "goal_km": ..., "progress_pct": ...}
  ]
  ```
- Uses each member's own goal for their percentage
- **Filter by running activities only:** per-member distance is computed with `WHERE sport_type = 'Run'` (or equivalent ORM condition); non-running activities must not contribute to any member's distance or progress percentage
- Filters to current-year running activities (`sport_type = 'Run'`) per member
- Does NOT expose other users' tokens, raw activities, or PII beyond the above fields

**Dependencies:** TASK-6.3, TASK-5.3

**Complexity:** Medium

**Testability:** Two users both in same club both authorize app → User A calls `GET /clubs/{id}/progress` → sees both users' progress. User not in club returns `403`. User only in club sees only members with app authorized.

---

#### TASK-6.5

**Name:** Streamlit club progress view

**Goal:** Render the club switcher and per-member progress bar list in Streamlit.

**Context:** Second major product feature UI.

**Input:** `GET /clubs`. `GET /clubs/{id}/progress`.

**Output:**
- Club switcher: selectbox populated from `GET /clubs`
- Per-member progress bar list for selected club
- Persistent disclaimer: "This club view shows members who have connected this app. It is a progress visualization, not a competition leaderboard."
- Empty state: "No other members of this club have connected the app yet."
- GDPR links visible

**Dependencies:** TASK-6.4, TASK-2.8

**Complexity:** Small

**Testability:** With two authorized club members → club view shows both with correct percentages. Single member sees empty-state message. Non-member club not in dropdown.

---

### EPIC-7 — Privacy and Account Deletion

---

#### TASK-7.1

**Name:** Create deletion audit log schema

**Goal:** A minimal deletion event log table for recording deletion events without PII.

**Context:** Required by design spec before any deletion logic is implemented.

**Input:** Database setup.

**Output:**
- `deletion_events` table: `id` (PK), `user_id` (bigint, not FK — preserved after user deletion), `reason` (text: `user_initiated` / `strava_deauth`), `deleted_at` (timestamptz)
- No PII columns
- Alembic migration

**Dependencies:** TASK-1.4

**Complexity:** Small

**Testability:** Migration applies. Row inserted manually verifiable in `psql`.

---

#### TASK-7.2

**Name:** Implement user data deletion service

**Goal:** A reusable service function that deletes all data for a user and writes a deletion event log entry.

**Context:** Used by both `POST /privacy/delete` and `POST /strava/deauth`. Centralizing deletion prevents inconsistency.

**Input:** All user-related tables. Deletion audit log from TASK-7.1.

**Output:**
- `backend/deletion_service.py` with `delete_user_data(db, user_id: int, reason: str)`:
  - Deletes: `activities`, `club_memberships`, `oauth_credentials`, `sync_state`, `goals`
  - Deletes: `users` row
  - Inserts: `deletion_events` row with `user_id` (Strava athlete ID), `reason`, `deleted_at`
  - All deletions in a single database transaction
  - Logs completion (no PII)

**Dependencies:** TASK-7.1, TASK-3.1, TASK-6.1, TASK-5.1

**Complexity:** Small

**Testability:** Unit test: seed a user with activities, goals, clubs → call `delete_user_data` → all rows gone → `deletion_events` has one entry → re-running is idempotent (no error on missing rows).

---

#### TASK-7.3

**Name:** Implement `POST /privacy/export` endpoint

**Goal:** Return all stored data for the authenticated user as a downloadable JSON payload.

**Context:** DSAR self-service requirement.

**Input:** All user-related tables. Auth middleware.

**Output:**
- `POST /privacy/export` returns a JSON response containing:
  - User record (athlete ID, created_at)
  - Goal
  - All activities (all fields except internal PKs)
  - Club memberships
  - Sync state
- Response includes `Content-Disposition: attachment; filename="strava-export.json"`
- Tokens are NEVER included in the export
- Per-IP rate limiting applied

**Dependencies:** TASK-2.6, TASK-3.1, TASK-5.1, TASK-6.1

**Complexity:** Small

**Testability:** Authenticated `POST /privacy/export` returns JSON containing own activities and goal. No tokens in response. Unauthenticated call returns `401`.

---

#### TASK-7.4

**Name:** Implement `POST /privacy/delete` endpoint

**Goal:** Allow authenticated user to delete their own account and all data.

**Context:** DSAR self-service and GDPR right to erasure.

**Input:** Deletion service from TASK-7.2. Auth middleware.

**Output:**
- `POST /privacy/delete` calls `delete_user_data(db, current_user.id, reason="user_initiated")`
- Immediately invalidates the session (clears session cookie in response)
- Returns `200 {"deleted": true}`
- Per-IP rate limiting applied

**Dependencies:** TASK-7.2, TASK-2.6

**Complexity:** Small

**Testability:** Authenticated user calls `POST /privacy/delete` → `200` returned → all DB rows gone → `deletion_events` has entry → subsequent `GET /session/me` returns `401`.

---

#### TASK-7.5

**Name:** Implement `POST /strava/deauth` endpoint

**Goal:** Handle Strava's deauthorization webhook: verify Strava signature, erase all user data, invalidate session.

**Context:** Required by Strava's platform terms. Must be implemented before going to production.

**Input:** Deletion service from TASK-7.2. Strava deauth payload and signature scheme.

**Output:**
- `POST /strava/deauth` receives Strava's deauth payload
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

#### TASK-7.6

**Name:** Streamlit privacy page

**Goal:** Provide self-service data export and account deletion UI in Streamlit.

**Context:** Required for user-facing GDPR compliance before real users are onboarded.

**Input:** `POST /privacy/export`. `POST /privacy/delete`. Auth state.

**Output:**
- Privacy page accessible from all pages
- "Download My Data" button → calls `POST /privacy/export` → triggers browser file download
- "Delete My Account" button → confirmation dialog ("This will permanently delete all your data. This cannot be undone.") → on confirm calls `POST /privacy/delete` → redirects to login page
- GDPR document links visible

**Dependencies:** TASK-7.3, TASK-7.4, TASK-2.8

**Complexity:** Small

**Testability:** Click "Download My Data" → JSON file downloaded containing own activities. Click "Delete My Account" → confirm → redirected to login → all data gone from DB.

---
