# TASK-3.2 — Strava API Client (Activity Fetch)

**Date:** 2026-05-31
**Status:** Approved

---

## Goal

Implement a thin async HTTP client that fetches a single page of activities from the Strava API for an authenticated user.

---

## Key Design Decisions

### Module-level async function, not a class
The client is a standalone async function (`fetch_activities`) rather than a class. No instance state is needed — the access token is passed per call. A new `httpx.AsyncClient` is created per call via `async with`, ensuring sockets are always closed promptly. Connection reuse across paginated calls (within a single sync) is not worth the added complexity given the 10-minute cooldown and manual-trigger sync model.

### Single-page function; pagination loop belongs in the sync engine
`fetch_activities` fetches exactly one page. TASK-3.4 (the sync engine) owns the pagination loop, calling `fetch_activities` with incrementing `page` values until an empty list is returned. This keeps the client single-responsibility and trivially testable.

### `after` parameter forwarded to Strava
The Strava API supports an `after` epoch-timestamp parameter to filter activities to a given start date. `fetch_activities` accepts `after: int | None = None` and forwards it as a query param when provided. TASK-3.4 uses this to restrict fetches to the current calendar year. A `before` parameter is omitted (not needed for MVP sync logic; can be added in a future multi-year epic).

### Typed exceptions in `backend/sync/exceptions.py`
Two exception types cover the cases the sync engine needs to handle:
- `StravaUnauthorizedError` — HTTP 401; token invalid or expired; caller must refresh or invalidate session
- `StravaAPIError` — any other non-2xx response

These are separate from `backend/auth/exceptions.py`'s `StravaAPIError` to avoid ambiguous cross-domain imports.

### No retry logic
Retries are explicitly out of scope for TASK-3.2 and TASK-3.4. The sync engine surfaces errors directly; the user can re-trigger after the cooldown expires.

---

## Interface

```python
# backend/sync/strava_client.py

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

async def fetch_activities(
    access_token: str,
    *,
    after: int | None = None,
    page: int = 1,
    per_page: int = 200,
) -> list[dict]:
    ...
```

- Sets `Authorization: Bearer <access_token>` header
- Passes `page`, `per_page`, and `after` (if not None) as query parameters
- Returns raw JSON list — no transformation
- Logs `"Fetching Strava activities page=%d"` (never logs the token)
- Returns `[]` when Strava returns an empty list (signals page exhaustion to caller)
- Raises `StravaUnauthorizedError` on HTTP 401
- Raises `StravaAPIError` on any other non-2xx response

---

## Exceptions

```python
# backend/sync/exceptions.py

class StravaUnauthorizedError(Exception):
    pass

class StravaAPIError(Exception):
    pass
```

---

## New Files

| File | Purpose |
|---|---|
| `backend/sync/__init__.py` | Makes `sync` a package |
| `backend/sync/strava_client.py` | `fetch_activities` function |
| `backend/sync/exceptions.py` | `StravaUnauthorizedError`, `StravaAPIError` |
| `tests/backend/sync/__init__.py` | Makes test package |
| `tests/backend/sync/test_strava_client.py` | Unit tests (mocked with `respx`) |

## Dependency Change

Add `respx` to the `dev` dependency group in `pyproject.toml`. `respx` is the standard library for mocking `httpx` at the transport level — cleaner and less brittle than patching `AsyncClient` directly with `unittest.mock`.

---

## Tests

All tests mock the Strava HTTP endpoint using `respx`. No real network calls.

| Test | Assertion |
|---|---|
| Successful response | Returns list of dicts matching mocked payload |
| `after` param provided | Query string contains `after=<value>` |
| `after` not provided | Query string does not contain `after` |
| Empty response (page exhausted) | Returns `[]` |
| HTTP 401 | Raises `StravaUnauthorizedError` |
| HTTP 500 | Raises `StravaAPIError` |

---

## Testability

- All tests run without a network connection or Strava credentials
- `respx` intercepts `httpx` calls and returns mocked responses
- No DB interaction
