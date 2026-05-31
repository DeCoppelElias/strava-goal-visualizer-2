# TASK-3.2 — Strava Activity Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a thin async HTTP client function that fetches one page of activities from the Strava API, with typed exceptions and full unit-test coverage.

**Architecture:** Module-level async function `fetch_activities` in `backend/sync/strava_client.py`. Uses `httpx.AsyncClient` as a context manager per call. Domain-specific exceptions live in `backend/sync/exceptions.py`. Tests mock the HTTP layer with `respx` (intercepting at the transport level — no real network calls).

**Tech Stack:** Python 3.12, httpx 0.28, respx (new dev dependency), pytest-asyncio (auto mode already configured)

---

### Task 1: Add respx to dev dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock` (auto-updated by uv sync)

- [ ] Add `respx>=0.21` to the `dev` dependency group in `pyproject.toml`. The full updated group:

```toml
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=1.3",
    "respx>=0.21",
    "ruff>=0.4",
    "mypy>=1.10",
    "pre-commit>=3.7",
]
```

- [ ] Sync the environment:

```
uv sync
```

Expected: resolves and installs respx without errors.

- [ ] Verify the import works:

```
uv run python -c "import respx; print(respx.__version__)"
```

Expected: prints a version number (e.g. `0.21.x`).

- [ ] Commit:

```
git add pyproject.toml uv.lock
git commit -m "chore(deps): add respx to dev dependencies"
```

---

### Task 2: Create sync package and exceptions

**Files:**
- Create: `backend/sync/__init__.py`
- Create: `backend/sync/exceptions.py`
- Create: `tests/backend/sync/__init__.py`
- Create: `tests/backend/sync/test_strava_client.py` (exception tests only — expanded in Task 3)

- [ ] Write the first failing tests. Create `tests/backend/sync/__init__.py` as an empty file, then create `tests/backend/sync/test_strava_client.py`:

```python
from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError


def test_strava_unauthorized_error_is_exception():
    assert issubclass(StravaUnauthorizedError, Exception)


def test_strava_api_error_is_exception():
    assert issubclass(StravaAPIError, Exception)
```

- [ ] Run to verify the tests fail:

```
uv run pytest tests/backend/sync/test_strava_client.py -v
```

Expected: `ImportError: No module named 'backend.sync'`

- [ ] Create `backend/sync/__init__.py` as an empty file, then create `backend/sync/exceptions.py`:

```python
class StravaUnauthorizedError(Exception):
    pass


class StravaAPIError(Exception):
    pass
```

- [ ] Run to verify the tests pass:

```
uv run pytest tests/backend/sync/test_strava_client.py -v
```

Expected: 2 passed.

- [ ] Commit:

```
git add backend/sync/__init__.py backend/sync/exceptions.py tests/backend/sync/__init__.py tests/backend/sync/test_strava_client.py
git commit -m "feat(sync): add sync package with typed exceptions"
```

---

### Task 3: Implement fetch_activities

**Files:**
- Create: `backend/sync/strava_client.py`
- Modify: `tests/backend/sync/test_strava_client.py` (replace with full test suite)

- [ ] Replace the entire contents of `tests/backend/sync/test_strava_client.py` with the full test suite:

```python
import httpx
import pytest

from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.sync.strava_client import STRAVA_ACTIVITIES_URL, fetch_activities

SAMPLE_ACTIVITIES = [{"id": 1, "name": "Morning Run"}, {"id": 2, "name": "Evening Run"}]


def test_strava_unauthorized_error_is_exception():
    assert issubclass(StravaUnauthorizedError, Exception)


def test_strava_api_error_is_exception():
    assert issubclass(StravaAPIError, Exception)


async def test_fetch_activities_returns_activity_list(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=SAMPLE_ACTIVITIES)
    )
    result = await fetch_activities("my-token")
    assert result == SAMPLE_ACTIVITIES


async def test_fetch_activities_sends_after_param_when_provided(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    await fetch_activities("my-token", after=1735689600)
    assert respx_mock.calls.last.request.url.params["after"] == "1735689600"


async def test_fetch_activities_omits_after_param_when_not_provided(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    await fetch_activities("my-token")
    assert "after" not in respx_mock.calls.last.request.url.params


async def test_fetch_activities_returns_empty_list_when_page_exhausted(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    result = await fetch_activities("my-token")
    assert result == []


async def test_fetch_activities_raises_unauthorized_on_401(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(StravaUnauthorizedError):
        await fetch_activities("bad-token")


async def test_fetch_activities_raises_api_error_on_500(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(StravaAPIError):
        await fetch_activities("my-token")
```

- [ ] Run to verify the new tests fail (exception tests still pass, client tests fail):

```
uv run pytest tests/backend/sync/test_strava_client.py -v
```

Expected: 2 passed, 6 errors with `ImportError: cannot import name 'fetch_activities'`.

- [ ] Create `backend/sync/strava_client.py`:

```python
import logging
from typing import Any

import httpx

from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError

logger = logging.getLogger(__name__)

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


async def fetch_activities(
    access_token: str,
    *,
    after: int | None = None,
    page: int = 1,
    per_page: int = 200,
) -> list[dict[str, Any]]:
    params: dict[str, int] = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after

    logger.info("Fetching Strava activities page=%d", page)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            STRAVA_ACTIVITIES_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        if response.status_code == 401:
            raise StravaUnauthorizedError("Strava returned 401 — token invalid or expired")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StravaAPIError(f"Strava API error: {exc}") from exc
        return response.json()  # type: ignore[no-any-return]
```

- [ ] Run all sync tests to verify they all pass:

```
uv run pytest tests/backend/sync/test_strava_client.py -v
```

Expected: 8 passed.

- [ ] Run the full test suite to check for regressions:

```
uv run pytest -v
```

Expected: 49 passed (41 existing + 8 new).

- [ ] Commit:

```
git add backend/sync/strava_client.py tests/backend/sync/test_strava_client.py
git commit -m "feat(sync): implement fetch_activities Strava API client (TASK-3.2)"
```
