from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.auth.dependencies import get_current_user
from backend.shared.models import User
from fastapi import HTTPException


def _make_request(user_id: int | None) -> MagicMock:
    request = MagicMock()
    if user_id is None:
        request.session = {}
    else:
        request.session = {"user_id": user_id}
    return request


def _make_db(user: User | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_no_session():
    request = _make_request(user_id=None)
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_user_not_in_db():
    request = _make_request(user_id=42)
    db = _make_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_user_when_session_valid():
    user = User(id=1, strava_athlete_id=99999)
    request = _make_request(user_id=1)
    db = _make_db(user=user)

    result = await get_current_user(request, db)

    assert result is user


# ---------------------------------------------------------------------------
# GET /session/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_me_returns_401_when_unauthenticated():
    from backend.auth.dependencies import get_current_user
    from backend.main import app
    from fastapi.testclient import TestClient

    async def _raise_401():
        raise HTTPException(status_code=401)

    app.dependency_overrides[get_current_user] = _raise_401
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get("/session/me")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_session_me_returns_user_data_when_authenticated():
    from datetime import UTC, datetime

    from backend.auth.dependencies import get_current_user
    from backend.main import app
    from fastapi.testclient import TestClient

    created = datetime(2026, 1, 1, tzinfo=UTC)
    user = User(id=1, strava_athlete_id=12345678, created_at=created)

    async def _return_user():
        return user

    app.dependency_overrides[get_current_user] = _return_user
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/session/me")
        assert response.status_code == 200
        data = response.json()
        assert data["strava_athlete_id"] == 12345678
    finally:
        app.dependency_overrides.pop(get_current_user, None)
