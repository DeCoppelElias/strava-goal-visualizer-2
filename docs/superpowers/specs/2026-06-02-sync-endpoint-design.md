# TASK-3.4 — POST /sync Endpoint Design

_Date: 2026-06-02_

## Overview

Implements the `POST /sync` endpoint: fetches all current-year running activities from Strava for the authenticated user, upserts them into PostgreSQL, and records the sync completion timestamp. Includes per-user 10-minute cooldown enforcement and IP-level rate limiting.

---

## Files

### New

| File | Purpose |
|------|---------|
| `backend/sync/schemas.py` | `SyncResponse` Pydantic model |
| `backend/sync/sync_service.py` | `SyncService` — all business logic, no FastAPI imports |
| `backend/sync/router.py` | `POST /sync` route, error handling, rate limit |

### Modified

| File | Change |
|------|--------|
| `backend/sync/exceptions.py` | Add `SyncCooldownError(retry_after_seconds: int)` |
| `backend/dependencies.py` | Add `get_sync_service()` factory |
| `backend/main.py` | Register sync router via `app.include_router(sync_router)` |

---

## Schema

```python
class SyncResponse(BaseModel):
    synced_activities: int
    last_sync_completed_at: datetime
```

---

## SyncService

Constructed with a `StravaOAuthService` instance (injected via DI). Single public method:

```python
async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse
```

### Step-by-step flow

1. **Cooldown check** — read `SyncState` for `user_id`. If `last_sync_completed_at` exists and `now() - last_sync_completed_at < 10 minutes`, raise `SyncCooldownError(retry_after_seconds)` where `retry_after_seconds = 600 - elapsed_seconds`.

2. **Token** — call `self.oauth_service.ensure_fresh_token(db, user_id)` → plaintext access token. Raises `TokenRefreshError` on failure (propagated to router).

3. **Fetch** — call `fetch_all_activities(token, after=<unix timestamp of Jan 1 current year, UTC>)`. Raises `StravaAPIError` / `StravaUnauthorizedError` on failure.

4. **Filter** — discard any activity dict where `activity["sport_type"] != "Run"`. All remaining are runs.

5. **Bulk upsert** — execute a single `insert().on_conflict_do_update()` against the `activities` table. Conflict target: `(user_id, strava_activity_id)`. On conflict, update: `name`, `sport_type`, `distance_meters`, `moving_time_seconds`, `start_date`, `updated_at`. This runs inside the `session.begin()` transaction owned by `get_db` — no explicit commit in the service.

6. **Upsert SyncState** — read existing `SyncState` row for `user_id`. If present, update `last_sync_completed_at = now()`. If absent, insert a new row. (No `insert().on_conflict_do_update()` needed here since `SyncState` has `user_id` as PK and is a single row.)

7. **Return** — `SyncResponse(synced_activities=len(run_activities), last_sync_completed_at=now)`.

---

## Router

```
POST /sync
Rate limit: 2/minute per IP
Auth: requires get_current_user
```

Error mapping:

| Exception | HTTP response |
|-----------|--------------|
| `SyncCooldownError` | `429 Too Many Requests` + `Retry-After: <seconds>` header |
| `TokenRefreshError` | `401 Unauthorized` |
| `StravaUnauthorizedError` | `401 Unauthorized` |
| `StravaAPIError` | `502 Bad Gateway` |

---

## Dependency Injection

```python
# dependencies.py
def get_sync_service(
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),
) -> SyncService:
    return SyncService(strava_oauth_service)
```

---

## Transaction Ownership

Per the project convention (TASK-3.3.6): `SyncService` mutates ORM state but never calls `db.commit()`. The `session.begin()` context in `get_db` auto-commits on clean request exit and auto-rolls back on exception. All activity upserts and the `SyncState` update are atomic within that single transaction.

---

## Tests

Unit tests (no DB, no HTTP — mock `StravaOAuthService` and `fetch_all_activities`):

| Test | Assertion |
|------|-----------|
| First sync (no SyncState row) | No cooldown raised; completes successfully |
| Recent sync (< 10 min ago) | `SyncCooldownError` raised with correct `retry_after_seconds` |
| Sync after cooldown expires | Completes successfully |
| Mixed sport types returned | Only Run activities passed to upsert; count reflects only runs |
| All activities are non-Run | Upsert called with empty list; `synced_activities = 0` |
| `TokenRefreshError` from `ensure_fresh_token` | Propagates to router |
| `StravaAPIError` from `fetch_all_activities` | Propagates to router |

Integration/router tests (via `TestClient`, real DB):

| Test | Assertion |
|------|-----------|
| Unauthenticated `POST /sync` | `401` |
| Authenticated sync, mocked Strava | `200`, correct `synced_activities` count, DB rows present |
| Two syncs within 10 min | Second returns `429` with `Retry-After` header |
| Two syncs with mocked time gap | Both succeed; no duplicate rows |
| Non-Run activities in Strava response | Not stored in DB |
