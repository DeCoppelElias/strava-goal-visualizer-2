# TASK-5.1 Goals Database Schema — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `goals` table and `Goal` ORM model, auto-create a default 365 km goal row for every new user on first OAuth login.

**Architecture:** Add `Goal` to `backend/shared/models.py` following the `SyncState` pattern (user_id as PK). Create hand-written Alembic migration `0003_create_goals_table.py`. Extend `_upsert_user` in `strava_oauth_service.py` to `db.add(Goal(...))` immediately after flushing the new `User` row.

**Tech Stack:** SQLAlchemy async ORM, Alembic, PostgreSQL, pytest + pytest-asyncio.

---

## File Map

| Action | Path |
|---|---|
| Modify | `backend/shared/models.py` |
| Create | `backend/db/migrations/versions/0003_create_goals_table.py` |
| Modify | `backend/auth/strava_oauth_service.py` |
| Create | `tests/backend/shared/test_goals_model.py` |
| Modify | `tests/backend/auth/test_strava_oauth_service.py` |

---

## Task 1: Goal ORM model

**Files:**
- Modify: `backend/shared/models.py`
- Create: `tests/backend/shared/test_goals_model.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/shared/test_goals_model.py`:

```python
from decimal import Decimal

import pytest
from sqlalchemy import CheckConstraint, inspect as sa_inspect

from backend.shared.models import Goal, User


def test_goal_default_yearly_running_goal_km_is_365():
    goal = Goal(user_id=1)
    assert goal.yearly_running_goal_km == Decimal("365")


def test_goal_user_id_is_primary_key():
    pk_cols = {c.key for c in Goal.__table__.primary_key.columns}
    assert pk_cols == {"user_id"}


def test_goal_has_check_constraint_on_yearly_running_goal_km():
    constraints = [c for c in Goal.__table__.constraints if isinstance(c, CheckConstraint)]
    assert len(constraints) == 1
    assert "yearly_running_goal_km" in str(constraints[0].sqltext)


def test_goal_updated_at_is_timezone_aware():
    assert sa_inspect(Goal).columns["updated_at"].type.timezone is True


def test_user_has_goal_relationship():
    assert hasattr(User, "goal")
```

- [ ] **Step 2: Run tests to confirm they fail**

```
uv run pytest tests/backend/shared/test_goals_model.py -v
```

Expected: all 5 tests fail with `ImportError: cannot import name 'Goal'`.

- [ ] **Step 3: Add the Goal model to `backend/shared/models.py`**

Add `CheckConstraint` to the existing SQLAlchemy import line (line 5):

```python
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, Text, UniqueConstraint
```

Add the `Goal` class at the end of the file:

```python
class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("yearly_running_goal_km > 0 AND yearly_running_goal_km <= 100000"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    yearly_running_goal_km: Mapped[Decimal] = mapped_column(Numeric, default=Decimal("365"))
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="goal")
```

Add the `goal` relationship to the existing `User` class (after the `sync_state` relationship on line 28):

```python
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="user", uselist=False)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
uv run pytest tests/backend/shared/test_goals_model.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Run full suite to confirm no regressions**

```
uv run pytest tests/ -v
```

Expected: all existing tests continue to pass.

- [ ] **Step 6: Commit**

```
git add backend/shared/models.py tests/backend/shared/test_goals_model.py
git commit -m "feat(goals): add Goal ORM model with check constraint"
```

---

## Task 2: Alembic migration

**Files:**
- Create: `backend/db/migrations/versions/0003_create_goals_table.py`

- [ ] **Step 1: Create the migration file**

Create `backend/db/migrations/versions/0003_create_goals_table.py`:

```python
"""create goals table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "yearly_running_goal_km",
            sa.Numeric(),
            nullable=False,
            server_default="365",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "yearly_running_goal_km > 0 AND yearly_running_goal_km <= 100000",
            name="ck_goals_yearly_running_goal_km",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("goals")
```

- [ ] **Step 2: Apply the migration**

Requires Docker DB running (`docker compose up db -d`):

```
uv run alembic upgrade head
```

Expected output ends with: `Running upgrade 0002 -> 0003, create goals table`

- [ ] **Step 3: Verify the table in psql**

```
docker compose exec db psql -U postgres -d postgres -c "\d goals"
```

Expected: table with columns `user_id`, `yearly_running_goal_km`, `updated_at` and a check constraint.

- [ ] **Step 4: Verify downgrade works**

```
uv run alembic downgrade -1
uv run alembic upgrade head
```

Expected: both commands complete without error.

- [ ] **Step 5: Commit**

```
git add backend/db/migrations/versions/0003_create_goals_table.py
git commit -m "feat(goals): add goals table migration (0003)"
```

---

## Task 3: Auto-create Goal on first login

**Files:**
- Modify: `backend/auth/strava_oauth_service.py`
- Modify: `tests/backend/auth/test_strava_oauth_service.py`

- [ ] **Step 1: Write failing tests**

Add the following two tests to `tests/backend/auth/test_strava_oauth_service.py` (after the existing `test_process_callback_creates_new_user_on_first_login` test, around line 200):

```python
@pytest.mark.asyncio
async def test_upsert_user_creates_default_goal_for_new_user(mock_settings, mock_crypto):
    from decimal import Decimal
    from backend.shared.models import Goal

    db = AsyncMock()
    db.add = MagicMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None  # new user
    db.execute.return_value = user_result

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    await service._upsert_user(db, strava_athlete_id=42)

    goal_calls = [c for c in db.add.call_args_list if isinstance(c.args[0], Goal)]
    assert len(goal_calls) == 1
    assert goal_calls[0].args[0].yearly_running_goal_km == Decimal("365")


@pytest.mark.asyncio
async def test_upsert_user_does_not_create_goal_for_existing_user(mock_settings, mock_crypto):
    from backend.shared.models import Goal, User

    existing_user = MagicMock(spec=User)
    existing_user.id = 5

    db = AsyncMock()
    db.add = MagicMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = existing_user
    db.execute.return_value = user_result

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    await service._upsert_user(db, strava_athlete_id=42)

    goal_calls = [c for c in db.add.call_args_list if isinstance(c.args[0], Goal)]
    assert len(goal_calls) == 0
```

- [ ] **Step 2: Run new tests to confirm they fail**

```
uv run pytest tests/backend/auth/test_strava_oauth_service.py::test_upsert_user_creates_default_goal_for_new_user tests/backend/auth/test_strava_oauth_service.py::test_upsert_user_does_not_create_goal_for_existing_user -v
```

Expected: `test_upsert_user_creates_default_goal_for_new_user` fails (no Goal added); `test_upsert_user_does_not_create_goal_for_existing_user` passes (it already doesn't add a Goal).

- [ ] **Step 3: Update the import in `backend/auth/strava_oauth_service.py`**

Change line 19 from:

```python
from backend.shared.models import OAuthCredentials, User
```

To:

```python
from backend.shared.models import Goal, OAuthCredentials, User
```

- [ ] **Step 4: Update `_upsert_user` in `backend/auth/strava_oauth_service.py`**

Change `_upsert_user` (lines 88–97) from:

```python
    async def _upsert_user(self, db: AsyncSession, strava_athlete_id: int) -> User:
        result = await db.execute(select(User).where(User.strava_athlete_id == strava_athlete_id))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(strava_athlete_id=strava_athlete_id)
            db.add(user)
            await db.flush()

        return user
```

To:

```python
    async def _upsert_user(self, db: AsyncSession, strava_athlete_id: int) -> User:
        result = await db.execute(select(User).where(User.strava_athlete_id == strava_athlete_id))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(strava_athlete_id=strava_athlete_id)
            db.add(user)
            await db.flush()
            db.add(Goal(user_id=user.id))

        return user
```

- [ ] **Step 5: Run all auth service tests**

```
uv run pytest tests/backend/auth/test_strava_oauth_service.py -v
```

Expected: all tests pass including the two new ones.

- [ ] **Step 6: Run full suite**

```
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
git add backend/auth/strava_oauth_service.py tests/backend/auth/test_strava_oauth_service.py
git commit -m "feat(goals): auto-create default goal row on first user login"
```
