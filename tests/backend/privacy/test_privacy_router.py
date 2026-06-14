from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.shared.db import get_db
from backend.shared.models import DeletionReason, User


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


# --- POST /strava/deauth ---


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
