# TASK-6.1 — Clubs & Club Memberships Database Schema

_Date: 2026-06-07_

---

## Goal

Add PostgreSQL tables for Strava clubs and club memberships, along with their SQLAlchemy ORM models, following existing project conventions exactly.

---

## Tables

### `clubs`

| Column | Type | Constraints |
|---|---|---|
| `id` | `BIGINT` | PK (Strava club ID — natural key, no surrogate) |
| `name` | `TEXT` | NOT NULL |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` |

No surrogate key. The Strava club ID is stable and unique across the platform, making it the correct natural primary key.

### `club_memberships`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | `INTEGER` | FK → `users.id`, NOT NULL |
| `club_id` | `BIGINT` | FK → `clubs.id`, NOT NULL |
| `synced_at` | `TIMESTAMPTZ` | NOT NULL |

- Composite PK on `(user_id, club_id)`.
- Additional index on `club_id` alone to support the future `GET /clubs/{club_id}/progress` query, which looks up all members of a given club.

---

## ORM Models

Both new models are added to `backend/shared/models.py`.

**Type discipline:**
- `Club.id` — `mapped_column(BigInteger, primary_key=True)` (Strava IDs exceed `INTEGER` range).
- `Club.updated_at` — `mapped_column(_tz, default=_now)` where `_tz = DateTime(timezone=True)`. Must not use bare `DateTime()`.
- `ClubMembership.synced_at` — `mapped_column(_tz)`. Must not use bare `DateTime()`.

**Relationships (bidirectional, consistent with existing models):**

```
Club
  └── memberships: Mapped[list["ClubMembership"]]  (back_populates="club")

ClubMembership
  ├── user: Mapped["User"]                          (back_populates="club_memberships")
  └── club: Mapped["Club"]                          (back_populates="memberships")

User (existing model — add one relationship)
  └── club_memberships: Mapped[list["ClubMembership"]]  (back_populates="user")
```

---

## Migration

File: `backend/db/migrations/versions/0004_create_clubs_tables.py`

- Revision: `0004`, down_revision: `0003`
- `upgrade()`: creates `clubs`, then `club_memberships` (FK dependency order), then creates the `club_id` index.
- `downgrade()`: drops `club_memberships`, then `clubs`.
- All `DateTime` columns use `sa.DateTime(timezone=True)` — not bare `sa.DateTime()`.

---

## Scope

This task is schema-only. No routes, no service logic, no Strava API calls. TASK-6.2 adds the sync-time club fetch; TASK-6.3/6.4 add the endpoints.

---

## Pre-conditions

- TASK-5.4 (Personal goal dashboard page) is complete — marked ✅ as part of this task's bookkeeping.
- Migration 0003 is the current head.
