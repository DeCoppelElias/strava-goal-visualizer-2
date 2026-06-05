# TASK-5.1 — Goals Database Schema

_Date: 2026-06-05_

---

## Overview

Add a `goals` table to store each user's yearly running goal, along with the `Goal` ORM model and auto-creation logic on first login.

---

## Schema

**Table: `goals`**

| Column | Type | Constraints |
|---|---|---|
| `user_id` | integer | PK, FK → `users.id` |
| `yearly_running_goal_km` | numeric | NOT NULL, default 365, CHECK > 0 AND <= 100000 |
| `updated_at` | timestamptz | NOT NULL |

- `user_id` is the primary key — one goal row per user.
- No `created_at`; goals do not need a creation audit trail.
- Column name is `yearly_running_goal_km` to distinguish from potential future goals for other activity types (e.g. cycling).
- Check constraint enforced at DB level; API-layer validation added in TASK-5.2.

---

## ORM Model (`backend/shared/models.py`)

New `Goal` class following the `SyncState` pattern (user_id as PK):

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

`User` model gains a `goal` relationship:

```python
goal: Mapped[Optional["Goal"]] = relationship(back_populates="user", uselist=False)
```

---

## Migration (`0003_create_goals_table.py`)

Hand-written Alembic migration (consistent with `0001` and `0002`):

- `upgrade`: `op.create_table("goals", ...)` with PK, FK, numeric column (server default `365`), check constraint, `updated_at`.
- `downgrade`: `op.drop_table("goals")`.

---

## Auto-creation on first login

Inside `_upsert_user` in `backend/auth/strava_oauth_service.py`, after the `db.flush()` that populates `user.id` for a new user:

```python
if user is None:
    user = User(strava_athlete_id=strava_athlete_id)
    db.add(user)
    await db.flush()
    db.add(Goal(user_id=user.id))  # default 365 km
```

Existing users (re-login) follow the existing path and are unaffected.

---

## Tests

1. New user via `_upsert_user` → `goals` row exists with `yearly_running_goal_km = 365`.
2. Existing user re-login → still exactly one goal row (no duplicate, no error).
3. DB constraint: inserting `yearly_running_goal_km = 0` raises `IntegrityError`.
4. DB constraint: inserting `yearly_running_goal_km = 100001` raises `IntegrityError`.

---

## Out of scope

- `GET /goals` and `PUT /goals` endpoints — TASK-5.2.
- Progress computation — TASK-5.3.
- Frontend — TASK-5.4.
