from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.auth.exceptions import TokenRefreshError
from backend.shared.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.shared.models import User
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from backend.shared.rate_limit import limiter

    limiter._storage.reset()
    yield


def _stub_user(user: User):
    async def _inner() -> User:
        return user

    return _inner


def _stub_401():
    async def _inner() -> User:
        raise HTTPException(status_code=401)

    return _inner


def _make_user() -> User:
    return User(id=1, strava_athlete_id=99999)


def _make_sync_response() -> SyncResponse:
    return SyncResponse(
        synced_activities=5,
        last_sync_completed_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC),
    )


def test_sync_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_sync_returns_200_and_response_when_successful():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(return_value=_make_sync_response())

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["synced_activities"] == 5
        assert "last_sync_completed_at" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_429_with_retry_after_on_cooldown():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=SyncCooldownError(retry_after_seconds=300))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "300"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_401_on_token_refresh_error():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=TokenRefreshError("refresh failed"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_401_on_strava_unauthorized():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=StravaUnauthorizedError("token invalid"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)


def test_sync_returns_502_on_strava_api_error():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_sync_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.run_sync = AsyncMock(side_effect=StravaAPIError("API down"))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_sync_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/sync")
        assert response.status_code == 502
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_sync_service, None)
