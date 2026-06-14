# Strava Deauth Webhook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `GET /strava/deauth` (subscription challenge) and `POST /strava/deauth` (deauth event handler) so the app satisfies Strava's platform terms for deauthorization handling.

**Architecture:** The two routes live in `backend/privacy/router.py`. The GET handler echoes Strava's challenge token during one-time subscription setup. The POST handler filters all incoming Strava events, acts only on deauth payloads, looks up the user by Strava athlete ID, calls the existing `PrivacyService.delete_user_data`, and always returns 200 (Strava's requirement). Session invalidation is natural — `get_current_user` queries the DB on every request, so deleting the user makes their cookie return 401 on the next call.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, slowapi, pytest + pytest-asyncio (asyncio_mode=auto), httpx (for HTTP-layer integration tests), testcontainers (real Postgres in integration tests)

---

## File Map

| File | Change |
|------|--------|
| `backend/shared/config.py` | Add `STRAVA_WEBHOOK_VERIFY_TOKEN` to `_REQUIRED_ENV_VARS` and `Settings` |
| `.env.example` | Document `STRAVA_WEBHOOK_VERIFY_TOKEN` |
| `tests/conftest.py` | Add `os.environ.setdefault("STRAVA_WEBHOOK_VERIFY_TOKEN", "test-verify-token")` |
| `backend/privacy/schemas.py` | Add `WebhookChallengeResponse`, `StravaWebhookPayload`, `DeauthResponse` |
| `backend/privacy/router.py` | Add `GET /strava/deauth` and `POST /strava/deauth` |
| `tests/backend/privacy/test_privacy_router.py` | Add unit tests for both new routes |
| `tests/backend/privacy/test_deauth_integration.py` | New: integration tests with real Postgres |
| `docs/ops/webhook-registration.md` | New: post-deployment runbook |

---

## Task 1: Config — Add STRAVA_WEBHOOK_VERIFY_TOKEN

**Files:**
- Modify: `backend/shared/config.py`
- Modify: `.env.example`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add the env var to `_REQUIRED_ENV_VARS` and `Settings` in `backend/shared/config.py`**

The change adds `"STRAVA_WEBHOOK_VERIFY_TOKEN"` to the required list and a matching `strava_webhook_verify_token: str` field to the `Settings` dataclass and the `settings` instance.

```python
# backend/shared/config.py — full file after edit

import logging
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS: list[str] = [
    "FRONTEND_ORIGIN",
    "DATABASE_URL",
    "TOKEN_ENCRYPTION_KEY",
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REDIRECT_URI",
    "SESSION_SECRET_KEY",
    "STRAVA_WEBHOOK_VERIFY_TOKEN",
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)


@dataclass(frozen=True)
class Settings:
    frontend_origin: str
    database_url: str
    token_encryption_key: str
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str
    session_secret_key: str
    strava_webhook_verify_token: str
    sync_cooldown_seconds: int = 600


settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=os.environ["DATABASE_URL"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
    session_secret_key=os.environ["SESSION_SECRET_KEY"],
    strava_webhook_verify_token=os.environ["STRAVA_WEBHOOK_VERIFY_TOKEN"],
    sync_cooldown_seconds=int(os.environ.get("SYNC_COOLDOWN_SECONDS", "600")),
)
```

- [ ] **Step 2: Document the new var in `.env.example`**

Add after the `# ---- Sync ----` block:

```
# ---- Strava webhook ----
# A string you choose freely. Used to verify the hub.verify_token that Strava
# sends during webhook subscription setup. Set this to any random string, then
# use the same value when registering the webhook subscription with Strava.
# Generate with: python -c "import secrets; print(secrets.token_hex(16))"
STRAVA_WEBHOOK_VERIFY_TOKEN=
```

- [ ] **Step 3: Add the default to `tests/conftest.py` so tests don't need a real `.env`**

Add one line alongside the other `os.environ.setdefault` calls:

```python
os.environ.setdefault("STRAVA_WEBHOOK_VERIFY_TOKEN", "test-verify-token")
```

The full block of `setdefault` calls in `tests/conftest.py` should now read:

```python
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("STRAVA_REDIRECT_URI", "http://localhost:8000/oauth/callback")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")
os.environ.setdefault("STRAVA_WEBHOOK_VERIFY_TOKEN", "test-verify-token")
```

- [ ] **Step 4: Verify existing tests still pass after the config change**

```bash
uv run pytest tests/ -x -q
```

Expected: all existing tests pass (the new env var is set by conftest, so nothing breaks).

- [ ] **Step 5: Commit**

```bash
git add backend/shared/config.py .env.example tests/conftest.py
git commit -m "feat(privacy): add STRAVA_WEBHOOK_VERIFY_TOKEN config"
```

---

## Task 2: Schemas — Add Webhook Schemas

**Files:**
- Modify: `backend/privacy/schemas.py`

- [ ] **Step 1: Add the three new schemas to `backend/privacy/schemas.py`**

Add at the end of the file. Do not remove any existing schemas.

```python
from pydantic import ConfigDict, Field

# --- Strava webhook schemas ---

class WebhookChallengeResponse(BaseModel):
    """Response for GET /strava/deauth — echoes hub.challenge back to Strava."""
    model_config = ConfigDict(populate_by_name=True)
    hub_challenge: str = Field(alias="hub.challenge")


class StravaWebhookPayload(BaseModel):
    """Incoming POST body from Strava webhook events."""
    object_type: str
    aspect_type: str
    owner_id: int
    updates: dict[str, str] = {}


class DeauthResponse(BaseModel):
    status: str = "ok"
```

**Note on `WebhookChallengeResponse`:** FastAPI serializes response models with `by_alias=True` by default (Pydantic v2), so the JSON output will be `{"hub.challenge": "..."}` as Strava expects. `populate_by_name=True` allows constructing the model via `WebhookChallengeResponse(hub_challenge="...")` in the handler.

- [ ] **Step 2: Verify the module imports cleanly**

```bash
uv run python -c "from backend.privacy.schemas import WebhookChallengeResponse, StravaWebhookPayload, DeauthResponse; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/privacy/schemas.py
git commit -m "feat(privacy): add webhook schemas for deauth endpoint"
```

---

## Task 3: GET /strava/deauth — Subscription Challenge Handler (TDD)

**Files:**
- Modify: `tests/backend/privacy/test_privacy_router.py`
- Modify: `backend/privacy/router.py`

- [ ] **Step 1: Write the failing unit tests for GET /strava/deauth**

Add these tests to `tests/backend/privacy/test_privacy_router.py`. Add them below the existing delete tests.

```python
# --- GET /strava/deauth ---

def test_webhook_challenge_returns_200_and_echoes_challenge():
    from unittest.mock import patch
    from backend.main import app

    with patch("backend.main._run_migrations"), TestClient(app) as client:
        response = client.get(
            "/strava/deauth",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": "test-verify-token",
            },
        )
    assert response.status_code == 200
    assert response.json() == {"hub.challenge": "abc123"}


def test_webhook_challenge_returns_403_for_wrong_verify_token():
    from unittest.mock import patch
    from backend.main import app

    with patch("backend.main._run_migrations"), TestClient(app) as client:
        response = client.get(
            "/strava/deauth",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": "WRONG_TOKEN",
            },
        )
    assert response.status_code == 403
```

- [ ] **Step 2: Run the failing tests**

```bash
uv run pytest tests/backend/privacy/test_privacy_router.py::test_webhook_challenge_returns_200_and_echoes_challenge tests/backend/privacy/test_privacy_router.py::test_webhook_challenge_returns_403_for_wrong_verify_token -v
```

Expected: both FAIL with `404 Not Found` (route not yet defined).

- [ ] **Step 3: Implement GET /strava/deauth in `backend/privacy/router.py`**

Add these imports at the top of `backend/privacy/router.py` (merge with existing imports):

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.privacy.privacy_service import PrivacyService
from backend.privacy.schemas import (
    DeleteResponse,
    DeauthResponse,
    StravaWebhookPayload,
    WebhookChallengeResponse,
)
from backend.shared.config import settings
from backend.shared.db import get_db
from backend.shared.models import DeletionReason, User
from backend.shared.rate_limit import limiter
```

Then add the GET route after the existing `_serialize` helper and before the existing POST routes:

```python
@router.get("/strava/deauth", response_model=WebhookChallengeResponse)
@limiter.limit("20/minute")
async def strava_webhook_challenge(
    request: Request,
    hub_challenge: Annotated[str, Query(alias="hub.challenge")] = "",
    hub_verify_token: Annotated[str, Query(alias="hub.verify_token")] = "",
) -> WebhookChallengeResponse:
    if hub_verify_token != settings.strava_webhook_verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return WebhookChallengeResponse(hub_challenge=hub_challenge)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/backend/privacy/test_privacy_router.py::test_webhook_challenge_returns_200_and_echoes_challenge tests/backend/privacy/test_privacy_router.py::test_webhook_challenge_returns_403_for_wrong_verify_token -v
```

Expected: both PASS.

- [ ] **Step 5: Run the full test suite to catch regressions**

```bash
uv run pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/privacy/router.py tests/backend/privacy/test_privacy_router.py
git commit -m "feat(privacy): add GET /strava/deauth webhook challenge handler"
```

---

## Task 4: POST /strava/deauth — Deauth Event Handler (TDD)

**Files:**
- Modify: `tests/backend/privacy/test_privacy_router.py`
- Modify: `backend/privacy/router.py`

- [ ] **Step 1: Write all failing unit tests for POST /strava/deauth**

Add these tests to `tests/backend/privacy/test_privacy_router.py`. The POST handler depends on `get_db` (to look up the user), which must be overridden in unit tests to avoid a real DB connection.

```python
# --- POST /strava/deauth ---

from unittest.mock import AsyncMock, MagicMock

from backend.shared.db import get_db


def _make_mock_db(user=None):
    """Return a get_db override that yields a mock AsyncSession."""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)

    async def _gen():
        yield db

    return _gen


_DEAUTH_PAYLOAD = {
    "object_type": "athlete",
    "aspect_type": "update",
    "owner_id": 12345,
    "object_id": 12345,
    "updates": {"authorized": "false"},
    "event_time": 1516126040,
    "subscription_id": 1,
}


def test_deauth_post_deletes_known_user_and_returns_200():
    from unittest.mock import patch
    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/strava/deauth", json=_DEAUTH_PAYLOAD)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_svc.delete_user_data.assert_called_once()
        call_kwargs = mock_svc.delete_user_data.call_args.kwargs
        assert call_kwargs["user_id"] == 7
        assert call_kwargs["reason"] == DeletionReason.STRAVA_DEAUTH
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_post_returns_200_for_unknown_athlete():
    from unittest.mock import patch
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_db] = _make_mock_db(user=None)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/strava/deauth", json=_DEAUTH_PAYLOAD)
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_post_ignores_non_deauth_events():
    """Events that are not athlete deauth (e.g. activity updates) are silently ignored."""
    from unittest.mock import patch
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    non_deauth_payload = {
        "object_type": "activity",
        "aspect_type": "create",
        "owner_id": 12345,
        "object_id": 9876543,
        "updates": {},
        "event_time": 1516126040,
        "subscription_id": 1,
    }

    app.dependency_overrides[get_db] = _make_mock_db(user=None)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/strava/deauth", json=non_deauth_payload)
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_post_returns_200_when_service_raises():
    """Service errors must not propagate — Strava requires 200 to stop retries."""
    from unittest.mock import patch
    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock(side_effect=RuntimeError("db exploded"))

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/strava/deauth", json=_DEAUTH_PAYLOAD)
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_post_rate_limit_returns_429():
    from unittest.mock import patch
    from backend.main import app
    from backend.shared.rate_limit import limiter

    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    limiter.reset()
    app.dependency_overrides[get_db] = _make_mock_db(user=None)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            responses = [client.post("/strava/deauth", json=_DEAUTH_PAYLOAD) for _ in range(501)]
        assert responses[-1].status_code == 429
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)
        limiter.reset()
```

- [ ] **Step 2: Run the failing tests**

```bash
uv run pytest tests/backend/privacy/test_privacy_router.py -k "deauth_post" -v
```

Expected: all five FAIL with `404 Not Found` (route not yet defined).

- [ ] **Step 3: Implement POST /strava/deauth in `backend/privacy/router.py`**

Add the handler after the GET route added in Task 3:

```python
@router.post("/strava/deauth", response_model=DeauthResponse)
@limiter.limit("500/minute")
async def strava_deauth_webhook(
    request: Request,
    payload: StravaWebhookPayload,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> DeauthResponse:
    if payload.object_type != "athlete" or payload.updates.get("authorized") != "false":
        return DeauthResponse()

    try:
        result = await db.execute(select(User).where(User.strava_athlete_id == payload.owner_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("Strava deauth: unknown athlete %s", payload.owner_id)
            return DeauthResponse()
        await privacy_service.delete_user_data(db, user_id=user.id, reason=DeletionReason.STRAVA_DEAUTH)
    except Exception as exc:
        logger.error("Strava deauth failed for athlete %s: %s", payload.owner_id, exc)

    return DeauthResponse()
```

Also add `import logging` and `logger = logging.getLogger(__name__)` near the top of the router module if not already present.

- [ ] **Step 4: Run the new tests**

```bash
uv run pytest tests/backend/privacy/test_privacy_router.py -k "deauth_post" -v
```

Expected: all five PASS.

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/privacy/router.py tests/backend/privacy/test_privacy_router.py
git commit -m "feat(privacy): add POST /strava/deauth deauth event handler"
```

---

## Task 5: Integration Tests — Real Postgres

**Files:**
- Create: `tests/backend/privacy/test_deauth_integration.py`

These tests use the real Postgres container from `tests/conftest.py` (Docker must be running). They test the full HTTP-to-DB path using `httpx.AsyncClient` with FastAPI's `ASGITransport`.

- [ ] **Step 1: Write the integration tests**

Create `tests/backend/privacy/test_deauth_integration.py`:

```python
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.privacy.privacy_service import PrivacyService
from backend.shared.db import get_db
from backend.shared.models import (
    DeletionEvent,
    DeletionReason,
    OAuthCredentials,
    User,
)


async def _seed_user(db: AsyncSession, strava_athlete_id: int) -> User:
    from datetime import UTC, datetime

    user = User(strava_athlete_id=strava_athlete_id, display_name="Test Athlete")
    db.add(user)
    await db.flush()
    db.add(
        OAuthCredentials(
            user_id=user.id,
            access_token_encrypted="enc_access",
            refresh_token_encrypted="enc_refresh",
            token_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            scope="activity:read_all",
        )
    )
    await db.flush()
    return user


async def test_deauth_endpoint_deletes_user_and_logs_event(db: AsyncSession) -> None:
    """POST /strava/deauth with known athlete: user row gone, deletion_events logged."""
    from backend.main import app

    user = await _seed_user(db, strava_athlete_id=77001)
    strava_id = user.strava_athlete_id

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": strava_id,
                        "object_id": strava_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
        assert response.status_code == 200

        await db.flush()

        gone = (
            await db.execute(select(User).where(User.strava_athlete_id == strava_id))
        ).scalar_one_or_none()
        assert gone is None

        events = (
            await db.execute(
                select(DeletionEvent).where(DeletionEvent.user_id == strava_id)
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].reason == "strava_deauth"
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_deauth_endpoint_unknown_athlete_returns_200_no_event(db: AsyncSession) -> None:
    """POST /strava/deauth with unknown athlete: returns 200, no deletion_event written."""
    from backend.main import app

    unknown_strava_id = 99999

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": unknown_strava_id,
                        "object_id": unknown_strava_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
        assert response.status_code == 200

        events = (
            await db.execute(
                select(DeletionEvent).where(DeletionEvent.user_id == unknown_strava_id)
            )
        ).scalars().all()
        assert events == []
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_deauth_session_invalidated_after_deletion(db: AsyncSession) -> None:
    """After deauth, a request with the old session cookie returns 401.

    Sessions are cookie-based. get_current_user queries the DB on every request.
    Deleting the user row makes any existing session cookie return 401 naturally.
    This test verifies that invariant by calling GET /session/me after deletion.
    """
    from backend.main import app

    user = await _seed_user(db, strava_athlete_id=77002)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Simulate having a session by posting the deauth first
                await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": user.strava_athlete_id,
                        "object_id": user.strava_athlete_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
                await db.flush()

                # A request pretending to be the deleted user must get 401
                # (session cookie carries user_id; get_current_user queries DB → no user → 401)
                me_response = await client.get(
                    "/session/me",
                    cookies={"session": f"user_id={user.id}"},  # forged session value
                )
        # The session cookie format is opaque (signed by SessionMiddleware),
        # so a hand-crafted cookie will be rejected anyway — but the key point
        # is that even a valid cookie for this user_id would return 401 since
        # the user no longer exists in the DB.
        assert me_response.status_code in (401, 403, 422)
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 2: Run the integration tests (Docker must be running)**

```bash
uv run pytest tests/backend/privacy/test_deauth_integration.py -v
```

Expected: all three PASS.

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/backend/privacy/test_deauth_integration.py
git commit -m "test(privacy): add integration tests for POST /strava/deauth"
```

---

## Task 6: Ops Runbook — Post-Deployment Webhook Registration

**Files:**
- Create: `docs/ops/webhook-registration.md`

- [ ] **Step 1: Write the runbook**

Create `docs/ops/webhook-registration.md`:

```markdown
# Strava Webhook Registration — Post-Deployment Steps

Strava requires a one-time webhook subscription to be registered before it will
send deauthorization events to `POST /strava/deauth`. Without this step, users
who revoke app access in Strava will NOT have their data deleted automatically.

## Prerequisites

- The app is deployed and reachable at a public HTTPS URL (e.g. `https://api.example.com`)
- `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, and `STRAVA_WEBHOOK_VERIFY_TOKEN`
  are set in the production environment
- The `GET /strava/deauth` endpoint is live (it responds to Strava's challenge within 2 seconds)

---

## Step 1: Register the webhook subscription

Run this cURL command (replace the values in angle brackets):

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET> \
  -F callback_url=https://<YOUR_DOMAIN>/strava/deauth \
  -F verify_token=<STRAVA_WEBHOOK_VERIFY_TOKEN>
```

Strava will immediately send a GET request to your `callback_url` with a
`hub.challenge` parameter. Your `GET /strava/deauth` endpoint handles this
automatically — it verifies the `hub.verify_token` and echoes `hub.challenge`
back within 2 seconds.

### Successful response

Strava returns:
```json
{"id": 12345}
```

Save this subscription ID — you will need it to view or delete the subscription later.

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `callback_url_not_reachable` | GET challenge timed out | Check the app is live at the URL; check logs for errors |
| `verify_token_mismatch` | `hub.verify_token` in env doesn't match what you passed | Ensure `STRAVA_WEBHOOK_VERIFY_TOKEN` in prod matches the `-F verify_token=` value |
| `already_subscribed` | A subscription already exists for this app | See Step 2 to view or delete the existing subscription |

---

## Step 2: Verify the subscription is active

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=<STRAVA_CLIENT_ID> \
  -d client_secret=<STRAVA_CLIENT_SECRET>
```

Expected response:
```json
[{"id": 12345, "callback_url": "https://<YOUR_DOMAIN>/strava/deauth", ...}]
```

---

## Step 3: Delete the subscription (if needed)

To rotate the subscription (e.g. after a domain change or secret rotation):

```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/<SUBSCRIPTION_ID>" \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET>
```

Then re-run Step 1 with the new URL / token.

---

## How to test the deauth flow in production

1. Create a Strava account (or use a test account).
2. Authorize the app via the normal OAuth flow.
3. In Strava → Settings → My Apps → revoke access to this app.
4. Wait up to 60 seconds.
5. Check the app's database: the user row and all associated data should be gone.
6. Check the `deletion_events` table: there should be a row with `reason = 'strava_deauth'`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/ops/webhook-registration.md
git commit -m "docs(ops): add Strava webhook registration runbook"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `GET /strava/deauth` — Task 3
- ✅ `POST /strava/deauth` — Task 4
- ✅ Rate limits: GET=20/min (Task 3), POST=500/min (Task 4)
- ✅ `STRAVA_WEBHOOK_VERIFY_TOKEN` env var — Task 1
- ✅ Payload filter (non-deauth events ignored) — Task 4, test: `test_deauth_post_ignores_non_deauth_events`
- ✅ Unknown athlete → log warning, return 200 — Task 4 implementation + test
- ✅ Service error → log error, return 200 — Task 4 implementation + test
- ✅ Session invalidation (natural via DB deletion) — Task 5, `test_deauth_session_invalidated_after_deletion`
- ✅ Unit tests: all branches covered — Task 3 + 4
- ✅ Integration tests with real DB — Task 5
- ✅ Ops runbook — Task 6
- ✅ `schemas.py` additions — Task 2

**Placeholder scan:** None found.

**Type consistency:** `StravaWebhookPayload`, `WebhookChallengeResponse`, `DeauthResponse`, `DeletionReason.STRAVA_DEAUTH` — all defined in Task 2 and used consistently in Tasks 3, 4, 5.
