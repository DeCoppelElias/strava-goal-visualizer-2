---
title: TASK-5.3 — Personal Progress Computation
date: 2026-06-06
status: approved
---

## Overview

Add `GET /dashboard/personal` to the goals domain. The endpoint computes current-year running distance and progress percentage against the user's yearly goal, drawing on `Activity`, `Goal`, and `SyncState` tables.

The route is intentionally named `/dashboard/personal` (not `/goals/dashboard`) to leave room for a future `/dashboard/club` sibling.

---

## Schema

**File:** `backend/goals/schemas.py`

New model added alongside existing `GoalResponse`:

```python
class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
```

`last_sync_completed_at` is non-optional — the endpoint 404s before reaching the response when no `SyncState` row exists, so a `None` value can never reach this field.

---

## Service

**File:** `backend/goals/goals_service.py`

New method `get_personal_dashboard(db, user_id)` on `GoalService`:

### Steps

1. Load `SyncState` for `user_id` → if `None`, raise `HTTPException(404, detail="not_synced")`
2. Load `Goal` for `user_id` → if `None`, raise `HTTPException(404, detail="Goal not found")`
3. Query `SUM(distance_meters)` from `Activity` where `user_id = user_id` AND `start_date >= Jan 1 of current UTC year`
4. Compute fields:
   - `goal_km = float(goal.yearly_running_goal_km)`
   - `distance_to_date_km = (sum_meters or 0) / 1000`
   - `progress_pct = round(distance_to_date_km / goal_km * 100, 2)`
   - `days_in_year = 366 if calendar.isleap(year) else 365`
   - `day_of_year = today.timetuple().tm_yday`
   - `expected_pct = round(day_of_year / days_in_year * 100, 2)`
   - `on_pace = distance_to_date_km >= goal_km * (day_of_year / days_in_year)`
5. Return `PersonalDashboardResponse`

Uses `func.sum()` — single aggregate DB query, no Python-side iteration over activities.

### Edge cases

| State | Behaviour |
|---|---|
| No `SyncState` row | `404 detail="not_synced"` |
| No `Goal` row | `404 detail="Goal not found"` |
| Synced, zero runs this year | `200` with `distance_to_date_km=0`, `progress_pct=0`, `on_pace=False` |
| Leap year | `days_in_year=366` |

---

## Route

**File:** `backend/goals/router.py`

```python
@router.get("/dashboard/personal", response_model=PersonalDashboardResponse)
@limiter.limit("30/minute")
async def get_personal_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    goal_service: GoalService = Depends(get_goal_service),
) -> PersonalDashboardResponse:
    return await goal_service.get_personal_dashboard(db, current_user.id)
```

Reuses the existing `get_goal_service` factory — no changes to `dependencies.py`.

---

## Tests

### Service unit tests (`tests/backend/goals/test_goal_service.py`)

- Known activities in current year → verify `distance_to_date_km`, `progress_pct`, `expected_pct`, `on_pace` match manual calculation
- Activities from a previous year are excluded from the sum
- Activities belonging to another user are excluded
- No `SyncState` → `HTTPException(404, detail="not_synced")`
- No `Goal` → `HTTPException(404, detail="Goal not found")`
- Synced but zero running activities → returns 0 km, 0%, `on_pace=False`

### Router tests (`tests/backend/goals/test_goals_router.py`)

- Unauthenticated → `401`
- Authenticated, service returns valid data → `200` with correct JSON shape
- Service raises `"not_synced"` → `404` propagated correctly

---

## What is not in scope

- Aggregation beyond the current calendar year
- Activity breakdown (individual runs)
- Club dashboard (future `/dashboard/club`)
