# Design: Integration Test DB Infrastructure (TASK-6.2.1)

**Date:** 2026-06-09
**Status:** Approved (pending spec review)
**Backlog task:** TASK-6.2.1 _(ad-hoc)_ — Set up integration test database infrastructure

## Problem

The current `tests/backend/sync/test_sync_service.py` tests for `_sync_clubs` mock
`db.execute` and assert on `db.execute.call_count`. This verifies only *how many
times* a method was called — not that the correct SQL ran, nor that data landed in
the right columns. We need real integration tests that assert actual database row
state after a sync, and reusable fixtures that all future data-access tests
(TASK-6.3, TASK-6.4, EPIC-7 deletion logic) can build on.

A real PostgreSQL instance is **required**, not optional: `sync_service.py` uses
`sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update(...)` plus
`BigInteger`, `Numeric`, and timezone-aware timestamps. SQLite cannot run these
faithfully, so an in-memory shortcut is ruled out.

## Approach

Use **testcontainers** to start a throwaway PostgreSQL container for the test
session, pinned to an exact image. The suite manages its own database, so `pytest`
works whenever Docker is running — no "did you start the DB?" precondition, and
local matches CI (GitHub Actions `ubuntu-latest` already provides Docker).

### Why testcontainers over alternatives

- **SQLite in-memory** — rejected: dialect mismatch (ON CONFLICT, BigInteger,
  Numeric, tz timestamps). Tests would pass locally and lie about production.
- **Mock the DB** — rejected: this is the current state being replaced; call-count
  assertions give zero confidence in the actual SQL.
- **Externally-provided Postgres (compose + CI `services:`)** — viable, simpler test
  code, faster. Rejected because it is not self-contained: a single dev on Windows
  must remember to start the DB and keep local/CI wiring in sync. testcontainers
  removes that entire failure class, and Docker is already a hard project dependency.

## Feasibility notes (verified)

These are real catches found during design that the backlog wording does not mention:

1. **`config.py` exits at import time.** `backend/shared/config.py:26-29` calls
   `sys.exit(1)` if any of 7 required env vars is missing. There is **no `.env`
   checked in and no `env:` block in CI**, so today the CI `test` job cannot import
   these modules cleanly. **`tests/conftest.py` must set dummy env vars before any
   backend import** so config import succeeds with no local DB and in CI.

2. **testcontainers extra name.** The backlog wrote `testcontainers[postgresql]`; in
   testcontainers 4.x the extra is `testcontainers[postgres]`, imported as
   `from testcontainers.postgres import PostgresContainer`. Verify exact name at
   `uv sync` time.

3. **asyncpg driver + event-loop scoping.** `PostgresContainer` defaults to a
   `psycopg2` URL; we need `driver="asyncpg"`. Combining a session-scoped async
   engine with function-scoped tests under `pytest-asyncio` triggers the classic
   "got Future attached to a different loop" error. **Resolved by Option A below.**

4. **Foreign-key seeding.** `club_memberships.user_id` and `club_id` are FKs. The old
   mock tests passed `user_id=1` to a fake DB; a real DB rejects this unless a `User`
   (and `Club`) row exists. Integration tests must seed a `User` first.

5. **Docker confirmed available** on the dev machine (server 29.4.2).

## Test isolation strategy — Option A (per-test engine)

Decision: **per-test engine, no global loop-scope config.**

- The **container** starts once per session via a plain *synchronous* fixture, so the
  slow part is paid once and stays off the event loop entirely (sidestepping the loop
  trap).
- The **`db`** fixture is function-scoped and async: each test builds its own engine
  on its own event loop, creates the schema, yields a session, then drops the schema
  and disposes. Loops and engines always match → no cross-loop errors. Isolation is
  perfect (fresh schema per test). Cost is ~tens of ms per test on 8 tiny tables —
  negligible at this table count.

Rejected alternative (Option B, spec-literal): one session-scoped engine
("create tables once") forced onto a single shared loop via
`asyncio_default_fixture_loop_scope = "session"` and
`asyncio_default_test_loop_scope = "session"`. This matches the backlog wording but
spreads global loop config across the **entire** suite (blast radius on existing
async tests) to save milliseconds. Not worth it now; revisit only if the suite grows
to hundreds of DB tests, where a truncate-between-tests variant would beat both.

**Deviation from backlog:** the backlog lists three fixtures
(`postgres_container`, `async_engine`, `db`). Under Option A the session-scoped
`async_engine` collapses into the function-scoped `db` fixture. We keep
`postgres_container` (session) and `db` (function); there is no separate
`async_engine` fixture.

## Components

### 1. `tests/conftest.py` — env-var shim (module top, before backend imports)

Set the 7 required env vars with `os.environ.setdefault(...)` so they are only filled
when absent (a real `.env` or CI secret still wins). `DATABASE_URL` gets a throwaway
value; the real test engine uses the container URL instead. `TOKEN_ENCRYPTION_KEY`
must be a valid Fernet key.

```python
import os
from cryptography.fernet import Fernet

os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("STRAVA_REDIRECT_URI", "http://localhost:8000/oauth/callback")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")
```

### 2. Fixtures

- `postgres_container` — `@pytest.fixture(scope="session")` (synchronous). Starts
  `PostgresContainer("postgres:16-alpine", driver="asyncpg")`, yields it, stops on
  teardown.
- `db` — `@pytest_asyncio.fixture` (function scope). Per test:
  1. `engine = create_async_engine(postgres_container.get_connection_url())`
  2. `async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)`
  3. `async with AsyncSession(engine, expire_on_commit=False) as session: yield session`
  4. teardown: `drop_all` + `await engine.dispose()`

### 3. Rewrite `tests/backend/sync/test_sync_service.py` club tests

Remove the two mock-count tests:
- `test_sync_clubs_deletes_memberships_even_when_no_clubs`
- `test_sync_clubs_upserts_clubs_and_inserts_memberships`

Add a small `seed_user(db, ...) -> User` helper (inserts a `User`, returns it).
Rewrite as integration tests that patch `fetch_athlete_clubs`, call `_sync_clubs`
against the real `db`, then query `Club` / `ClubMembership` back and assert exact
contents. New cases:
- Non-empty clubs → `clubs` rows and `club_memberships` rows exist with correct
  values.
- Empty clubs → memberships for the user are removed.
- **Membership replacement:** sync {A, B}, then sync {B, C} → memberships are exactly
  {B, C}.
- **Club name upsert:** sync club id 10 named "Old", then "New" → single `clubs` row,
  name updated.

The existing non-club tests (cooldown, run-filter counts, sync-state upsert,
token-refresh propagation) remain mock-based and untouched — they do not exercise SQL
correctness and converting them is out of scope.

### 4. `pyproject.toml`

Add `testcontainers[postgres]` to the `dev` dependency group. **No** `asyncio_*`
loop-scope settings. Verify the extra name resolves during `uv sync`.

### 5. Documentation — establish this as the standard

So the harness is reused (not reinvented) by TASK-6.3, TASK-6.4, and EPIC-7, three docs
are updated to make real-DB integration testing the documented convention:

- **`CLAUDE.md`** — add a short **Testing Convention** subsection (place it after
  "Key Design Constraints"): data-access logic — anything emitting SQL via Core DML
  (`insert`/`delete`/`on_conflict_*`), ORM persistence (`db.add` + flush), or
  aggregates — **must** have integration tests against a real Postgres using the `db`
  fixture in `tests/conftest.py`; pure logic/branching (cooldown math, the run-filter)
  may stay mock-based. Note the container starts automatically (Docker must be
  running). Also add `tests/conftest.py` to the **Key Files** list and a bullet under
  **Where to Find Things**.
- **`docs/design.md`** — add a new **§6.0.5 Testing Strategy** subsection immediately
  after §6.0.4 (Database Access Pattern). Content: why a real Postgres is required
  (Postgres-specific DML cannot be faithfully mocked or run on SQLite — see the
  `_sync_clubs` vs `_upsert_sync_state` contrast); the testcontainers approach; the
  fixture model (session-scoped synchronous container + function-scoped async `db`,
  fresh schema per test, no global loop-scope config); and the integration-vs-unit
  guideline (assert *outcomes* — query the table — for data access; mock only pure
  logic). Follow the existing 6.0.x heading style.
- **`docs/epics/backlog.md`** — add a brief **Testing Convention** note near the top
  (after the `_Generated_` line, before `## EPICS`) stating that data-access tasks use
  the integration DB harness introduced in TASK-6.2.1, so future tasks' testability
  criteria can assume a real `db` fixture.

These three edits are deliverables of this task, kept in the same commit as the
infrastructure they describe.

## Implementation order

1. **Spike (de-risk first):** add the dep, write a throwaway one-test conftest that
   starts the container and runs `SELECT 1` through asyncpg. Prove the
   Windows + asyncpg + loop path is green before building the rest.
2. Build `tests/conftest.py` (env shim + `postgres_container` + `db`).
3. Rewrite the club tests with `seed_user` + real assertions.
4. Remove the spike scaffolding.
5. Update `CLAUDE.md`, `docs/design.md` (§6.0.5), and `docs/epics/backlog.md` to
   document the convention.

## Verification

- `uv run pytest tests/backend/sync/test_sync_service.py -k clubs -v` passes with **no
  local DB running** (testcontainers starts one; Docker must be running).
- Full suite `uv run pytest` still green (existing tests unaffected).
- First run pulls `postgres:16-alpine` (~30–60s one-time) and starts the Ryuk reaper.
- `CLAUDE.md`, `docs/design.md`, and `docs/epics/backlog.md` updated and internally
  consistent with the implemented fixtures (fixture names and the Docker-must-be-
  running caveat match the code).

## Out of scope

- CI `services:` / explicit Docker wiring (ubuntu runners already provide Docker).
- Converting non-club sync tests to integration tests (`_upsert_activities` and
  `_upsert_sync_state` are noted as future follow-ups, not done here).
- Any change to `sync_service.py` production code.
