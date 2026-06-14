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
