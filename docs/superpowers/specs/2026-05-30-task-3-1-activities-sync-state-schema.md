# TASK-3.1 — Activities & Sync State Database Schema

**Date:** 2026-05-30
**Status:** Approved

---

## Goal

Add `Activity` and `SyncState` ORM models to `backend/shared/models.py` and create a corresponding Alembic migration.

---

## Key Design Decisions

### Only running activities stored (data minimization)
The sync engine filters to `sport_type = 'Run'` at ingest — non-running activities from Strava are discarded before any DB write. The `Activity` model still includes a `sport_type` column (it will always be `"Run"`) for clarity and forward compatibility, but no query-time filter is needed. This follows the GDPR data minimization principle: the app's purpose is running goal visualization, so storing cycling or swimming data has no justification.

### `distance_meters` as `Numeric`, not `Float`
`Numeric` avoids floating-point rounding errors. Strava returns meter values as floats but storing them as `Numeric` is more principled for a distance field.

### `SyncState` uses `user_id` as PK
One sync state row per user. No surrogate key needed — `user_id` is both the PK and the FK. `last_sync_completed_at` is NOT NULL — the absence of a row means "never synced". The sync engine inserts on first sync and upserts on subsequent syncs. No separate `updated_at` column because `last_sync_completed_at` already serves as the update timestamp.

### Index on `(user_id, start_date)`
Added proactively for goal progress queries (EPIC-5) that will filter by user and date range. At typical Strava user data volumes (hundreds to low thousands of activities), a partial index is not needed.

---

## Schema

### `activities` table

| Column | Type | Constraints |
|---|---|---|
| `id` | `Integer` | PK |
| `user_id` | `Integer` | FK → `users.id`, not null |
| `strava_activity_id` | `BigInteger` | not null |
| `name` | `Text` | not null |
| `sport_type` | `Text` | not null |
| `distance_meters` | `Numeric` | not null |
| `moving_time_seconds` | `Integer` | not null |
| `start_date` | `DateTime(timezone=True)` | not null |
| `created_at` | `DateTime(timezone=True)` | server default `now()` |
| `updated_at` | `DateTime(timezone=True)` | server default `now()` |

**Unique constraint:** `(user_id, strava_activity_id)`
**Index:** `(user_id, start_date)`

### `sync_state` table

| Column | Type | Constraints |
|---|---|---|
| `user_id` | `Integer` | PK + FK → `users.id` |
| `last_sync_completed_at` | `DateTime(timezone=True)` | not null |

---

## ORM Models (`backend/shared/models.py`)

```python
class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "strava_activity_id"),
        Index("ix_activities_user_start_date", "user_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    strava_activity_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text)
    sport_type: Mapped[str] = mapped_column(Text)
    distance_meters: Mapped[Decimal] = mapped_column(Numeric)
    moving_time_seconds: Mapped[int] = mapped_column()
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="activities")


class SyncState(Base):
    __tablename__ = "sync_state"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_sync_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sync_state")
```

`User` gets two new relationships:
```python
activities: Mapped[list["Activity"]] = relationship(back_populates="user")
sync_state: Mapped[Optional["SyncState"]] = relationship(back_populates="user", uselist=False)
```

---

## Migration

File: `backend/db/migrations/versions/0002_create_sync_tables.py`

- `down_revision = "0001"`
- `upgrade()`: create `activities` (with unique constraint + index), then `sync_state`
- `downgrade()`: drop `sync_state`, then `activities`

---

## Testability

- Tables visible in `psql` after `alembic upgrade head`
- Backend starts without migration errors
- Inserting two activities with the same `(user_id, strava_activity_id)` raises an integrity error
- No `sync_state` row exists for a new user (never synced)
- Inserting a `SyncState` row with a real timestamp succeeds; inserting without `last_sync_completed_at` raises an integrity error
