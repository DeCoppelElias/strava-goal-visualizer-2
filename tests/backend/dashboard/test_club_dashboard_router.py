from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.dashboard.schemas import ClubDashboardResponse, MemberProgressResponse
from backend.shared.models import User
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
    return User(id=1, strava_athlete_id=99999, display_name="Test T.")


def test_get_club_dashboard_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/club/1")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_club_dashboard_returns_403_for_non_member():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_club_dashboard = AsyncMock(
        side_effect=HTTPException(status_code=403, detail="not_a_member")
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/dashboard/club/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)


def test_get_club_dashboard_returns_200_with_club_progress():
    from backend.auth.dependencies import get_current_user
    from backend.dependencies import get_dashboard_service
    from backend.main import app

    mock_svc = MagicMock()
    mock_svc.get_club_dashboard = AsyncMock(
        return_value=ClubDashboardResponse(
            club_id=42,
            club_name="Road Runners",
            members=[
                MemberProgressResponse(
                    strava_athlete_id=100,
                    display_name="Alice A.",
                    distance_to_date_km=10.0,
                    goal_km=100.0,
                    progress_pct=10.0,
                    daily_series=[],
                )
            ],
        )
    )

    app.dependency_overrides[get_current_user] = _stub_user(_make_user())
    app.dependency_overrides[get_dashboard_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/dashboard/club/42")
        assert response.status_code == 200
        data = response.json()
        assert data["club_id"] == 42
        assert data["club_name"] == "Road Runners"
        assert len(data["members"]) == 1
        assert data["members"][0]["strava_athlete_id"] == 100
        assert data["members"][0]["display_name"] == "Alice A."
        assert data["members"][0]["distance_to_date_km"] == 10.0
        assert data["members"][0]["goal_km"] == 100.0
        assert data["members"][0]["progress_pct"] == 10.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_dashboard_service, None)
