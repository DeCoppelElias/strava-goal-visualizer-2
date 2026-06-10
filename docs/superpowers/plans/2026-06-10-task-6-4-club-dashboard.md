# TASK-6.4 Club Dashboard Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `GET /dashboard/club/{club_id}` returning per-member running progress for all app-authorised members of a club, visible only to club members.

**Architecture:** `DashboardService.get_club_dashboard()` handles all progress computation in 4 queries (membership check, club fetch, member aggregate, goal fetch). The `User` model gains a `display_name` column (firstname + last initial) populated at OAuth time. Route and schemas live in the existing `dashboard` domain.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Alembic, pytest + testcontainers

---

## File Map

| Action | Path |
|--------|------|
| Modify | `backend/shared/models.py` |
| Create | `backend/db/migrations/versions/0005_add_user_display_name.py` |
| Modify | `backend/auth/strava_oauth_service.py` |
| Modify | `tests/backend/auth/test_strava_oauth_service.py` |
| Modify | `backend/dashboard/schemas.py` |
| Modify | `backend/dashboard/dashboard_service.py` |
| Create | `tests/backend/dashboard/test_club_dashboard_service.py` |
| Modify | `backend/dashboard/router.py` |
| Create | `tests/backend/dashboard/test_club_dashboard_router.py` |
| Modify | `docs/epics/backlog.md` |
| Modify | `docs/design.md` |

---

## Task 1: Add `display_name` to User model and create migration

**Files:**
- Modify: `backend/shared/models.py`
- Create: `backend/db/migrations/versions/0005_add_user_display_name.py`

- [ ] **Step 1: Add `display_name` column to the `User` model**

In `backend/shared/models.py`, add one line to the `User` class (after `strava_athlete_id`):

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    strava_athlete_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    display_name: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(_tz, default=_now)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)
    # ... relationships unchanged
```

- [ ] **Step 2: Create the Alembic migration**

Create `backend/db/migrations/versions/0005_add_user_display_name.py` with this exact content:

```python
"""add display_name to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-10

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "display_name")
```

- [ ] **Step 3: Apply the migration**

```bash
docker compose up db -d
uv run alembic upgrade head
```

Expected output ends with: `Running upgrade 0004 -> 0005, add display_name to users`

- [ ] **Step 4: Commit**

```bash
git add backend/shared/models.py backend/db/migrations/versions/0005_add_user_display_name.py
git commit -m "feat(auth): add display_name column to users table"
```

---

## Task 2: Update `_upsert_user` to populate `display_name`

**Files:**
- Modify: `backend/auth/strava_oauth_service.py`
- Modify: `tests/backend/auth/test_strava_oauth_service.py`

- [ ] **Step 1: Write new failing tests and update existing `_upsert_user` tests**

In `tests/backend/auth/test_strava_oauth_service.py`:

1. Update `_VALID_STRAVA_TOKEN_RESPONSE` to include athlete name fields (the existing tests still pass; new tests need them):

```python
_VALID_STRAVA_TOKEN_RESPONSE = {
    "access_token": "access_abc",
    "refresh_token": "refresh_xyz",
    "expires_at": 9999999999,
    "athlete": {"id": 11111111, "firstname": "Test", "lastname": "User"},
    "scope": "activity:read_all,profile:read_all",
}
```

2. Update the two existing tests that call `_upsert_user` with the old `strava_athlete_id=` keyword — they will break when the signature changes:

```python
# test_upsert_user_creates_default_goal_for_new_user  (line ~203)
# Change the call from:
#   await service._upsert_user(db, strava_athlete_id=42)
# to:
    await service._upsert_user(db, athlete={"id": 42})

# test_upsert_user_does_not_create_goal_for_existing_user  (line ~224)
# Change the call from:
#   await service._upsert_user(db, strava_athlete_id=42)
# to:
    await service._upsert_user(db, athlete={"id": 42})
```

3. Append the three new tests at the end of the file:

```python
@pytest.mark.asyncio
async def test_upsert_user_sets_display_name_from_firstname_and_last_initial(
    mock_settings, mock_crypto
):
    db = AsyncMock()
    db.add = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    db.execute.return_value = user_result

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    user = await service._upsert_user(
        db, athlete={"id": 42, "firstname": "Elias", "lastname": "De Coppel"}
    )

    assert user.display_name == "Elias D."


@pytest.mark.asyncio
async def test_upsert_user_sets_display_name_without_initial_when_no_lastname(
    mock_settings, mock_crypto
):
    db = AsyncMock()
    db.add = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    db.execute.return_value = user_result

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    user = await service._upsert_user(
        db, athlete={"id": 42, "firstname": "Elias", "lastname": ""}
    )

    assert user.display_name == "Elias"


@pytest.mark.asyncio
async def test_upsert_user_updates_display_name_on_relogin(mock_settings, mock_crypto):
    from backend.shared.models import User as UserModel

    existing_user = MagicMock(spec=UserModel)
    existing_user.id = 5
    existing_user.strava_athlete_id = 42

    db = AsyncMock()
    db.add = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = existing_user
    db.execute.return_value = user_result

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    user = await service._upsert_user(
        db, athlete={"id": 42, "firstname": "New", "lastname": "Name"}
    )

    assert user.display_name == "New N."
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
uv run pytest tests/backend/auth/test_strava_oauth_service.py -v
```

Expected: multiple FAILs — the two updated calls use the wrong signature, and the three new tests call a method that doesn't exist yet.

- [ ] **Step 3: Implement the changes in `strava_oauth_service.py`**

Replace `_upsert_user` with:

```python
async def _upsert_user(self, db: AsyncSession, athlete: dict[str, Any]) -> User:
    strava_athlete_id: int = athlete["id"]
    firstname = athlete.get("firstname", "")
    lastname = athlete.get("lastname", "")
    last_initial = f" {lastname[0]}." if lastname else ""
    display_name = f"{firstname}{last_initial}".strip()

    result = await db.execute(select(User).where(User.strava_athlete_id == strava_athlete_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(strava_athlete_id=strava_athlete_id, display_name=display_name)
        db.add(user)
        await db.flush()
        db.add(Goal(user_id=user.id, yearly_running_goal_km=Decimal("365")))
    else:
        user.display_name = display_name

    return user
```

Replace the two lines in `process_callback` that call `_upsert_user`:

```python
# Remove:
#   athlete_id: int = token_data["athlete"]["id"]
#   user = await self._upsert_user(db, athlete_id)
# Replace with:
    user = await self._upsert_user(db, token_data["athlete"])
```

- [ ] **Step 4: Run tests to confirm all pass**

```bash
uv run pytest tests/backend/auth/test_strava_oauth_service.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/auth/strava_oauth_service.py tests/backend/auth/test_strava_oauth_service.py
git commit -m "feat(auth): populate display_name from Strava athlete data on login"
```

---

## Task 3: Add new dashboard schemas

**Files:**
- Modify: `backend/dashboard/schemas.py`

- [ ] **Step 1: Add `MemberProgressResponse` and `ClubDashboardResponse`**

Replace the full contents of `backend/dashboard/schemas.py` with:

```python
from datetime import datetime

from pydantic import BaseModel


class DailyDistancePoint(BaseModel):
    date: str  # YYYY-MM-DD
    cumulative_km: float


class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
    daily_series: list[DailyDistancePoint]


class MemberProgressResponse(BaseModel):
    strava_athlete_id: int
    display_name: str
    distance_to_date_km: float
    goal_km: float
    progress_pct: float


class ClubDashboardResponse(BaseModel):
    club_id: int
    club_name: str
    members: list[MemberProgressResponse]
```

- [ ] **Step 2: Commit**

```bash
git add backend/dashboard/schemas.py
git commit -m "feat(dashboard): add MemberProgressResponse and ClubDashboardResponse schemas"
```

---

## Task 4: Implement `get_club_dashboard` service method (TDD)

**Files:**
- Create: `tests/backend/dashboard/test_club_dashboard_service.py`
- Modify: `backend/dashboard/dashboard_service.py`

- [ ] **Step 1: Create the integration test file**

Create `tests/backend/dashboard/test_club_dashboard_service.py`:

```python
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.dashboard_service import DashboardService
from backend.shared.models import Activity, Club, ClubMembership, Goal, User


async def _seed_user(db: AsyncSession, strava_athlete_id: int, display_name: str = "") -> User:
    user = User(strava_athlete_id=strava_athlete_id, display_name=display_name)
    db.add(user)
    await db.flush()
    return user


async def _seed_club(db: AsyncSession, club_id: int, name: str) -> Club:
    club = Club(id=club_id, name=name, updated_at=datetime.now(UTC))
    db.add(club)
    await db.flush()
    return club


async def _seed_membership(db: AsyncSession, user_id: int, club_id: int) -> ClubMembership:
    membership = ClubMembership(user_id=user_id, club_id=club_id, synced_at=datetime.now(UTC))
    db.add(membership)
    await db.flush()
    return membership


async def _seed_goal(db: AsyncSession, user_id: int, yearly_km: float) -> Goal:
    goal = Goal(user_id=user_id, yearly_running_goal_km=Decimal(str(yearly_km)))
    db.add(goal)
    await db.flush()
    return goal


_counter = 0


async def _seed_activity(
    db: AsyncSession, user_id: int, distance_meters: float, start_date: datetime
) -> Activity:
    global _counter
    _counter += 1
    activity = Activity(
        user_id=user_id,
        strava_activity_id=_counter,
        name="Morning Run",
        sport_type="Run",
        distance_meters=Decimal(str(distance_meters)),
        moving_time_seconds=3600,
        start_date=start_date,
    )
    db.add(activity)
    await db.flush()
    return activity


async def test_get_club_dashboard_returns_progress_for_all_members(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=1, name="Road Runners")
    user_a = await _seed_user(db, strava_athlete_id=100, display_name="Alice A.")
    user_b = await _seed_user(db, strava_athlete_id=200, display_name="Bob B.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    await _seed_goal(db, user_b.id, yearly_km=200.0)
    this_year = datetime(datetime.now(UTC).year, 3, 1, tzinfo=UTC)
    await _seed_activity(db, user_a.id, distance_meters=10_000, start_date=this_year)
    await _seed_activity(db, user_b.id, distance_meters=20_000, start_date=this_year)

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    assert result.club_id == club.id
    assert result.club_name == "Road Runners"
    assert len(result.members) == 2
    by_athlete = {m.strava_athlete_id: m for m in result.members}
    assert by_athlete[100].distance_to_date_km == 10.0
    assert by_athlete[100].goal_km == 100.0
    assert by_athlete[100].progress_pct == 10.0
    assert by_athlete[100].display_name == "Alice A."
    assert by_athlete[200].distance_to_date_km == 20.0
    assert by_athlete[200].goal_km == 200.0
    assert by_athlete[200].progress_pct == 10.0
    assert by_athlete[200].display_name == "Bob B."


async def test_get_club_dashboard_raises_403_if_requesting_user_not_a_member(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=2, name="Trail Blazers")
    user = await _seed_user(db, strava_athlete_id=300)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert exc_info.value.status_code == 403


async def test_get_club_dashboard_excludes_members_without_goal(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=3, name="Sprinters")
    user_a = await _seed_user(db, strava_athlete_id=400, display_name="Alice A.")
    user_b = await _seed_user(db, strava_athlete_id=500, display_name="Bob B.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    # user_b intentionally has no goal

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    assert len(result.members) == 1
    assert result.members[0].strava_athlete_id == 400


async def test_get_club_dashboard_includes_member_with_goal_but_no_activities(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=4, name="Beginners")
    user = await _seed_user(db, strava_athlete_id=600, display_name="Carol C.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert len(result.members) == 1
    assert result.members[0].distance_to_date_km == 0.0
    assert result.members[0].progress_pct == 0.0


async def test_get_club_dashboard_ignores_previous_year_activities(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=5, name="Marathoners")
    user = await _seed_user(db, strava_athlete_id=700, display_name="Dave D.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)
    last_year = datetime(datetime.now(UTC).year - 1, 6, 1, tzinfo=UTC)
    await _seed_activity(db, user.id, distance_meters=50_000, start_date=last_year)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert result.members[0].distance_to_date_km == 0.0


async def test_get_club_dashboard_raises_403_for_club_user_is_not_in(db: AsyncSession) -> None:
    svc = DashboardService()
    club_a = await _seed_club(db, club_id=6, name="Club A")
    club_b = await _seed_club(db, club_id=7, name="Club B")
    user = await _seed_user(db, strava_athlete_id=800)
    await _seed_membership(db, user.id, club_a.id)
    # user is in club_a but NOT club_b

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club_b.id)

    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/backend/dashboard/test_club_dashboard_service.py -v
```

Expected: all FAIL with `AttributeError: 'DashboardService' object has no attribute 'get_club_dashboard'`

- [ ] **Step 3: Implement `get_club_dashboard` in `dashboard_service.py`**

The full updated `backend/dashboard/dashboard_service.py`:

```python
import calendar
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.schemas import (
    ClubDashboardResponse,
    DailyDistancePoint,
    MemberProgressResponse,
    PersonalDashboardResponse,
)
from backend.shared.models import Activity, Club, ClubMembership, Goal, SyncState, User


class DashboardService:
    async def get_personal_dashboard(
        self, db: AsyncSession, user_id: int
    ) -> PersonalDashboardResponse:
        sync_result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        sync_state = sync_result.scalar_one_or_none()
        if sync_state is None:
            raise HTTPException(status_code=404, detail="not_synced")

        goal_result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = goal_result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")

        now = datetime.now(UTC)
        year_start = datetime(now.year, 1, 1, tzinfo=UTC)

        activities_result = await db.execute(
            select(Activity.start_date, Activity.distance_meters)
            .where(
                Activity.user_id == user_id,
                Activity.start_date >= year_start,
            )
            .order_by(Activity.start_date.asc())
        )
        rows = activities_result.all()

        daily_totals: dict[str, float] = defaultdict(float)
        for row in rows:
            date_str = row.start_date.date().isoformat()
            daily_totals[date_str] += float(row.distance_meters)

        daily_series: list[DailyDistancePoint] = []
        cumulative = 0.0
        for date_str, day_meters in daily_totals.items():
            cumulative += day_meters / 1000
            daily_series.append(
                DailyDistancePoint(date=date_str, cumulative_km=round(cumulative, 3))
            )

        sum_meters = sum(float(r.distance_meters) for r in rows)
        goal_km = float(goal.yearly_running_goal_km)
        distance_to_date_km = sum_meters / 1000
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
            daily_series=daily_series,
        )

    async def get_club_dashboard(
        self, db: AsyncSession, requesting_user_id: int, club_id: int
    ) -> ClubDashboardResponse:
        membership_result = await db.execute(
            select(ClubMembership).where(
                ClubMembership.user_id == requesting_user_id,
                ClubMembership.club_id == club_id,
            )
        )
        if membership_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="not_a_member")

        club_result = await db.execute(select(Club).where(Club.id == club_id))
        club = club_result.scalar_one_or_none()
        if club is None:
            raise HTTPException(status_code=404, detail="club_not_found")

        members_result = await db.execute(
            select(User)
            .join(ClubMembership, ClubMembership.user_id == User.id)
            .where(ClubMembership.club_id == club_id)
        )
        members = list(members_result.scalars().all())
        member_ids = [m.id for m in members]

        if not member_ids:
            return ClubDashboardResponse(club_id=club.id, club_name=club.name, members=[])

        now = datetime.now(UTC)
        year_start = datetime(now.year, 1, 1, tzinfo=UTC)

        activity_result = await db.execute(
            select(
                Activity.user_id,
                func.sum(Activity.distance_meters).label("total_meters"),
            )
            .where(
                Activity.user_id.in_(member_ids),
                Activity.start_date >= year_start,
            )
            .group_by(Activity.user_id)
        )
        distance_by_user: dict[int, float] = {
            row.user_id: float(row.total_meters) for row in activity_result.all()
        }

        goals_result = await db.execute(select(Goal).where(Goal.user_id.in_(member_ids)))
        goal_by_user: dict[int, Goal] = {g.user_id: g for g in goals_result.scalars().all()}

        progress_list: list[MemberProgressResponse] = []
        for member in members:
            goal = goal_by_user.get(member.id)
            if goal is None:
                continue
            goal_km = float(goal.yearly_running_goal_km)
            distance_km = distance_by_user.get(member.id, 0.0) / 1000
            progress_pct = round(distance_km / goal_km * 100, 2)
            progress_list.append(
                MemberProgressResponse(
                    strava_athlete_id=member.strava_athlete_id,
                    display_name=member.display_name,
                    distance_to_date_km=distance_km,
                    goal_km=goal_km,
                    progress_pct=progress_pct,
                )
            )

        return ClubDashboardResponse(
            club_id=club.id,
            club_name=club.name,
            members=progress_list,
        )
```

- [ ] **Step 4: Run tests to confirm all pass**

```bash
uv run pytest tests/backend/dashboard/test_club_dashboard_service.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/dashboard/dashboard_service.py tests/backend/dashboard/test_club_dashboard_service.py
git commit -m "feat(dashboard): implement DashboardService.get_club_dashboard"
```

---

## Task 5: Add route and router tests

**Files:**
- Modify: `backend/dashboard/router.py`
- Create: `tests/backend/dashboard/test_club_dashboard_router.py`

- [ ] **Step 1: Create the router test file**

Create `tests/backend/dashboard/test_club_dashboard_router.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.dashboard.schemas import ClubDashboardResponse, MemberProgressResponse
from backend.shared.models import User


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
    return User(id=1, strava_athlete_id=99999, display_name="Test T.")


def test_get_club_dashboard_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/club/1")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_club_dashboard_returns_403_for_non_member():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_club_dashboard = AsyncMock(
        side_effect=HTTPException(status_code=403, detail="not_a_member")
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/club/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)


def test_get_club_dashboard_returns_200_with_club_progress():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_club_dashboard = AsyncMock(
        return_value=ClubDashboardResponse(
            club_id=42,
            club_name="Road Runners",
            members=[
                MemberProgressResponse(
                    strava_athlete_id=100,
                    display_name="Alice A.",
                    distance_to_date_km=10.0,
                    goal_km=100.0,
                    progress_pct=10.0,
                )
            ],
        )
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/dashboard/club/42")
        assert response.status_code == 200
        data = response.json()
        assert data["club_id"] == 42
        assert data["club_name"] == "Road Runners"
        assert len(data["members"]) == 1
        assert data["members"][0]["strava_athlete_id"] == 100
        assert data["members"][0]["display_name"] == "Alice A."
        assert data["members"][0]["distance_to_date_km"] == 10.0
        assert data["members"][0]["goal_km"] == 100.0
        assert data["members"][0]["progress_pct"] == 10.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/backend/dashboard/test_club_dashboard_router.py -v
```

Expected: FAILs with 404 (route doesn't exist yet)

- [ ] **Step 3: Add the endpoint to `backend/dashboard/router.py`**

Full updated file:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dashboard.dashboard_service import DashboardService
from backend.dashboard.schemas import ClubDashboardResponse, PersonalDashboardResponse
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


@router.get("/dashboard/club/{club_id}", response_model=ClubDashboardResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_club_dashboard(
    request: Request,
    club_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    dashboard_service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> ClubDashboardResponse:
    return await dashboard_service.get_club_dashboard(db, current_user.id, club_id)
```

- [ ] **Step 4: Run tests to confirm all pass**

```bash
uv run pytest tests/backend/dashboard/test_club_dashboard_router.py -v
```

Expected: all PASS

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```bash
uv run pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/dashboard/router.py tests/backend/dashboard/test_club_dashboard_router.py
git commit -m "feat(dashboard): add GET /dashboard/club/{club_id} endpoint"
```

---

## Task 6: Update backlog and design doc

**Files:**
- Modify: `docs/epics/backlog.md`
- Modify: `docs/design.md`

- [ ] **Step 1: Update TASK-6.4 in `docs/epics/backlog.md`**

Find the `#### TASK-6.4` section and update the Output block to reflect the actual implementation:

- URL changed from `GET /clubs/{club_id}/progress` to `GET /dashboard/club/{club_id}`
- Service: `DashboardService.get_club_dashboard()` (not `ClubsService`)
- Schema: `ClubDashboardResponse` with `club_id`, `club_name`, `members: list[MemberProgressResponse]`
- `MemberProgressResponse` now includes `display_name: str`
- Mark the task as `✅`: `#### TASK-6.4 ✅`

- [ ] **Step 2: Update `docs/design.md`**

In the rate-limit table (§6.0.3), update:
```
| `GET /clubs/{club_id}/progress` | 30/minute | |
```
to:
```
| `GET /dashboard/club/{club_id}` | 30/minute | |
```

In the authorization table, update:
```
| `GET /clubs/{id}/progress` | Authenticated athlete | Must be a member of club `{id}` |
```
to:
```
| `GET /dashboard/club/{club_id}` | Authenticated athlete | Must be a member of club `{club_id}` |
```

- [ ] **Step 3: Commit**

```bash
git add docs/epics/backlog.md docs/design.md
git commit -m "docs: update TASK-6.4 spec to reflect GET /dashboard/club/{club_id} implementation"
```
