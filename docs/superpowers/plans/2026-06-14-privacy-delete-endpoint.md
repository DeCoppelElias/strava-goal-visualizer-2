# Privacy Delete Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /privacy/delete` so an authenticated user can permanently erase their account and all data (GDPR right to erasure).

**Architecture:** Thin endpoint — delegates all deletion to `PrivacyService.delete_user_data` (already implemented), clears the session cookie, and returns `{"deleted": true}`. One new schema model (`DeleteResponse`), one new route in the existing privacy router, one new test file.

**Tech Stack:** FastAPI, Pydantic v2, slowapi rate limiting, starlette sessions, pytest + unittest.mock (router tests).

---

## Files

| Action | Path |
|--------|------|
| Modify | `backend/privacy/schemas.py` |
| Modify | `backend/privacy/router.py` |
| Create | `tests/backend/privacy/test_privacy_router.py` |

---

### Task 1: Write failing router tests

**Files:**
- Create: `tests/backend/privacy/test_privacy_router.py`

- [ ] **Step 1: Create the test file**

```python
# tests/backend/privacy/test_privacy_router.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.shared.models import DeletionReason, User


def _stub_user(user: User):
    async def _inner():
        return user
    return _inner


def _stub_401():
    async def _inner():
        raise HTTPException(status_code=401)
    return _inner


def test_delete_returns_200_and_deleted_true_when_authenticated():
    from unittest.mock import patch

    from backend.main import app

    user = User(id=1, strava_athlete_id=99999)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_current_user] = _stub_user(user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/privacy/delete")
        assert response.status_code == 200
        assert response.json() == {"deleted": True}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_delete_calls_service_with_user_initiated_reason():
    from unittest.mock import patch

    from backend.main import app

    user = User(id=7, strava_athlete_id=88888)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_current_user] = _stub_user(user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            client.post("/privacy/delete")
        mock_svc.delete_user_data.assert_called_once()
        call_kwargs = mock_svc.delete_user_data.call_args
        assert call_kwargs.kwargs["user_id"] == 7
        assert call_kwargs.kwargs["reason"] == DeletionReason.USER_INITIATED
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_delete_returns_401_when_unauthenticated():
    from unittest.mock import patch

    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/privacy/delete")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_delete_rate_limit_returns_429():
    from unittest.mock import patch

    from backend.main import app
    from backend.shared.rate_limit import limiter

    user = User(id=1, strava_athlete_id=99999)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    limiter.reset()
    app.dependency_overrides[get_current_user] = _stub_user(user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            responses = [client.post("/privacy/delete") for _ in range(6)]
        assert responses[-1].status_code == 429
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_privacy_service, None)
        limiter.reset()
```

- [ ] **Step 2: Run tests — expect failure (name not found)**

```
uv run pytest tests/backend/privacy/test_privacy_router.py -v
```

Expected: `FAILED` — `ImportError` or `404` because the route doesn't exist yet.

---

### Task 2: Add `DeleteResponse` schema

**Files:**
- Modify: `backend/privacy/schemas.py`

- [ ] **Step 3: Append `DeleteResponse` to the schemas file**

Add at the end of `backend/privacy/schemas.py`:

```python
class DeleteResponse(BaseModel):
    deleted: bool
```

The file already imports `BaseModel` from pydantic — no new import needed.

---

### Task 3: Add the endpoint to the privacy router

**Files:**
- Modify: `backend/privacy/router.py`

- [ ] **Step 4: Add the import and endpoint**

Current top of `backend/privacy/router.py`:

```python
import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.privacy.privacy_service import PrivacyService
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter
```

Replace the import block with (adds `DeletionReason` and `DeleteResponse`):

```python
import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.privacy.privacy_service import PrivacyService
from backend.privacy.schemas import DeleteResponse
from backend.shared.db import get_db
from backend.shared.models import DeletionReason, User
from backend.shared.rate_limit import limiter
```

Then append the new endpoint after the existing `export_user_data` function:

```python
@router.post("/privacy/delete", response_model=DeleteResponse)
@limiter.limit("5/hour")
async def delete_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> DeleteResponse:
    await privacy_service.delete_user_data(
        db, user_id=current_user.id, reason=DeletionReason.USER_INITIATED
    )
    request.session.clear()
    return DeleteResponse(deleted=True)
```

- [ ] **Step 5: Run the tests — expect all passing**

```
uv run pytest tests/backend/privacy/test_privacy_router.py -v
```

Expected output:
```
PASSED tests/backend/privacy/test_privacy_router.py::test_delete_returns_200_and_deleted_true_when_authenticated
PASSED tests/backend/privacy/test_privacy_router.py::test_delete_calls_service_with_user_initiated_reason
PASSED tests/backend/privacy/test_privacy_router.py::test_delete_returns_401_when_unauthenticated
PASSED tests/backend/privacy/test_privacy_router.py::test_delete_rate_limit_returns_429
4 passed
```

- [ ] **Step 6: Run the full test suite to check for regressions**

```
uv run pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 7: Run linter and type-checker**

```
uv run ruff check backend/privacy/
uv run mypy backend/privacy/
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add backend/privacy/schemas.py backend/privacy/router.py tests/backend/privacy/test_privacy_router.py
git commit -m "feat(privacy): add POST /privacy/delete endpoint"
```
