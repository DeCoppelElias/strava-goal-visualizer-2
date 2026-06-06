# TASK-5.3 Personal Progress Computation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /dashboard/personal` that computes current-year running distance and pace against the user's yearly goal.

**Architecture:** Three small changes in the goals domain: add `PersonalDashboardResponse` to schemas, add `get_personal_dashboard` to `GoalService`, add the route to the router. No new files, no changes to `dependencies.py` or `main.py`.

**Tech Stack:** FastAPI, SQLAlchemy async (`func.sum`), Pydantic v2, `calendar` stdlib, `unittest.mock` for tests.

---

## File Map

| File | Change |
|---|---|
| `backend/goals/schemas.py` | Add `PersonalDashboardResponse` |
| `backend/goals/goals_service.py` | Add `get_personal_dashboard` method to `GoalService` |
| `backend/goals/router.py` | Add `GET /dashboard/personal` route |
| `tests/backend/goals/test_goal_service.py` | Add service-level tests |
| `tests/backend/goals/test_goals_router.py` | Add router-level tests |

---

## Task 1: Add `PersonalDashboardResponse` schema

**Files:**
- Modify: `backend/goals/schemas.py`
- Test: `tests/backend/goals/test_goals_router.py` (import smoke test added at top of file)

- [ ] **Step 1: Write a failing import test**

Add this test at the bottom of `tests/backend/goals/test_goals_router.py`:

```python
def test_personal_dashboard_response_schema_importable():
    from backend.goals.schemas import PersonalDashboardResponse  # noqa: F401
```

- [ ] **Step 2: Run the test to confirm it fails**

```
uv run pytest tests/backend/goals/test_goals_router.py::test_personal_dashboard_response_schema_importable -v
```

Expected: `ImportError: cannot import name 'PersonalDashboardResponse'`

- [ ] **Step 3: Add the schema**

Replace the full content of `backend/goals/schemas.py` with:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    yearly_running_goal_km: float


class UpdateGoalRequest(BaseModel):
    yearly_running_goal_km: float = Field(gt=0, le=100_000)


class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
```

- [ ] **Step 4: Run the test to confirm it passes**

```
uv run pytest tests/backend/goals/test_goals_router.py::test_personal_dashboard_response_schema_importable -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```
git add backend/goals/schemas.py tests/backend/goals/test_goals_router.py
git commit -m "feat(goals): add PersonalDashboardResponse schema"
```

---

## Task 2: Implement `get_personal_dashboard` service method

**Files:**
- Modify: `backend/goals/goals_service.py`
- Test: `tests/backend/goals/test_goal_service.py`

- [ ] **Step 1: Write the failing service tests**

Add the following to the bottom of `tests/backend/goals/test_goal_service.py`.

First, add these imports at the top of the file (merge with existing imports):

```python
from datetime import UTC, datetime as _real_datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.goals.goals_service import GoalService
from backend.shared.models import Goal, SyncState
from fastapi import HTTPException
```

Then add these helpers and tests at the bottom:

```python
# ── dashboard helpers ────────────────────────────────────────────────────────

def _make_sync_state() -> SyncState:
    state = SyncState()
    state.user_id = 1
    state.last_sync_completed_at = _real_datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    return state


def _make_db_for_dashboard(
    sync_state: object, goal: object, sum_meters: object
) -> AsyncMock:
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


# ── dashboard tests ──────────────────────────────────────────────────────────

async def test_get_personal_dashboard_raises_404_when_no_sync_state():
    svc = GoalService()
    db = _make_db_for_dashboard(sync_state=None, goal=_make_goal(), sum_meters=None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not_synced"


async def test_get_personal_dashboard_raises_404_when_no_goal():
    svc = GoalService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(), goal=None, sum_meters=None
    )
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Goal not found"


async def test_get_personal_dashboard_returns_zero_when_no_activities():
    svc = GoalService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        sum_meters=None,  # SQL SUM of empty set returns NULL
    )
    with patch("backend.goals.goals_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 0.0
    assert result.progress_pct == 0.0
    assert result.on_pace is False


async def test_get_personal_dashboard_on_pace_true_when_ahead():
    # 200 km done, expected = 157.0 km → on pace
    # progress_pct = round(200/365*100, 2) = 54.79
    svc = GoalService()
    sync = _make_sync_state()
    db = _make_db_for_dashboard(
        sync_state=sync,
        goal=_make_goal(365.0),
        sum_meters=Decimal("200000"),
    )
    with patch("backend.goals.goals_service.datetime") as mock_dt:
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
    svc = GoalService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        sum_meters=Decimal("142500"),
    )
    with patch("backend.goals.goals_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 142.5
    assert result.progress_pct == 39.04
    assert result.on_pace is False
    assert result.expected_pct == 43.01
```

- [ ] **Step 2: Run the tests to confirm they fail**

```
uv run pytest tests/backend/goals/test_goal_service.py -k "dashboard" -v
```

Expected: `AttributeError: 'GoalService' object has no attribute 'get_personal_dashboard'`

- [ ] **Step 3: Implement `get_personal_dashboard`**

Replace the full content of `backend/goals/goals_service.py` with:

```python
import calendar
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.goals.schemas import PersonalDashboardResponse
from backend.shared.models import Activity, Goal, SyncState


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

- [ ] **Step 4: Run the dashboard tests to confirm they pass**

```
uv run pytest tests/backend/goals/test_goal_service.py -k "dashboard" -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Run the full goals service test suite to confirm no regressions**

```
uv run pytest tests/backend/goals/test_goal_service.py -v
```

Expected: all tests PASSED

- [ ] **Step 6: Commit**

```
git add backend/goals/goals_service.py tests/backend/goals/test_goal_service.py
git commit -m "feat(goals): add get_personal_dashboard to GoalService"
```

---

## Task 3: Add `GET /dashboard/personal` route

**Files:**
- Modify: `backend/goals/router.py`
- Test: `tests/backend/goals/test_goals_router.py`

- [ ] **Step 1: Write the failing router tests**

Add the following to the bottom of `tests/backend/goals/test_goals_router.py`:

```python
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
    from backend.dependencies import get_goal_service
    from backend.goals.schemas import PersonalDashboardResponse
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
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
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
        app.dependency_overrides.pop(get_goal_service, None)


def test_get_personal_dashboard_returns_404_when_not_synced():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_personal_dashboard = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="not_synced")
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
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
        app.dependency_overrides.pop(get_goal_service, None)
```

Also add `from unittest.mock import patch` to the imports at the top of `test_goals_router.py` if not already present.

- [ ] **Step 2: Run the new tests to confirm they fail**

```
uv run pytest tests/backend/goals/test_goals_router.py -k "personal_dashboard" -v
```

Expected: 3 tests FAILED with `404 Not Found` (route doesn't exist yet)

- [ ] **Step 3: Add the route**

Replace the full content of `backend/goals/router.py` with:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_goal_service
from backend.goals.goals_service import GoalService
from backend.goals.schemas import GoalResponse, PersonalDashboardResponse, UpdateGoalRequest
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


@router.get("/dashboard/personal", response_model=PersonalDashboardResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_personal_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> PersonalDashboardResponse:
    return await goal_service.get_personal_dashboard(db, current_user.id)
```

- [ ] **Step 4: Run the new router tests to confirm they pass**

```
uv run pytest tests/backend/goals/test_goals_router.py -k "personal_dashboard" -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Run the full goals router test suite to confirm no regressions**

```
uv run pytest tests/backend/goals/test_goals_router.py -v
```

Expected: all tests PASSED

- [ ] **Step 6: Run the full test suite**

```
uv run pytest tests/ -v
```

Expected: all tests PASSED

- [ ] **Step 7: Run CI checks**

```
make ci
```

Expected: all checks pass (lint, format, typecheck)

- [ ] **Step 8: Commit**

```
git add backend/goals/router.py tests/backend/goals/test_goals_router.py
git commit -m "feat(goals): add GET /dashboard/personal endpoint"
```

---

## Done

After all three tasks and commits, `GET /dashboard/personal` is live. Mark TASK-5.3 as `✅` in `docs/epics/backlog.md`.
