# Integration Test DB Infrastructure (TASK-6.2.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide reusable pytest fixtures that start a real PostgreSQL via testcontainers and give each test an isolated `AsyncSession`, then replace the mock-count `_sync_clubs` tests with integration tests that assert real DB state — and document this as the standard for future data-access tests.

**Architecture:** A session-scoped *synchronous* `postgres_container` fixture starts one throwaway Postgres for the whole run (kept off the event loop). A function-scoped *async* `db` fixture builds an asyncpg engine per test, creates the full schema, yields a session, and drops the schema afterwards — so each test runs on its own event loop against a pristine schema with no global loop-scope config (Option A). A `tests/conftest.py` env-var shim lets `backend.shared.config` import without a real `.env`.

**Tech Stack:** pytest, pytest-asyncio (`asyncio_mode = "auto"`), testcontainers[postgres], SQLAlchemy async, asyncpg, PostgreSQL 16.

**Spec:** `docs/superpowers/specs/2026-06-09-integration-test-db-infrastructure-design.md`

---

## File Structure

- **Create** `tests/conftest.py` — env-var shim + `postgres_container` (session, sync) + `db` (function, async) fixtures. Root conftest so it applies to the whole suite.
- **Modify** `tests/backend/sync/test_sync_service.py` — remove the two mock-count `_sync_clubs` tests; add a `seed_user` helper and four integration tests.
- **Modify** `pyproject.toml` — add `testcontainers[postgres]` to the `dev` dependency group.
- **Modify** `CLAUDE.md` — Testing Convention section + Key Files / Where to Find Things entries.
- **Modify** `docs/design.md` — new §6.0.5 Testing Strategy.
- **Modify** `docs/epics/backlog.md` — top-of-file Testing Convention note; mark TASK-6.2.1 ✅.
- **Temporary** `tests/test_spike_db.py` — throwaway spike (created and deleted in Task 1).

---

## Task 1: Add dependency and de-risk with a spike

Prove the Windows + Docker + asyncpg + pytest-asyncio path works end-to-end before building anything reusable. This validates the exact testcontainers extra name and async connection API.

**Files:**
- Modify: `pyproject.toml` (dev group)
- Create (temporary): `tests/test_spike_db.py`

- [ ] **Step 1: Add the dependency**

Run:
```bash
uv add --group dev "testcontainers[postgres]"
```
Expected: `pyproject.toml` gains `testcontainers[postgres]>=...` under `[dependency-groups] dev` and `uv.lock` updates. If uv reports the `postgres` extra is unknown, retry with `testcontainers[postgresql]` and note which one resolved (this is the spec's open item #2).

- [ ] **Step 2: Write the spike test**

Create `tests/test_spike_db.py`:
```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer


async def test_spike_container_select_one() -> None:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        engine = create_async_engine(pg.get_connection_url())
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
        await engine.dispose()
```

- [ ] **Step 3: Run the spike (Docker must be running)**

Run:
```bash
uv run pytest tests/test_spike_db.py -v
```
Expected: PASS. First run pulls `postgres:16-alpine` (~30–60s) and starts the Ryuk reaper container. If it fails with `got Future attached to a different loop`, the Option-A assumption is wrong — STOP and report before proceeding. If `get_connection_url()` returns a `psycopg2` URL, confirm `driver="asyncpg"` was passed.

- [ ] **Step 4: Delete the spike**

Run:
```bash
git rm -f tests/test_spike_db.py 2>/dev/null || rm tests/test_spike_db.py
```
The spike has served its purpose; the real fixtures come next.

- [ ] **Step 5: Commit the dependency**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add testcontainers[postgres] for integration tests"
```

---

## Task 2: Build the fixtures and the first integration test

TDD: write one club integration test that needs the `db` fixture (fails — no fixture yet), then create `conftest.py` to make it pass. This proves the harness against real code.

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/backend/sync/test_sync_service.py`

- [ ] **Step 1: Add imports and a `seed_user` helper to the test file**

At the top of `tests/backend/sync/test_sync_service.py`, add two new imports and extend the existing models import. The current line `from backend.shared.models import SyncState` becomes:
```python
from backend.shared.models import Club, ClubMembership, SyncState, User
```
And add these two lines alongside the other imports:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```
Then add this helper near the other `_make_*` helpers:
```python
async def seed_user(db: AsyncSession, strava_athlete_id: int = 12345) -> User:
    """Insert a User row and flush so its autoincrement id is available for FKs."""
    user = User(strava_athlete_id=strava_athlete_id)
    db.add(user)
    await db.flush()
    return user
```

- [ ] **Step 2: Write the first integration test (failing)**

Append to `tests/backend/sync/test_sync_service.py`:
```python
# ---------------------------------------------------------------------------
# SyncService._sync_clubs — integration tests (real PostgreSQL via `db` fixture)
# ---------------------------------------------------------------------------


async def test_sync_clubs_inserts_clubs_and_memberships(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()
    clubs = [{"id": 10, "name": "Club A"}, {"id": 20, "name": "Club B"}]

    with patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=clubs)):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    club_rows = (await db.execute(select(Club).order_by(Club.id))).scalars().all()
    assert [(c.id, c.name) for c in club_rows] == [(10, "Club A"), (20, "Club B")]

    membership_ids = (
        await db.execute(
            select(ClubMembership.club_id)
            .where(ClubMembership.user_id == user.id)
            .order_by(ClubMembership.club_id)
        )
    ).scalars().all()
    assert membership_ids == [10, 20]
```

- [ ] **Step 3: Run it to verify it fails for the right reason**

Run:
```bash
uv run pytest tests/backend/sync/test_sync_service.py::test_sync_clubs_inserts_clubs_and_memberships -v
```
Expected: ERROR — `fixture 'db' not found`. (Not a failed assertion — a missing fixture.)

- [ ] **Step 4: Create `tests/conftest.py`**

Create `tests/conftest.py`:
```python
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

# Set required env vars BEFORE importing any backend module: backend.shared.config
# calls sys.exit(1) at import time if any are missing, and there is no .env in CI.
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("STRAVA_REDIRECT_URI", "http://localhost:8000/oauth/callback")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")

from backend.shared.models import Base  # noqa: E402  (must follow env setup above)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start one throwaway Postgres for the whole test session (synchronous: stays
    off the event loop, so it never collides with per-test loops)."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg


@pytest_asyncio.fixture
async def db(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncSession, None]:
    """Per-test AsyncSession against a fresh schema. A new engine is built on the
    test's own event loop (Option A: no shared engine, no global loop-scope config)."""
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/backend/sync/test_sync_service.py::test_sync_clubs_inserts_clubs_and_memberships -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/backend/sync/test_sync_service.py
git commit -m "test(sync): add integration DB harness and first club integration test"
```

---

## Task 3: Replace the remaining mock-count tests with integration tests

Add the three remaining real-DB cases, then delete the two obsolete mock-count tests.

**Files:**
- Modify: `tests/backend/sync/test_sync_service.py`

- [ ] **Step 1: Add the membership-removal test**

Append:
```python
async def test_sync_clubs_removes_memberships_when_no_clubs(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "Club A"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    with patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=[])):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    remaining = (
        await db.execute(select(ClubMembership).where(ClubMembership.user_id == user.id))
    ).scalars().all()
    assert remaining == []
```

- [ ] **Step 2: Add the membership-replacement test**

Append:
```python
async def test_sync_clubs_replaces_membership_set(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "A"}, {"id": 20, "name": "B"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 20, "name": "B"}, {"id": 30, "name": "C"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    membership_ids = (
        await db.execute(
            select(ClubMembership.club_id)
            .where(ClubMembership.user_id == user.id)
            .order_by(ClubMembership.club_id)
        )
    ).scalars().all()
    assert membership_ids == [20, 30]
```

- [ ] **Step 3: Add the club-name upsert test**

Append:
```python
async def test_sync_clubs_upserts_club_name(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "Old Name"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "New Name"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")  # noqa: S106

    clubs = (await db.execute(select(Club).where(Club.id == 10))).scalars().all()
    assert len(clubs) == 1
    assert clubs[0].name == "New Name"
```

- [ ] **Step 4: Delete the two obsolete mock-count tests**

In `tests/backend/sync/test_sync_service.py`, remove these two functions entirely (they assert `db.execute.call_count`, replaced by the integration tests above):
- `test_sync_clubs_deletes_memberships_even_when_no_clubs`
- `test_sync_clubs_upserts_clubs_and_inserts_memberships`

Keep `test_run_sync_calls_sync_clubs_with_access_token` (it tests delegation wiring, not SQL) and all cooldown / run-filter / sync-state / token-refresh tests unchanged.

- [ ] **Step 5: Run the full club test set**

Run:
```bash
uv run pytest tests/backend/sync/test_sync_service.py -k clubs -v
```
Expected: 4 PASS (`inserts_clubs_and_memberships`, `removes_memberships_when_no_clubs`, `replaces_membership_set`, `upserts_club_name`), 1 PASS for `test_run_sync_calls_sync_clubs_with_access_token`. No reference to the two deleted tests.

- [ ] **Step 6: Run the whole suite**

Run:
```bash
uv run pytest
```
Expected: all green, no errors collecting (env shim lets config import). Confirms existing mock-based tests are unaffected.

- [ ] **Step 7: Lint**

Run:
```bash
uv run ruff check tests/ && uv run ruff format --check tests/
```
Expected: pass. If imports are flagged unordered, run `uv run ruff check --fix tests/` and `uv run ruff format tests/`.

- [ ] **Step 8: Commit**

```bash
git add tests/backend/sync/test_sync_service.py
git commit -m "test(sync): replace club mock-count tests with real-DB integration tests"
```

---

## Task 4: Document the convention

Make real-DB integration testing the documented standard so TASK-6.3, TASK-6.4, and EPIC-7 reuse the harness.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/design.md`
- Modify: `docs/epics/backlog.md`

- [ ] **Step 1: Add the Testing Convention section to `CLAUDE.md`**

Insert this new section immediately after the `## Key Design Constraints` block (after its closing `---`, before `## Commands`):
```markdown
## Testing Convention

Data-access logic is verified with **integration tests against a real PostgreSQL**, not mocks. A throwaway Postgres starts automatically via `testcontainers` (Docker must be running); use the `db` fixture in `tests/conftest.py` to get a per-test `AsyncSession` against a fresh schema.

- **Write an integration test** (use the `db` fixture) whenever the code emits SQL: Core DML (`insert`/`delete`/`on_conflict_*`), ORM persistence (`db.add` + flush), or aggregate/window queries. Assert on **actual row state read back from the DB** — never on `db.execute.call_count`.
- **A mock-based unit test is appropriate** only for pure logic with no SQL semantics (e.g. cooldown math, the `sport_type == "Run"` filter).
- The container starts once per test session; each test gets an isolated schema, so tests need no manual cleanup.

---
```

- [ ] **Step 2: Add `tests/conftest.py` to the Key Files and Where to Find Things lists in `CLAUDE.md`**

In the `## Key Files` list, add:
```markdown
- **Test fixtures:** `tests/conftest.py` — session-scoped Postgres container + per-test `db` `AsyncSession` for integration tests
```
In the `## Where to Find Things` list, add:
```markdown
- **Test DB harness:** `tests/conftest.py`
```

- [ ] **Step 3: Add §6.0.5 Testing Strategy to `docs/design.md`**

Insert immediately after the §6.0.4 (Database Access Pattern) block and before the `## 6. Architecture` heading:
```markdown
### 6.0.5 Testing Strategy

Data-access code is verified with **integration tests against a real PostgreSQL**, started on demand via `testcontainers` (see `tests/conftest.py`). A real database is required, not a convenience: the sync engine uses PostgreSQL-specific DML — `insert(...).on_conflict_do_update(...)`, set-based `delete(...).where(...)` — plus `BigInteger`/`Numeric`/timezone-aware columns. These cannot be faithfully mocked or emulated on SQLite, so a mock that only counts `db.execute` calls proves nothing about the SQL that actually runs.

**Fixture model:** a session-scoped, synchronous `postgres_container` fixture starts one throwaway Postgres for the test session; a function-scoped async `db` fixture builds an asyncpg engine, creates the full schema, yields an `AsyncSession`, and drops the schema afterwards. Each test runs against a pristine schema on its own event loop — no shared state and no global event-loop configuration.

**When to use which:** write an integration test (assert on rows read back from the database) for anything that emits SQL — Core DML, ORM persistence, or aggregates. Reserve mock-based unit tests for pure logic with no database semantics (cooldown timing, activity-type filtering). Prefer asserting outcomes (the row that landed) over intent (the object handed to the session).
```

- [ ] **Step 4: Add the Testing Convention note to `docs/epics/backlog.md`**

Insert between the `_Generated: May 2, 2026_` line's following `---` and the `## EPICS` heading:
```markdown
## Testing Convention

Data-access tasks are verified with integration tests against a real PostgreSQL via the `db` fixture in `tests/conftest.py` (introduced in TASK-6.2.1). Testability criteria below that read like "after sync, the table contains…" assume this harness — assert on real row state, not mock call counts.

---
```

- [ ] **Step 5: Mark TASK-6.2.1 complete in `docs/epics/backlog.md`**

Change the heading `#### TASK-6.2.1 _(ad-hoc)_` to `#### TASK-6.2.1 ✅`.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md docs/design.md docs/epics/backlog.md
git commit -m "docs: document integration test DB convention; mark TASK-6.2.1 done"
```

---

## Task 5: Final verification

- [ ] **Step 1: Full suite with no local DB running**

Ensure no local Postgres is needed (testcontainers provides it). Run:
```bash
uv run pytest
```
Expected: all tests pass, including the four club integration tests.

- [ ] **Step 2: CI gate locally**

Run:
```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy backend frontend
```
Expected: pass. (`tests/` is excluded from mypy by `pyproject.toml`, so conftest/test typing is not gated.)

- [ ] **Step 3: Confirm the spike is gone**

Run:
```bash
git status --porcelain && ls tests/test_spike_db.py 2>&1
```
Expected: clean working tree; `tests/test_spike_db.py` does not exist.

---

## Notes / risks (carry into execution)

- **Docker must be running** for any of these tests. If `pytest` hangs or errors with a Docker connection error, start Docker Desktop first.
- **First run is slow** (~30–60s) pulling `postgres:16-alpine`; subsequent runs reuse the image.
- **Extra name** (`testcontainers[postgres]` vs `[postgresql]`) is verified in Task 1, Step 1 — use whichever uv resolves.
- **`# noqa: S106`** on `_sync_clubs(..., "token")` silences the bandit hardcoded-password rule (it is a dummy access token), matching the existing convention in this file.
- If the spike (Task 1) hits `got Future attached to a different loop`, the Option-A assumption failed — stop and reconsider before building fixtures.
