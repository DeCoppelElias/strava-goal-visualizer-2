# Operations & Observability Basics — Design Spec

_Date: 2026-06-18_
_Status: Approved (pending spec review)_
_Epic: EPIC-8 — Operations & Observability_

## Motivation

The app is heading to production on Fly.io for an expected user base of ~100–1000
people. At that scale a full observability stack (OpenTelemetry, Prometheus,
Grafana, hosted error tracking) is overkill and a maintenance burden. What we
actually need are two cheap, high-value capabilities:

1. **See what is going wrong in production** — traceable logs with visibility at
   the failure points that realistically break (Strava rate limits, OAuth token
   refresh, deauthorization).
2. **See how the service is doing** — a documented, repeatable way to read usage
   statistics straight from PostgreSQL.

This spec covers two independent tasks. They share the "operations basics" theme
but ship as **two separate commits**.

## Scope

- **TASK-8.2** — Refine application logging (code).
- **TASK-8.3** — Document DB statistics queries (documentation + a `make stats`
  helper).

## Non-Goals

- No JSON / structured logging yet. Plain text stays; the design isolates the
  format so a later switch to JSON is a small change.
- No log shipping / centralized aggregation. We rely on `fly logs`.
- No error-tracking service (e.g. Sentry).
- No schema changes. In particular, **no `last_seen_at` column** — true
  active-user (WAU/DAU) metrics are explicitly deferred to a future task. Stats
  are limited to data already in the database.
- No admin UI or admin endpoint.

---

## TASK-8.2 — Refine application logging

### Goal

Every log line is traceable to a single request, the format is consistent across
all modules, and the real production failure points emit explicit, actionable log
records. Plain-text output, swappable to JSON later.

### Design

**1. Logging setup module — `backend/shared/logging.py`**

A new module owns logging configuration, replacing the inline `basicConfig` in
`main.py`.

- A module-level `ContextVar` holds the current request id:
  ```python
  request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
  ```
- A `logging.Filter` subclass injects that value onto every `LogRecord` so the
  format string can reference it:
  ```python
  class RequestIdFilter(logging.Filter):
      def filter(self, record: logging.LogRecord) -> bool:
          record.request_id = request_id_var.get()
          return True
  ```
- `configure_logging()` calls `logging.basicConfig(...)` with the new format and
  attaches `RequestIdFilter` to the root handler(s):
  ```
  %(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s
  ```
- Output goes to stdout/stderr (12-factor); Fly captures it for `fly logs`.

**2. Request-ID middleware — `backend/shared/request_id.py`**

A Starlette `BaseHTTPMiddleware` that, per request:

- Reads an incoming `X-Request-ID` header if present, otherwise generates
  `uuid4().hex`.
- Sets `request_id_var` (keeping the reset token), runs the request, and resets
  the contextvar in a `finally` block.
- Echoes the id back as the `X-Request-ID` response header.

Registered in `main.py` via `app.add_middleware(...)`. Because the contextvar is
set for the duration of the request, **every** log record emitted by any module
during that request automatically carries the same id — that is the correlation
mechanism.

**3. Failure-point logging**

Add explicit records at the three sites that actually break in production. Tokens
are never included in any log (existing project rule).

- **Strava rate limits — `backend/sync/strava_client.py`.** Currently a 429 falls
  through `response.raise_for_status()` and becomes a generic `StravaAPIError`
  with no distinct signal. Add, in both `fetch_activities` and
  `fetch_athlete_clubs`, before raising:
  ```python
  if response.status_code == 429:
      logger.warning(
          "Strava rate limit hit (429); retry-after=%s",
          response.headers.get("Retry-After", "?"),
      )
  ```
  These functions only receive an `access_token`, not a user id, so correlation
  to a user relies on the request id (the calling sync service has the user id in
  its own log lines). The existing `StravaAPIError` flow is unchanged.

- **OAuth token refresh — `backend/auth/strava_oauth_service.py`.** On a token
  refresh failure, log an `error` (status / reason, never the token or refresh
  token) before the existing exception propagates.

- **Deauthorization webhook — `backend/privacy/`.** Log webhook receipt at
  `info` and any processing failure at `error`. (TASK-7 already added some deauth
  error logging; this aligns it with the new convention and ensures receipt is
  logged.)

**4. Convention note — `CLAUDE.md`**

A short subsection under logging guidance:
- Use a module-level `logger = logging.getLogger(__name__)`.
- Level guidance: `info` for normal lifecycle, `warning` for recoverable/expected
  external failures (e.g. 429), `error` for unexpected failures.
- The request id is injected automatically — do not pass it manually.
- Never log tokens or secrets.

### Files affected

- `backend/shared/logging.py` — new: contextvar, filter, `configure_logging()`.
- `backend/shared/request_id.py` — new: request-id middleware.
- `backend/main.py` — call `configure_logging()`; register the middleware; remove
  the inline `basicConfig`.
- `backend/sync/strava_client.py` — 429 warning logs.
- `backend/auth/strava_oauth_service.py` — token-refresh error log.
- `backend/privacy/` (router/service) — webhook receipt + failure logs.
- `CLAUDE.md` — logging convention note.
- `tests/backend/...` — tests below.

### Testing

- **Integration (TestClient):** a request returns an `X-Request-ID` response
  header; a provided `X-Request-ID` is echoed back unchanged.
- **`caplog` assertions:** within a request, emitted records carry a non-default
  `request_id`. A simulated Strava 429 (mocked httpx response) emits the expected
  `warning`. A simulated token-refresh failure emits the expected `error`.
- Existing test suite continues to pass (format change must not break assertions
  that match on message text).

---

## TASK-8.3 — Document DB statistics queries

### Goal

A reference document the operator can open to read usage statistics from
PostgreSQL, working both locally and against the deployed Fly database, plus a
`make stats` shortcut for the common subset.

### Location

`docs/ops/db-statistics.md` (alongside the existing `docs/ops/webhook-registration.md`).

### Contents

**1. How to connect**

- **Local (docker compose):**
  ```bash
  docker compose exec db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
  ```
- **Production (Fly.io) — quick ad-hoc session:**
  ```bash
  fly postgres connect -a <db-app>
  ```
- **Production (Fly.io) — run the curated stats file directly (no tunnel):**
  ```bash
  fly postgres connect -a <db-app> < scripts/stats.sql
  ```
- **Production (Fly.io) — tunnel for a GUI client or `make stats`:**
  ```bash
  fly proxy 5432 -a <db-app>          # leaves a tunnel open on localhost:5432
  # then point DATABASE_URL / your client at localhost:5432
  ```
- **Read-only recommendation:** create and use a read-only PostgreSQL role for
  running statistics so an accidental query cannot mutate data. Include the
  `CREATE ROLE ... LOGIN; GRANT CONNECT/USAGE/SELECT` snippet.
- **Cross-reference:** note that `fly logs` shows the live plain-text log stream
  (with request ids) for correlating anomalies seen in the stats.

**2. Query catalogue** (grouped; all against existing columns)

_Users_
```sql
-- Total registered users
SELECT count(*) FROM users;

-- Signups per week
SELECT date_trunc('week', created_at) AS week, count(*)
FROM users GROUP BY 1 ORDER BY 1 DESC;

-- Most recent signups
SELECT id, display_name, created_at
FROM users ORDER BY created_at DESC LIMIT 20;
```

_Engagement_
```sql
-- Users who have synced at least one activity
SELECT count(DISTINCT user_id) FROM activities;

-- Users with a yearly goal set
SELECT count(*) FROM goals;

-- Activities per user (distribution)
SELECT u.id, u.display_name, count(a.id) AS activities
FROM users u LEFT JOIN activities a ON a.user_id = u.id
GROUP BY u.id, u.display_name ORDER BY activities DESC;
```

_Clubs_
```sql
-- Clubs tracked
SELECT count(*) FROM clubs;

-- Members per club
SELECT c.id, c.name, count(m.user_id) AS members
FROM clubs c LEFT JOIN club_memberships m ON m.club_id = c.id
GROUP BY c.id, c.name ORDER BY members DESC;
```

_Content volume_
```sql
-- Total activities and combined distance (km)
SELECT count(*) AS activities,
       round(sum(distance_meters) / 1000, 1) AS total_km
FROM activities;

-- Data date range
SELECT min(start_date) AS earliest, max(start_date) AS latest
FROM activities;
```

_(All stored activities are runs — `sport_type = 'Run'` is enforced at ingest —
so no sport filter is needed.)_

**3. Caveat box**

- There is **no `last_seen_at`** column, so "active users" cannot be measured by
  login recency. The closest proxy is *who has synced activities* (engagement
  queries above). A future task may add `last_seen_at` for real WAU/DAU.
- Sessions are **signed cookies** (Starlette `SessionMiddleware`), so there is
  **no server-side session store** and therefore no "currently online" count —
  that state does not exist server-side.

**4. `make stats` helper**

- `scripts/stats.sql` — the curated subset as one ordered result set (totals:
  users, signups last 7 days, users synced, users with a goal, total activities,
  total distance, clubs). Single source of truth, reused by the Fly prod command.
- `Makefile` target routes through the compose `db` container (the service
  publishes no host port, and the app's `DATABASE_URL` uses the
  `postgresql+asyncpg://` driver which `psql` cannot parse):
  ```makefile
  stats: ## Print key usage statistics from the local database
  	docker compose exec -T db psql -U postgres -d strava_dev -f - < scripts/stats.sql
  ```
- Local: `make stats`. Production: the same file via `fly postgres connect -a
  <db-app> < scripts/stats.sql` (documented in the doc).

### Files affected

- `docs/ops/db-statistics.md` — new.
- `scripts/stats.sql` — new.
- `Makefile` — new `stats` target + help entry.

### Verification

- Each query in the doc runs without error against a populated local database and
  returns the described shape.
- `make stats` prints the summary against the local DB; documented Fly
  invocations are correct for Fly's CLI.
- This is a documentation/tooling task — no automated tests.

---

## Constraints (both tasks)

- Tokens and secrets are never logged.
- Logging changes must not alter response bodies or rate-limiting behavior.
- Stats access in production goes through the Fly tunnel / `fly postgres connect`
  — the PostgreSQL port is never exposed publicly; a read-only role is preferred.

## Packaging

- One spec (this document); two backlog entries: **TASK-8.2** (logging) and
  **TASK-8.3** (DB stats docs) under **EPIC-8 — Operations & Observability**.
- Two commits, one per task, per the one-task-one-commit rule.
- Note: `TASK-8.1` already exists as an ad-hoc Achievement Badges task; these
  observability tasks take 8.2/8.3 to avoid renumbering it.
