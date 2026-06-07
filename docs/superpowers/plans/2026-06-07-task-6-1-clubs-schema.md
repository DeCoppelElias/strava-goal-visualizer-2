# TASK-6.1 — Clubs & Club Memberships Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `clubs` and `club_memberships` PostgreSQL tables with ORM models, bidirectional relationships, and an Alembic migration.

**Architecture:** Two new SQLAlchemy ORM models (`Club`, `ClubMembership`) added to `backend/shared/models.py`. The `User` model gains a `club_memberships` relationship. A single Alembic migration (`0004`) creates both tables and a `club_id` index on `club_memberships`. All timestamp columns use `DateTime(timezone=True)` — no bare `DateTime()`.

**Tech Stack:** SQLAlchemy 2.x (mapped_column / Mapped), Alembic, PostgreSQL, pytest

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Modify | `backend/shared/models.py` | Add `Club`, `ClubMembership` models; add `club_memberships` to `User` |
| Create | `backend/db/migrations/versions/0004_create_clubs_tables.py` | Alembic migration creating both tables and index |
| Create | `tests/backend/shared/test_clubs_models.py` | Unit tests for new models and relationships |
| Modify | `docs/epics/backlog.md` | Mark TASK-5.4 ✅ and TASK-6.1 ✅ |

---

## Task 1: Write failing tests for `Club` and `ClubMembership` models

**Files:**
- Create: `tests/backend/shared/test_clubs_models.py`

- [ ] **Step 1: Create the test file**

```python
# tests/backend/shared/test_clubs_models.py
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import Index
from sqlalchemy import inspect as sa_inspect

from backend.shared.models import Club, ClubMembership, User


def test_club_model_columns():
    club = Club(id=12345, name="Running Club")
    assert club.id == 12345
    assert club.name == "Running Club"


def test_club_id_is_primary_key():
    pk_cols = {c.key for c in Club.__table__.primary_key.columns}
    assert pk_cols == {"id"}


def test_club_id_is_biginteger():
    assert isinstance(Club.__table__.c.id.type, sa.BigInteger)


def test_club_updated_at_is_timezone_aware():
    assert sa_inspect(Club).columns["updated_at"].type.timezone is True


def test_club_has_memberships_relationship():
    assert hasattr(Club, "memberships")


def test_club_membership_model_columns():
    ts = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)
    membership = ClubMembership(user_id=1, club_id=12345, synced_at=ts)
    assert membership.user_id == 1
    assert membership.club_id == 12345
    assert membership.synced_at == ts


def test_club_membership_primary_key_is_composite():
    pk_cols = {c.key for c in ClubMembership.__table__.primary_key.columns}
    assert pk_cols == {"user_id", "club_id"}


def test_club_membership_club_id_is_biginteger():
    assert isinstance(ClubMembership.__table__.c.club_id.type, sa.BigInteger)


def test_club_membership_has_index_on_club_id():
    table_args = ClubMembership.__table_args__
    indexes = [a for a in table_args if isinstance(a, Index)]
    assert len(indexes) == 1
    col_names = {c.key for c in indexes[0].columns}
    assert col_names == {"club_id"}


def test_club_membership_synced_at_is_timezone_aware():
    assert sa_inspect(ClubMembership).columns["synced_at"].type.timezone is True


def test_club_membership_has_user_relationship():
    assert hasattr(ClubMembership, "user")


def test_club_membership_has_club_relationship():
    assert hasattr(ClubMembership, "club")


def test_user_has_club_memberships_relationship():
    assert hasattr(User, "club_memberships")
```

- [ ] **Step 2: Run tests to confirm they fail**

```
uv run pytest tests/backend/shared/test_clubs_models.py -v
```

Expected: `ImportError: cannot import name 'Club' from 'backend.shared.models'`

---

## Task 2: Implement `Club` and `ClubMembership` ORM models

**Files:**
- Modify: `backend/shared/models.py`

- [ ] **Step 1: Add `Club` and `ClubMembership` to models.py, and `club_memberships` to `User`**

In `backend/shared/models.py`:

1. Add `club_memberships` relationship to the existing `User` class (it uses a forward reference so it can go in any order, but add it after the `goal` line):

```python
    club_memberships: Mapped[list["ClubMembership"]] = relationship(back_populates="user")
```

2. Append the two new classes at the end of the file:

```python
class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now)

    memberships: Mapped[list["ClubMembership"]] = relationship(back_populates="club")


class ClubMembership(Base):
    __tablename__ = "club_memberships"
    __table_args__ = (Index("ix_club_memberships_club_id", "club_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    club_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clubs.id"), primary_key=True)
    synced_at: Mapped[datetime] = mapped_column(_tz)

    user: Mapped["User"] = relationship(back_populates="club_memberships")
    club: Mapped["Club"] = relationship(back_populates="memberships")
```

Note: `BigInteger`, `ForeignKey`, `Index`, `Text` are already imported. `_tz` and `_now` are already defined at the top of the file.

- [ ] **Step 2: Run tests to confirm they pass**

```
uv run pytest tests/backend/shared/test_clubs_models.py -v
```

Expected: all 13 tests PASS

- [ ] **Step 3: Run full test suite to confirm no regressions**

```
uv run pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```
git add backend/shared/models.py tests/backend/shared/test_clubs_models.py
git commit -m "feat(clubs): add Club and ClubMembership ORM models"
```

---

## Task 3: Write and verify the Alembic migration

**Files:**
- Create: `backend/db/migrations/versions/0004_create_clubs_tables.py`

- [ ] **Step 1: Create the migration file**

```python
# backend/db/migrations/versions/0004_create_clubs_tables.py
"""create clubs tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clubs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "club_memberships",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.BigInteger(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.PrimaryKeyConstraint("user_id", "club_id"),
    )
    op.create_index(
        "ix_club_memberships_club_id",
        "club_memberships",
        ["club_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_club_memberships_club_id", table_name="club_memberships")
    op.drop_table("club_memberships")
    op.drop_table("clubs")
```

- [ ] **Step 2: Apply the migration against the running database**

Ensure Postgres is running (`docker compose up db -d`), then:

```
uv run alembic upgrade head
```

Expected output ends with: `Running upgrade 0003 -> 0004, create clubs tables`

- [ ] **Step 3: Verify tables exist in the database**

```
docker compose exec db psql -U postgres -d postgres -c "\d clubs"
docker compose exec db psql -U postgres -d postgres -c "\d club_memberships"
```

Expected for `clubs`: columns `id` (bigint PK), `name` (text), `updated_at` (timestamptz)

Expected for `club_memberships`: columns `user_id` (integer, FK), `club_id` (bigint, FK), `synced_at` (timestamptz); composite PK; index `ix_club_memberships_club_id`

- [ ] **Step 4: Verify downgrade and re-upgrade cleanly**

```
uv run alembic downgrade -1
uv run alembic upgrade head
```

Expected: no errors on either command

- [ ] **Step 5: Commit**

```
git add backend/db/migrations/versions/0004_create_clubs_tables.py
git commit -m "feat(clubs): add migration 0004 for clubs and club_memberships tables"
```

---

## Task 4: Mark backlog tasks as complete

**Files:**
- Modify: `docs/epics/backlog.md`

- [ ] **Step 1: Mark TASK-5.4 and TASK-6.1 complete in the backlog**

In `docs/epics/backlog.md`:

- Change `#### TASK-5.4` → `#### TASK-5.4 ✅`
- Change `#### TASK-6.1` → `#### TASK-6.1 ✅`

- [ ] **Step 2: Commit**

```
git add docs/epics/backlog.md
git commit -m "chore(backlog): mark TASK-5.4 and TASK-6.1 complete"
```
