# Dashboard Domain Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move personal dashboard logic out of the `goals` domain into a new `dashboard/` domain so `GoalService` becomes pure goal CRUD and `/dashboard/*` routes have a clean home.

**Architecture:** Four tasks: (1) scaffold the new domain + service tests; (2) atomic routing cut-over — wire dashboard router, remove route from goals, swap router tests; (3) strip dashboard code from goals domain; (4) update backlog. Route URL, response shape, and status codes are unchanged throughout.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, `unittest.mock`.

---

## File Map

| File | Action |
|---|---|
| `backend/dashboard/__init__.py` | Create (empty) |
| `backend/dashboard/schemas.py` | Create — `PersonalDashboardResponse` |
| `backend/dashboard/dashboard_service.py` | Create — `DashboardService` |
| `backend/dashboard/router.py` | Create — `GET /dashboard/personal` |
| `backend/dependencies.py` | Modify — add `get_dashboard_service` factory |
| `backend/main.py` | Modify — register `dashboard_router` |
| `backend/goals/router.py` | Modify — remove dashboard route |
| `backend/goals/goals_service.py` | Modify — remove `get_personal_dashboard` |
| `backend/goals/schemas.py` | Modify — remove `PersonalDashboardResponse` |
| `tests/backend/dashboard/__init__.py` | Create (empty) |
| `tests/backend/dashboard/test_dashboard_service.py` | Create — 5 service tests |
| `tests/backend/dashboard/test_dashboard_router.py` | Create — 4 router tests |
| `tests/backend/goals/test_goal_service.py` | Modify — remove dashboard helpers + tests |
| `tests/backend/goals/test_goals_router.py` | Modify — remove 4 dashboard tests |

---

## Task 1: Create `backend/dashboard/` domain + service tests

**Files:**
- Create: `backend/dashboard/__init__.py`
- Create: `backend/dashboard/schemas.py`
- Create: `backend/dashboard/dashboard_service.py`
- Create: `backend/dashboard/router.py`
- Create: `tests/backend/dashboard/__init__.py`
- Create: `tests/backend/dashboard/test_dashboard_service.py`

- [ ] **Step 1: Write a failing import test**

Create `tests/backend/dashboard/__init__.py` (empty file), then create `tests/backend/dashboard/test_dashboard_service.py` with just the import smoke test:

```python
from decimal import Decimal
from datetime import UTC
from datetime import datetime as _real_datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.dashboard.dashboard_service import DashboardService
from backend.shared.models import Goal, SyncState
from fastapi import HTTPException
```

- [ ] **Step 2: Run to confirm it fails**

```
uv run pytest tests/backend/dashboard/test_dashboard_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.dashboard'`

- [ ] **Step 3: Create `backend/dashboard/__init__.py`**

Empty file at `backend/dashboard/__init__.py`.

- [ ] **Step 4: Create `backend/dashboard/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
```

- [ ] **Step 5: Create `backend/dashboard/dashboard_service.py`**

```python
import calendar
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.schemas import PersonalDashboardResponse
from backend.shared.models import Activity, Goal, SyncState


class DashboardService:
    async def get_personal_dashboard(
        self, db: AsyncSession, user_id: int
    ) -> PersonalDashboardResponse:
        sync_result = await db.execute(
            select(SyncState).where(SyncState.user_id == user_id)
        )
        sync_state = sync_result.scalar_one_or_none()
        if sync_state is None:
            raise HTTPException(status_code=404, detail="not_synced")

        goal_result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = goal_result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")

        now = datetime.now(UTC)
        year_start = datetime(now.year, 1, 1, tzinfo=UTC)

        sum_result = await db.execute(
            select(func.sum(Activity.distance_meters)).where(
                Activity.user_id == user_id,
                Activity.start_date >= year_start,
            )
        )
        sum_meters = sum_result.scalar()

        goal_km = float(goal.yearly_running_goal_km)
        distance_to_date_km = float(sum_meters or 0) / 1000
        progress_pct = round(distance_to_date_km / goal_km * 100, 2)

        today = now.date()
        days_in_year = 366 if calendar.isleap(today.year) else 365
        day_of_year = today.timetuple().tm_yday
        expected_pct = round(day_of_year / days_in_year * 100, 2)
        on_pace = distance_to_date_km >= goal_km * (day_of_year / days_in_year)

        return PersonalDashboardResponse(
            goal_km=goal_km,
            distance_to_date_km=distance_to_date_km,
            progress_pct=progress_pct,
            on_pace=on_pace,
            expected_pct=expected_pct,
            last_sync_completed_at=sync_state.last_sync_completed_at,
        )
```

- [ ] **Step 6: Create `backend/dashboard/router.py`**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dashboard.dashboard_service import DashboardService
from backend.dashboard.schemas import PersonalDashboardResponse
from backend.dependencies import get_dashboard_service
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.get("/dashboard/personal", response_model=PersonalDashboardResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_personal_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    dashboard_service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> PersonalDashboardResponse:
    return await dashboard_service.get_personal_dashboard(db, current_user.id)
```

- [ ] **Step 7: Complete the service test file**

Replace the content of `tests/backend/dashboard/test_dashboard_service.py` with the full test suite:

```python
from datetime import UTC
from datetime import datetime as _real_datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.dashboard.dashboard_service import DashboardService
from backend.shared.models import Goal, SyncState
from fastapi import HTTPException


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


def _make_sync_state() -> SyncState:
    state = SyncState()
    state.user_id = 1
    state.last_sync_completed_at = _real_datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    return state


def _make_db_for_dashboard(sync_state: object, goal: object, sum_meters: object) -> AsyncMock:
    """Mock db for get_personal_dashboard: 3 sequential execute() calls."""
    sync_result = MagicMock()
    sync_result.scalar_one_or_none.return_value = sync_state

    goal_result = MagicMock()
    goal_result.scalar_one_or_none.return_value = goal

    sum_result = MagicMock()
    sum_result.scalar.return_value = sum_meters

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[sync_result, goal_result, sum_result])
    return db


_FIXED_NOW = _real_datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
# 2026-06-06 is day 157 of 365 (non-leap year)
# expected_pct = round(157/365*100, 2) = 43.01
# expected_km  = 365 * (157/365)       = 157.0


async def test_get_personal_dashboard_raises_404_when_no_sync_state():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=None, goal=_make_goal(), sum_meters=None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not_synced"


async def test_get_personal_dashboard_raises_404_when_no_goal():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=_make_sync_state(), goal=None, sum_meters=None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Goal not found"


async def test_get_personal_dashboard_returns_zero_when_no_activities():
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        sum_meters=None,
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 0.0
    assert result.progress_pct == 0.0
    assert result.on_pace is False


async def test_get_personal_dashboard_on_pace_true_when_ahead():
    # 200 km done, expected = 157.0 km → on pace
    # progress_pct = round(200/365*100, 2) = 54.79
    svc = DashboardService()
    sync = _make_sync_state()
    db = _make_db_for_dashboard(
        sync_state=sync,
        goal=_make_goal(365.0),
        sum_meters=Decimal("200000"),
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.goal_km == 365.0
    assert result.distance_to_date_km == 200.0
    assert result.progress_pct == 54.79
    assert result.on_pace is True
    assert result.expected_pct == 43.01
    assert result.last_sync_completed_at == sync.last_sync_completed_at


async def test_get_personal_dashboard_on_pace_false_when_behind():
    # 142.5 km done, expected = 157.0 km → behind
    # progress_pct = round(142.5/365*100, 2) = 39.04
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        sum_meters=Decimal("142500"),
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 142.5
    assert result.progress_pct == 39.04
    assert result.on_pace is False
    assert result.expected_pct == 43.01
```

- [ ] **Step 8: Run the service tests to confirm they pass**

```
uv run pytest tests/backend/dashboard/test_dashboard_service.py -v
```

Expected: 5 passed

- [ ] **Step 9: Run full suite to confirm no regressions**

```
uv run pytest tests/ -v
```

Expected: all passed (117 + 5 new = 122 passed)

- [ ] **Step 10: Commit**

```
git add backend/dashboard/ tests/backend/dashboard/__init__.py tests/backend/dashboard/test_dashboard_service.py
git commit -m "feat(dashboard): scaffold dashboard domain with DashboardService"
```

---

## Task 2: Atomic routing cut-over

Wire `dashboard_router` into the app, remove the dashboard route from the goals router, and swap all router-level tests in one commit. This avoids the route being registered twice.

**Files:**
- Modify: `backend/dependencies.py`
- Modify: `backend/main.py`
- Modify: `backend/goals/router.py`
- Create: `tests/backend/dashboard/test_dashboard_router.py`
- Modify: `tests/backend/goals/test_goals_router.py`

- [ ] **Step 1: Write the failing dashboard router tests**

Create `tests/backend/dashboard/test_dashboard_router.py`:

```python
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.shared.models import Goal, User
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from backend.shared.rate_limit import limiter

    limiter._storage.reset()
    yield


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


def test_personal_dashboard_response_schema_importable():
    from backend.dashboard.schemas import PersonalDashboardResponse  # noqa: F401


def test_get_personal_dashboard_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/personal")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_personal_dashboard_returns_200_with_correct_shape():
    from datetime import UTC, datetime

    from backend.auth.dependencies import get_current_user
    from backend.dashboard.schemas import PersonalDashboardResponse
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    fixed_time = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    mock_response = PersonalDashboardResponse(
        goal_km=365.0,
        distance_to_date_km=142.5,
        progress_pct=39.04,
        on_pace=False,
        expected_pct=43.01,
        last_sync_completed_at=fixed_time,
    )
    mock_svc = MagicMock()
    mock_svc.get_personal_dashboard = AsyncMock(return_value=mock_response)

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/dashboard/personal")
        assert response.status_code == 200
        data = response.json()
        assert data["goal_km"] == 365.0
        assert data["distance_to_date_km"] == 142.5
        assert data["progress_pct"] == 39.04
        assert data["on_pace"] is False
        assert data["expected_pct"] == 43.01
        assert "last_sync_completed_at" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)


def test_get_personal_dashboard_returns_404_when_not_synced():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_personal_dashboard = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="not_synced")
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/personal")
        assert response.status_code == 404
        assert response.json()["detail"] == "not_synced"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/backend/dashboard/test_dashboard_router.py -v
```

Expected: 2 failed (`test_..._200_with_correct_shape`, `test_..._404_when_not_synced`) — the route currently uses `get_goal_service`, not `get_dashboard_service`.

- [ ] **Step 3: Add `get_dashboard_service` to `backend/dependencies.py`**

Replace the full content of `backend/dependencies.py`:

```python
from fastapi import Depends

from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.dashboard.dashboard_service import DashboardService
from backend.goals.goals_service import GoalService
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


def get_goal_service() -> GoalService:
    return GoalService()


def get_dashboard_service() -> DashboardService:
    return DashboardService()
```

- [ ] **Step 4: Register `dashboard_router` and remove dashboard route from goals router**

Replace the full content of `backend/main.py`:

```python
import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from backend.auth.router import router as auth_router
from backend.dashboard.router import router as dashboard_router
from backend.goals.router import router as goals_router
from backend.shared.config import settings
from backend.shared.db import engine
from backend.shared.rate_limit import limiter
from backend.sync.router import router as sync_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — run DB migrations on startup
# ---------------------------------------------------------------------------
def _run_migrations() -> None:
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Running database migrations...")
    await asyncio.to_thread(_run_migrations)
    logger.info("Database migrations complete.")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Strava Goal Visualizer API", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=False,
    same_site="lax",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)
app.include_router(sync_router)
app.include_router(goals_router)
app.include_router(dashboard_router)


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str


class DbHealthResponse(BaseModel):
    db: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/db", response_model=DbHealthResponse)
@limiter.limit("10/minute")  # type: ignore[misc]
async def health_db(request: Request) -> DbHealthResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return DbHealthResponse(db="ok")
    except (SQLAlchemyError, OSError) as exc:
        logger.error("DB health check failed: %s", exc)
        return DbHealthResponse(db="error")
```

Replace the full content of `backend/goals/router.py`:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_goal_service
from backend.goals.goals_service import GoalService
from backend.goals.schemas import GoalResponse, UpdateGoalRequest
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.get("/goals", response_model=GoalResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_goals(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> GoalResponse:
    goal = await goal_service.get_goal(db, current_user.id)
    return GoalResponse(yearly_running_goal_km=float(goal.yearly_running_goal_km))


@router.put("/goals", response_model=GoalResponse)
@limiter.limit("10/minute")  # type: ignore[misc]
async def update_goals(
    request: Request,
    body: UpdateGoalRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> GoalResponse:
    goal = await goal_service.update_goal(db, current_user.id, body.yearly_running_goal_km)
    return GoalResponse(yearly_running_goal_km=float(goal.yearly_running_goal_km))
```

- [ ] **Step 5: Remove dashboard tests from `tests/backend/goals/test_goals_router.py`**

Replace the full content of `tests/backend/goals/test_goals_router.py`:

```python
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.shared.models import Goal, User
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from backend.shared.rate_limit import limiter

    limiter._storage.reset()
    yield


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


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


def test_get_goals_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/goals")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_goals_returns_200_with_default_goal():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_goal = AsyncMock(return_value=_make_goal(365.0))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/goals")
        assert response.status_code == 200
        assert response.json()["yearly_running_goal_km"] == 365.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 500.0})
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_put_goals_returns_200_with_updated_value():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.update_goal = AsyncMock(return_value=_make_goal(500.0))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.put("/goals", json={"yearly_running_goal_km": 500.0})
        assert response.status_code == 200
        assert response.json()["yearly_running_goal_km"] == 500.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_zero_km():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 0})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_negative_km():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": -10})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_km_above_100000():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 100_001})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)
```

- [ ] **Step 6: Run the dashboard router tests to confirm they pass**

```
uv run pytest tests/backend/dashboard/test_dashboard_router.py -v
```

Expected: 4 passed

- [ ] **Step 7: Run the full test suite**

```
uv run pytest tests/ -v
```

Expected: all passed

- [ ] **Step 8: Commit**

```
git add backend/dependencies.py backend/main.py backend/goals/router.py tests/backend/dashboard/test_dashboard_router.py tests/backend/goals/test_goals_router.py
git commit -m "refactor(dashboard): wire dashboard router and remove route from goals"
```

---

## Task 3: Clean up goals domain

Strip `get_personal_dashboard` and `PersonalDashboardResponse` from the goals domain, and remove the now-redundant dashboard tests from the goals test files.

**Files:**
- Modify: `backend/goals/goals_service.py`
- Modify: `backend/goals/schemas.py`
- Modify: `tests/backend/goals/test_goal_service.py`

- [ ] **Step 1: Replace `backend/goals/goals_service.py`**

```python
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import Goal


class GoalService:
    async def get_goal(self, db: AsyncSession, user_id: int) -> Goal:
        result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal

    async def update_goal(self, db: AsyncSession, user_id: int, km: float) -> Goal:
        result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")
        goal.yearly_running_goal_km = Decimal(str(km))
        return goal
```

- [ ] **Step 2: Replace `backend/goals/schemas.py`**

```python
from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    yearly_running_goal_km: float


class UpdateGoalRequest(BaseModel):
    yearly_running_goal_km: float = Field(gt=0, le=100_000)
```

- [ ] **Step 3: Replace `tests/backend/goals/test_goal_service.py`**

```python
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.goals.goals_service import GoalService
from backend.shared.models import Goal
from fastapi import HTTPException


def _make_db_with_goal(goal: object) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = goal
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


async def test_get_goal_returns_goal_when_found():
    svc = GoalService()
    goal = _make_goal()
    db = _make_db_with_goal(goal)
    result = await svc.get_goal(db, user_id=1)
    assert result is goal


async def test_get_goal_raises_404_when_not_found():
    svc = GoalService()
    db = _make_db_with_goal(None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_goal(db, user_id=1)
    assert exc_info.value.status_code == 404


async def test_update_goal_sets_km_and_returns_goal():
    svc = GoalService()
    goal = _make_goal(365.0)
    db = _make_db_with_goal(goal)
    result = await svc.update_goal(db, user_id=1, km=500.0)
    assert result.yearly_running_goal_km == Decimal("500.0")
    assert result is goal


async def test_update_goal_raises_404_when_not_found():
    svc = GoalService()
    db = _make_db_with_goal(None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update_goal(db, user_id=1, km=500.0)
    assert exc_info.value.status_code == 404


async def test_update_goal_does_not_commit():
    svc = GoalService()
    goal = _make_goal(365.0)
    db = _make_db_with_goal(goal)
    await svc.update_goal(db, user_id=1, km=500.0)
    db.commit.assert_not_called()
```

- [ ] **Step 4: Run the full test suite**

```
uv run pytest tests/ -v
```

Expected: all passed (same count as after Task 2 — dashboard tests in goals are gone, dashboard tests in new module remain)

- [ ] **Step 5: Run CI checks**

```
uv run ruff check backend/ tests/ && uv run ruff format --check backend/ tests/ && uv run mypy backend/
```

Expected: ruff clean on changed files, mypy passes

- [ ] **Step 6: Commit**

```
git add backend/goals/goals_service.py backend/goals/schemas.py tests/backend/goals/test_goal_service.py
git commit -m "refactor(goals): remove dashboard logic, GoalService is now pure goal CRUD"
```

---

## Task 4: Update backlog

- [ ] **Step 1: Add ad-hoc refactor entry to `docs/epics/backlog.md`**

Find the section `#### TASK-5.3 ✅` in `docs/epics/backlog.md` and add the following entry directly after its closing `---`:

```markdown
#### AD-HOC ✅

**Name:** Move personal dashboard into `dashboard/` domain

**Goal:** Separate cross-domain dashboard logic from `GoalService` so goal CRUD stays clean and `/dashboard/*` routes have a dedicated home ahead of the club dashboard.

**Changes:** Created `backend/dashboard/` domain (`schemas.py`, `dashboard_service.py`, `router.py`). Removed `get_personal_dashboard` and `PersonalDashboardResponse` from goals domain. Updated `dependencies.py` and `main.py`. Moved all dashboard tests to `tests/backend/dashboard/`.

---
```

- [ ] **Step 2: Commit**

```
git add docs/epics/backlog.md
git commit -m "docs(backlog): record dashboard domain refactor as ad-hoc task"
```

---

## Done

After all four tasks, `GoalService` owns only `get_goal` and `update_goal`. All dashboard logic lives in `backend/dashboard/`. Test count is unchanged. The endpoint behaviour is identical.
