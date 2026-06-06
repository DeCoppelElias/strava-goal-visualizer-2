from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.shared.models import Goal, User
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


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


def test_get_goals_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/goals")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_goals_returns_200_with_default_goal():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_goal = AsyncMock(return_value=_make_goal(365.0))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/goals")
        assert response.status_code == 200
        assert response.json()["yearly_running_goal_km"] == 365.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 500.0})
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_put_goals_returns_200_with_updated_value():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.update_goal = AsyncMock(return_value=_make_goal(500.0))

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.put("/goals", json={"yearly_running_goal_km": 500.0})
        assert response.status_code == 200
        assert response.json()["yearly_running_goal_km"] == 500.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_zero_km():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 0})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_negative_km():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": -10})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_put_goals_returns_422_for_km_above_100000():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_goal_service
    from backend.main import app

    mock_svc = MagicMock()
    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_goal_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put("/goals", json={"yearly_running_goal_km": 100_001})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_goal_service, None)


def test_personal_dashboard_response_schema_importable():
    from backend.goals.schemas import PersonalDashboardResponse  # noqa: F401
