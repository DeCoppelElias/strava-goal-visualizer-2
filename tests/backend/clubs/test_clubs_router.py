from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.shared.models import Club, User
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


def _make_club(club_id: int, name: str) -> Club:
    club = Club()
    club.id = club_id
    club.name = name
    club.updated_at = datetime.now(UTC)
    return club


def test_get_clubs_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/clubs")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_clubs_returns_200_with_club_list():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_clubs_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_clubs = AsyncMock(
        return_value=[
            _make_club(1, "Road Runners"),
            _make_club(2, "Trail Blazers"),
        ]
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_clubs_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/clubs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0] == {"id": 1, "name": "Road Runners"}
        assert data[1] == {"id": 2, "name": "Trail Blazers"}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_clubs_service, None)


def test_get_clubs_returns_200_with_empty_list():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_clubs_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_clubs = AsyncMock(return_value=[])

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_clubs_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/clubs")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_clubs_service, None)
