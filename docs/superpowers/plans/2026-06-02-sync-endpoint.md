# POST /sync Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `POST /sync` — fetches all current-year running activities from Strava, upserts them into PostgreSQL, enforces a 10-minute per-user cooldown, and records sync completion time.

**Architecture:** A `SyncService` class in `backend/sync/sync_service.py` owns all business logic (cooldown check, token fetch, activity filter, bulk upsert, sync state update). The router in `backend/sync/router.py` handles HTTP concerns only (rate limit, auth, error mapping). The existing `get_db` session with `session.begin()` auto-commits the entire sync atomically.

**Tech Stack:** FastAPI, SQLAlchemy async, `sqlalchemy.dialects.postgresql.insert` (bulk upsert), slowapi, httpx (via existing `fetch_all_activities`), pytest + AsyncMock.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/sync/exceptions.py` | Add `SyncCooldownError` |
| Create | `backend/sync/schemas.py` | `SyncResponse` Pydantic model |
| Create | `backend/sync/sync_service.py` | All sync business logic |
| Create | `backend/sync/router.py` | `POST /sync` HTTP handler |
| Modify | `backend/dependencies.py` | Add `get_sync_service()` factory |
| Modify | `backend/main.py` | Register sync router |
| Create | `tests/backend/sync/test_sync_service.py` | Service unit tests |
| Create | `tests/backend/sync/test_sync_router.py` | Router integration tests |

---

## Task 1: SyncCooldownError + SyncResponse schema

**Files:**
- Modify: `backend/sync/exceptions.py`
- Create: `backend/sync/schemas.py`
- Test: `tests/backend/sync/test_sync_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/sync/test_sync_service.py`:

```python
from backend.sync.exceptions import SyncCooldownError


def test_sync_cooldown_error_stores_retry_after_seconds():
    exc = SyncCooldownError(retry_after_seconds=300)
    assert exc.retry_after_seconds == 300


def test_sync_cooldown_error_is_exception():
    assert issubclass(SyncCooldownError, Exception)
```

- [ ] **Step 2: Run the test and confirm it fails**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: `ImportError` or `AttributeError` — `SyncCooldownError` not yet defined.

- [ ] **Step 3: Add `SyncCooldownError` to `backend/sync/exceptions.py`**

Current content of `backend/sync/exceptions.py`:
```python
from backend.shared.exceptions import StravaAPIError as StravaAPIError
from backend.shared.exceptions import StravaUnauthorizedError as StravaUnauthorizedError
```

Replace entirely with:
```python
from backend.shared.exceptions import StravaAPIError as StravaAPIError
from backend.shared.exceptions import StravaUnauthorizedError as StravaUnauthorizedError


class SyncCooldownError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Sync cooldown active — retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds
```

- [ ] **Step 4: Create `backend/sync/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class SyncResponse(BaseModel):
    synced_activities: int
    last_sync_completed_at: datetime
```

- [ ] **Step 5: Run the test and confirm it passes**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```
git add backend/sync/exceptions.py backend/sync/schemas.py tests/backend/sync/test_sync_service.py
git commit -m "feat(sync): add SyncCooldownError and SyncResponse schema"
```

---

## Task 2: SyncService — cooldown check

**Files:**
- Create: `backend/sync/sync_service.py`
- Modify: `tests/backend/sync/test_sync_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/backend/sync/test_sync_service.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sync.sync_service import COOLDOWN_SECONDS, SyncService


def _make_service() -> SyncService:
    mock_oauth = MagicMock()
    return SyncService(mock_oauth)


def _make_db_with_state(state: object) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = state
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


async def test_check_cooldown_does_not_raise_when_no_sync_state():
    svc = _make_service()
    db = _make_db_with_state(None)
    await svc._check_cooldown(db, user_id=1)  # must not raise


async def test_check_cooldown_raises_when_last_sync_was_recent():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=5)
    db = _make_db_with_state(state)

    with pytest.raises(SyncCooldownError) as exc_info:
        await svc._check_cooldown(db, user_id=1)

    assert 0 < exc_info.value.retry_after_seconds <= COOLDOWN_SECONDS


async def test_check_cooldown_does_not_raise_when_cooldown_expired():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=11)
    db = _make_db_with_state(state)

    await svc._check_cooldown(db, user_id=1)  # must not raise
```

- [ ] **Step 2: Run the tests and confirm they fail**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: `ImportError` — `SyncService` not yet defined.

- [ ] **Step 3: Create `backend/sync/sync_service.py`** with skeleton + `_check_cooldown`

```python
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.models import Activity, SyncState
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from backend.sync.strava_client import fetch_all_activities

COOLDOWN_SECONDS = 600


def _jan1_unix_timestamp() -> int:
    now = datetime.now(UTC)
    return int(datetime(now.year, 1, 1, tzinfo=UTC).timestamp())


class SyncService:
    def __init__(self, oauth_service: StravaOAuthService) -> None:
        self.oauth_service = oauth_service

    async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse:
        raise NotImplementedError

    async def _check_cooldown(self, db: AsyncSession, user_id: int) -> None:
        result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        state = result.scalar_one_or_none()
        if state is None:
            return
        elapsed = datetime.now(UTC) - state.last_sync_completed_at
        if elapsed < timedelta(seconds=COOLDOWN_SECONDS):
            raise SyncCooldownError(COOLDOWN_SECONDS - int(elapsed.total_seconds()))

    async def _upsert_activities(
        self, db: AsyncSession, user_id: int, activities: list[dict[str, Any]]
    ) -> None:
        raise NotImplementedError

    async def _upsert_sync_state(
        self, db: AsyncSession, user_id: int, completed_at: datetime
    ) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Run the tests and confirm they pass**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: 5 tests pass (2 from Task 1 + 3 new).

- [ ] **Step 5: Commit**

```
git add backend/sync/sync_service.py tests/backend/sync/test_sync_service.py
git commit -m "feat(sync): add SyncService skeleton with _check_cooldown"
```

---

## Task 3: SyncService — run_sync, _upsert_activities, _upsert_sync_state

**Files:**
- Modify: `backend/sync/sync_service.py`
- Modify: `tests/backend/sync/test_sync_service.py`

- [ ] **Step 1: Write the failing tests**

Add the following two imports to the import block at the top of `tests/backend/sync/test_sync_service.py` (after the existing imports):
```python
from unittest.mock import patch
from backend.shared.models import SyncState
```

Then append the following test functions at the bottom of the file:

```python


def _make_db_no_state() -> AsyncMock:
    """Returns a mock DB where all scalar lookups return None (first sync scenario)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


async def test_run_sync_returns_zero_count_when_no_activities():
    svc = _make_service()
    db = _make_db_no_state()

    with patch(
        "backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=[])
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 0


async def test_run_sync_counts_only_run_activities():
    svc = _make_service()
    db = _make_db_no_state()

    mixed = [
        {
            "id": 1, "sport_type": "Run", "name": "Morning Run",
            "distance": 5000.0, "moving_time": 1800,
            "start_date": "2026-01-15T08:00:00Z",
        },
        {
            "id": 2, "sport_type": "Ride", "name": "Bike Ride",
            "distance": 20000.0, "moving_time": 3600,
            "start_date": "2026-01-16T09:00:00Z",
        },
        {
            "id": 3, "sport_type": "Run", "name": "Evening Run",
            "distance": 8000.0, "moving_time": 2700,
            "start_date": "2026-01-17T18:00:00Z",
        },
    ]

    with patch(
        "backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=mixed)
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 2


async def test_run_sync_returns_zero_when_all_non_run():
    svc = _make_service()
    db = _make_db_no_state()

    activities = [
        {
            "id": 1, "sport_type": "Swim", "name": "Pool",
            "distance": 1000.0, "moving_time": 1200,
            "start_date": "2026-01-01T07:00:00Z",
        }
    ]

    with patch(
        "backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=activities)
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 0


async def test_upsert_sync_state_inserts_when_no_existing_state():
    svc = _make_service()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    now = datetime.now(UTC)
    await svc._upsert_sync_state(db, user_id=1, completed_at=now)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, SyncState)
    assert added.user_id == 1
    assert added.last_sync_completed_at == now


async def test_upsert_sync_state_updates_existing_state():
    svc = _make_service()
    existing_state = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_state
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    now = datetime.now(UTC)
    await svc._upsert_sync_state(db, user_id=1, completed_at=now)

    db.add.assert_not_called()
    assert existing_state.last_sync_completed_at == now


async def test_run_sync_propagates_token_refresh_error():
    from backend.auth.exceptions import TokenRefreshError

    mock_oauth = MagicMock()
    mock_oauth.ensure_fresh_token = AsyncMock(side_effect=TokenRefreshError("failed"))
    svc = SyncService(mock_oauth)
    db = _make_db_no_state()

    with pytest.raises(TokenRefreshError):
        await svc.run_sync(db, user_id=1)
```

- [ ] **Step 2: Run the tests and confirm they fail**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: the 6 new tests fail with `NotImplementedError`.

- [ ] **Step 3: Implement all methods in `backend/sync/sync_service.py`**

Replace the file entirely:

```python
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.models import Activity, SyncState
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from backend.sync.strava_client import fetch_all_activities

COOLDOWN_SECONDS = 600


def _jan1_unix_timestamp() -> int:
    now = datetime.now(UTC)
    return int(datetime(now.year, 1, 1, tzinfo=UTC).timestamp())


class SyncService:
    def __init__(self, oauth_service: StravaOAuthService) -> None:
        self.oauth_service = oauth_service

    async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse:
        await self._check_cooldown(db, user_id)
        access_token = await self.oauth_service.ensure_fresh_token(db, user_id)
        raw = await fetch_all_activities(access_token, after=_jan1_unix_timestamp())
        runs = [a for a in raw if a.get("sport_type") == "Run"]
        if runs:
            await self._upsert_activities(db, user_id, runs)
        now = datetime.now(UTC)
        await self._upsert_sync_state(db, user_id, now)
        return SyncResponse(synced_activities=len(runs), last_sync_completed_at=now)

    async def _check_cooldown(self, db: AsyncSession, user_id: int) -> None:
        result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        state = result.scalar_one_or_none()
        if state is None:
            return
        elapsed = datetime.now(UTC) - state.last_sync_completed_at
        if elapsed < timedelta(seconds=COOLDOWN_SECONDS):
            raise SyncCooldownError(COOLDOWN_SECONDS - int(elapsed.total_seconds()))

    async def _upsert_activities(
        self, db: AsyncSession, user_id: int, activities: list[dict[str, Any]]
    ) -> None:
        now = datetime.now(UTC)
        rows = [
            {
                "user_id": user_id,
                "strava_activity_id": a["id"],
                "name": a["name"],
                "sport_type": a["sport_type"],
                "distance_meters": a["distance"],
                "moving_time_seconds": a["moving_time"],
                "start_date": datetime.fromisoformat(a["start_date"]),
                "updated_at": now,
            }
            for a in activities
        ]
        stmt = insert(Activity).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "strava_activity_id"],
            set_={
                "name": stmt.excluded.name,
                "sport_type": stmt.excluded.sport_type,
                "distance_meters": stmt.excluded.distance_meters,
                "moving_time_seconds": stmt.excluded.moving_time_seconds,
                "start_date": stmt.excluded.start_date,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await db.execute(stmt)

    async def _upsert_sync_state(
        self, db: AsyncSession, user_id: int, completed_at: datetime
    ) -> None:
        result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        state = result.scalar_one_or_none()
        if state is None:
            db.add(SyncState(user_id=user_id, last_sync_completed_at=completed_at))
        else:
            state.last_sync_completed_at = completed_at
```

- [ ] **Step 4: Run all sync service tests and confirm they pass**

```
uv run pytest tests/backend/sync/test_sync_service.py -v
```

Expected: 11 tests pass.

- [ ] **Step 5: Run the full test suite to confirm nothing is broken**

```
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
git add backend/sync/sync_service.py tests/backend/sync/test_sync_service.py
git commit -m "feat(sync): implement SyncService with run_sync, upsert, and sync state"
```

---

## Task 4: Router + DI + wire into main.py

**Files:**
- Create: `backend/sync/router.py`
- Modify: `backend/dependencies.py`
- Modify: `backend/main.py`
- Create: `tests/backend/sync/test_sync_router.py`

- [ ] **Step 1: Write the failing router tests**

Create `tests/backend/sync/test_sync_router.py`:

```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth.exceptions import TokenRefreshError
from backend.shared.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.shared.models import User
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse


def _stub_user(user: User):
    async def _inner() -> User:
        return user

    return _inner


def _stub_401():
    async def _inner() -> User:
        raise HTTPException(status_code=401)

    return _inner


def _make_user() -> User:
    return User(id=1, strava_athlete_id=99999)


def _make_sync_response() -> SyncResponse:
    return SyncResponse(
        synced_activities=5,
        last_sync_completed_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC),
    )


def test_sync_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_sync_returns_200_and_response_when_successful():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(return_value=_make_sync_response())

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["synced_activities"] == 5
        assert "last_sync_completed_at" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_429_with_retry_after_on_cooldown():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=SyncCooldownError(retry_after_seconds=300))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "300"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_401_on_token_refresh_error():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=TokenRefreshError("refresh failed"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_401_on_strava_unauthorized():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=StravaUnauthorizedError("token invalid"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_502_on_strava_api_error():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=StravaAPIError("API down"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 502
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)
```

- [ ] **Step 2: Run the tests and confirm they fail**

```
uv run pytest tests/backend/sync/test_sync_router.py -v
```

Expected: `ImportError` — `get_sync_service` and `/sync` route not yet defined.

- [ ] **Step 3: Create `backend/sync/router.py`**

```python
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.exceptions import TokenRefreshError
from backend.dependencies import get_sync_service
from backend.shared.db import get_db
from backend.shared.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.shared.models import User
from backend.shared.rate_limit import limiter
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from backend.sync.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
@limiter.limit("2/minute")  # type: ignore[misc]
async def sync_activities(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    sync_service: SyncService = Depends(get_sync_service),  # noqa: B008
) -> SyncResponse:
    try:
        return await sync_service.run_sync(db, current_user.id)
    except SyncCooldownError as exc:
        raise HTTPException(
            status_code=429,
            detail="Sync cooldown active",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except TokenRefreshError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token refresh failed — please log in again",
        ) from exc
    except StravaUnauthorizedError as exc:
        raise HTTPException(
            status_code=401,
            detail="Strava authorization invalid — please log in again",
        ) from exc
    except StravaAPIError as exc:
        logger.error("Strava API error during sync for user %d: %s", current_user.id, exc)
        raise HTTPException(status_code=502, detail="Strava API error") from exc
```

- [ ] **Step 4: Add `get_sync_service` to `backend/dependencies.py`**

Current full content of `backend/dependencies.py`:
```python
from fastapi import Depends

from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.config import settings
from backend.shared.crypto import Crypto

_crypto = Crypto(settings.token_encryption_key)


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_crypto() -> Crypto:
    return _crypto


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service, _crypto)
```

Replace entirely with:
```python
from fastapi import Depends

from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.config import settings
from backend.shared.crypto import Crypto
from backend.sync.sync_service import SyncService

_crypto = Crypto(settings.token_encryption_key)


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_crypto() -> Crypto:
    return _crypto


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service, _crypto)


def get_sync_service(
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> SyncService:
    return SyncService(strava_oauth_service)
```

- [ ] **Step 5: Register the sync router in `backend/main.py`**

Add the import after the existing auth router import (line 17):
```python
from backend.sync.router import router as sync_router
```

Add the router registration after `app.include_router(auth_router)` (line 70):
```python
app.include_router(sync_router)
```

- [ ] **Step 6: Run the router tests and confirm they pass**

```
uv run pytest tests/backend/sync/test_sync_router.py -v
```

Expected: 6 tests pass.

- [ ] **Step 7: Run the full test suite to confirm nothing is broken**

```
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
git add backend/sync/router.py backend/dependencies.py backend/main.py tests/backend/sync/test_sync_router.py
git commit -m "feat(sync): add POST /sync endpoint with cooldown, upsert, and rate limiting (TASK-3.4)"
```
