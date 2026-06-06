---
title: Dashboard Domain Refactor
date: 2026-06-06
status: approved
---

## Overview

Move the personal dashboard logic out of the `goals` domain and into a new `dashboard` domain. `GoalService` currently queries `SyncState` and `Activity` (sync-domain models) to compute dashboard values — a cross-domain concern that blurs goal CRUD boundaries. A dedicated `dashboard/` domain owns all `/dashboard/*` routes, leaving `GoalService` as pure goal CRUD and creating a natural home for the future `/dashboard/club` endpoint.

Behaviour is unchanged: same URL, same response shape, same status codes.

---

## New domain structure

```
backend/dashboard/
  __init__.py
  router.py            # GET /dashboard/personal
  schemas.py           # PersonalDashboardResponse
  dashboard_service.py # DashboardService.get_personal_dashboard
```

---

## What moves

| Source | Destination |
|---|---|
| `backend/goals/schemas.py` → `PersonalDashboardResponse` | `backend/dashboard/schemas.py` |
| `backend/goals/goals_service.py` → `get_personal_dashboard` | `backend/dashboard/dashboard_service.py` → `DashboardService` |
| `backend/goals/router.py` → `GET /dashboard/personal` route | `backend/dashboard/router.py` |
| `tests/backend/goals/test_goal_service.py` → dashboard helpers + 5 tests | `tests/backend/dashboard/test_dashboard_service.py` |
| `tests/backend/goals/test_goals_router.py` → 3 dashboard router tests + schema smoke test | `tests/backend/dashboard/test_dashboard_router.py` |

---

## What changes in existing files

### `backend/goals/goals_service.py`
Remove `get_personal_dashboard`. Drop now-unused imports: `calendar`, `func`, `SyncState`, `Activity`, `PersonalDashboardResponse`. Result: pure goal CRUD (`get_goal`, `update_goal`).

### `backend/goals/schemas.py`
Remove `PersonalDashboardResponse` and its `from datetime import datetime` import.

### `backend/goals/router.py`
Remove `GET /dashboard/personal` handler and `PersonalDashboardResponse` import.

### `backend/dependencies.py`
Add factory:
```python
from backend.dashboard.dashboard_service import DashboardService

def get_dashboard_service() -> DashboardService:
    return DashboardService()
```

### `backend/main.py`
Import and register:
```python
from backend.dashboard.router import router as dashboard_router
...
app.include_router(dashboard_router)
```

---

## Test files

### New: `tests/backend/dashboard/__init__.py`
Empty.

### New: `tests/backend/dashboard/test_dashboard_service.py`
Move from `test_goal_service.py`: `_make_sync_state`, `_make_db_for_dashboard`, `_FIXED_NOW`, and all 5 `test_get_personal_dashboard_*` tests. Add local `_make_goal` helper (copy from goals tests — no shared state between test modules).

### New: `tests/backend/dashboard/test_dashboard_router.py`
Move from `test_goals_router.py`: the 3 `test_get_personal_dashboard_*` router tests and `test_personal_dashboard_response_schema_importable`. Add local `_make_user`, `_stub_user`, `_stub_401` helpers and `reset_rate_limiter` fixture (copy from goals router tests).

### `tests/backend/goals/test_goal_service.py`
Remove: `_make_sync_state`, `_make_db_for_dashboard`, `_FIXED_NOW`, all `test_get_personal_dashboard_*` tests. Remove `SyncState` import and `patch` import if unused.

### `tests/backend/goals/test_goals_router.py`
Remove: `test_personal_dashboard_response_schema_importable` and 3 `test_get_personal_dashboard_*` router tests.

---

## What is not in scope

- Any change to the endpoint URL, response shape, or status codes
- Moving other goal endpoints
- Implementing `/dashboard/club`
