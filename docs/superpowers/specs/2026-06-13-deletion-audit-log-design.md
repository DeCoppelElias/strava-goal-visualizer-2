# TASK-7.1 — Deletion Audit Log Schema

_Date: 2026-06-13_

## Goal

Add a `deletion_events` table to record when user data is deleted, along with the reason. Rows must survive after the user row is deleted (no FK), and a Python domain model must constrain the valid reason values at the application level.

## Schema

**Table: `deletion_events`**

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` PK | autoincrement |
| `user_id` | `BIGINT` | Strava athlete ID — **not** a FK; preserved after user row is deleted |
| `reason` | `TEXT` | free-form in DB; constrained by `DeletionReason` at app level |
| `deleted_at` | `TIMESTAMPTZ` | UTC, set on insert via `default=_now` |

No `updated_at` — this is an immutable event log.

## ORM Model

Added to `backend/shared/models.py`:

```python
class DeletionReason(str, enum.Enum):
    USER_INITIATED = "user_initiated"
    STRAVA_DEAUTH  = "strava_deauth"

class DeletionEvent(Base):
    __tablename__ = "deletion_events"

    id:         Mapped[int]      = mapped_column(primary_key=True)
    user_id:    Mapped[int]      = mapped_column(BigInteger)
    reason:     Mapped[str]      = mapped_column(Text)
    deleted_at: Mapped[datetime] = mapped_column(_tz, default=_now)
```

`DeletionReason` uses `str, enum.Enum` so values compare equal to their string literals, allowing direct ORM assignment without conversion.

## Migration

File: `backend/db/migrations/versions/0006_create_deletion_events.py`
- `revision = "0006"`, `down_revision = "0005"`
- `upgrade`: `op.create_table("deletion_events", ...)` with all four columns
- `downgrade`: `op.drop_table("deletion_events")`

## Callers

The deletion service (`backend/privacy/deletion_service.py`, implemented in TASK-7.2) imports `DeletionReason` from `backend.shared.models` and passes `DeletionReason.USER_INITIATED` or `DeletionReason.STRAVA_DEAUTH` when constructing a `DeletionEvent` row.

## Testing

Testability per backlog: migration applies cleanly; a row can be inserted and read back via `psql`. Full integration-test coverage deferred to TASK-7.2 where the deletion service exercises this table.
