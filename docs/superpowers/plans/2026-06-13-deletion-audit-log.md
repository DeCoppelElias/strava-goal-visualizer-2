# TASK-7.1 — Deletion Audit Log Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `DeletionEvent` ORM model and `DeletionReason` enum to the shared models, then write and verify the Alembic migration that creates the `deletion_events` table.

**Architecture:** `DeletionReason` is a `str`+`enum.Enum` so values compare equal to their string literals — no conversion needed when writing to the `Text` DB column. `DeletionEvent` has no FK on `user_id` so rows survive after the `users` row is deleted. The test harness calls `Base.metadata.create_all` automatically, so the integration test does not need to run migrations.

**Tech Stack:** SQLAlchemy 2.0 async ORM, Alembic, pytest + pytest-asyncio, testcontainers (via existing `db` fixture in `tests/conftest.py`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/shared/models.py` | Add `DeletionReason` enum + `DeletionEvent` model |
| Create | `backend/db/migrations/versions/0006_create_deletion_events.py` | Alembic migration |
| Create | `tests/backend/shared/__init__.py` | Make test package discoverable |
| Create | `tests/backend/shared/test_deletion_event_model.py` | Integration test for model insert/read |

---

## Task 1: Add `DeletionReason` and `DeletionEvent` to models

**Files:**
- Modify: `backend/shared/models.py`
- Create: `tests/backend/shared/__init__.py`
- Create: `tests/backend/shared/test_deletion_event_model.py`

- [ ] **Step 1: Create the test package**

```bash
# Windows PowerShell
New-Item -ItemType File -Path "tests/backend/shared/__init__.py" -Force
```

Or simply create an empty file at `tests/backend/shared/__init__.py`.

- [ ] **Step 2: Write the failing integration test**

Create `tests/backend/shared/test_deletion_event_model.py`:

```python
import pytest
from sqlalchemy import select

from backend.shared.models import DeletionEvent, DeletionReason


@pytest.mark.asyncio
async def test_deletion_event_insert_and_read(db):
    event = DeletionEvent(
        user_id=12345678,
        reason=DeletionReason.USER_INITIATED,
    )
    db.add(event)
    await db.flush()

    result = await db.execute(select(DeletionEvent).where(DeletionEvent.id == event.id))
    row = result.scalar_one()

    assert row.user_id == 12345678
    assert row.reason == "user_initiated"
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_deletion_event_strava_deauth_reason(db):
    event = DeletionEvent(
        user_id=99999999,
        reason=DeletionReason.STRAVA_DEAUTH,
    )
    db.add(event)
    await db.flush()

    result = await db.execute(select(DeletionEvent).where(DeletionEvent.id == event.id))
    row = result.scalar_one()

    assert row.reason == "strava_deauth"


def test_deletion_reason_enum_string_equality():
    assert DeletionReason.USER_INITIATED == "user_initiated"
    assert DeletionReason.STRAVA_DEAUTH == "strava_deauth"
```

- [ ] **Step 3: Run the test — expect ImportError (model not defined yet)**

```bash
uv run pytest tests/backend/shared/test_deletion_event_model.py -v
```

Expected: **FAIL** — `ImportError: cannot import name 'DeletionEvent' from 'backend.shared.models'`

- [ ] **Step 4: Add `import enum` to `backend/shared/models.py`**

At the top of `backend/shared/models.py`, add `import enum` after the existing stdlib imports:

```python
import enum
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional
```

- [ ] **Step 5: Add `DeletionReason` and `DeletionEvent` to `backend/shared/models.py`**

Append to the end of `backend/shared/models.py`:

```python
class DeletionReason(str, enum.Enum):
    USER_INITIATED = "user_initiated"
    STRAVA_DEAUTH = "strava_deauth"


class DeletionEvent(Base):
    __tablename__ = "deletion_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    deleted_at: Mapped[datetime] = mapped_column(_tz, default=_now)
```

Note: no FK on `user_id` — it stores the Strava athlete ID as a plain `BigInteger` so the row is preserved after the `users` row is deleted.

- [ ] **Step 6: Run the tests — expect PASS**

```bash
uv run pytest tests/backend/shared/test_deletion_event_model.py -v
```

Expected output:
```
tests/backend/shared/test_deletion_event_model.py::test_deletion_event_insert_and_read PASSED
tests/backend/shared/test_deletion_event_model.py::test_deletion_event_strava_deauth_reason PASSED
tests/backend/shared/test_deletion_event_model.py::test_deletion_reason_enum_string_equality PASSED
3 passed
```

- [ ] **Step 7: Run the full suite to check for regressions**

```bash
uv run pytest tests/ -x -q
```

Expected: all tests pass, no failures.

- [ ] **Step 8: Commit**

```bash
git add backend/shared/models.py tests/backend/shared/__init__.py tests/backend/shared/test_deletion_event_model.py
git commit -m "feat(privacy): add DeletionEvent model and DeletionReason enum"
```

---

## Task 2: Write and verify the Alembic migration

**Files:**
- Create: `backend/db/migrations/versions/0006_create_deletion_events.py`

- [ ] **Step 1: Create the migration file**

Create `backend/db/migrations/versions/0006_create_deletion_events.py`:

```python
"""create deletion_events table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-13

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("deletion_events")
```

- [ ] **Step 2: Start the database (if not already running)**

```bash
docker compose up db -d
```

Wait a few seconds for Postgres to be ready.

- [ ] **Step 3: Apply the migration**

```bash
uv run alembic upgrade head
```

Expected output ends with:
```
Running upgrade 0005 -> 0006, create deletion_events table
```

- [ ] **Step 4: Verify the table exists**

```bash
docker compose exec db psql -U postgres -d postgres -c "\d deletion_events"
```

Expected output:
```
             Table "public.deletion_events"
   Column    |           Type           | Nullable
-------------+--------------------------+----------
 id          | integer                  | not null
 user_id     | bigint                   | not null
 reason      | text                     | not null
 deleted_at  | timestamp with time zone | not null
Indexes:
    "deletion_events_pkey" PRIMARY KEY, btree (id)
```

- [ ] **Step 5: Test the downgrade**

```bash
uv run alembic downgrade -1
```

Expected output:
```
Running downgrade 0006 -> 0005, create deletion_events table
```

- [ ] **Step 6: Re-apply the migration**

```bash
uv run alembic upgrade head
```

Expected: migration applies cleanly again.

- [ ] **Step 7: Commit**

```bash
git add backend/db/migrations/versions/0006_create_deletion_events.py
git commit -m "chore(db): add migration 0006 for deletion_events table"
```

---

## Done

Mark TASK-7.1 as `✅` in `docs/epics/backlog.md`.
