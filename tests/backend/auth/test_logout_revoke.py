from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.auth.dependencies import get_current_user
from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.crypto import Crypto
from backend.shared.models import OAuthCredentials, User
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _stub_user(user: User):
    async def _inner():
        return user

    return _inner


def _stub_401():
    async def _inner():
        raise HTTPException(status_code=401)

    return _inner


# ---------------------------------------------------------------------------
# POST /session/logout
# ---------------------------------------------------------------------------


def test_logout_returns_200_and_ok_when_authenticated():
    from backend.main import app

    user = User(id=1, strava_athlete_id=99999)
    app.dependency_overrides[get_current_user] = _stub_user(user)
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/session/logout")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_logout_returns_401_when_unauthenticated():
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/session/logout")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_logout_is_idempotent():
    """Calling logout twice returns 200 both times."""
    from backend.main import app

    user = User(id=1, strava_athlete_id=99999)
    app.dependency_overrides[get_current_user] = _stub_user(user)
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            first = client.post("/session/logout")
            second = client.post("/session/logout")
        assert first.status_code == 200
        assert second.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_logout_rate_limit_returns_429():
    """Exceeding 10 req/min must yield 429."""
    from backend.main import app
    from backend.shared.rate_limit import limiter

    user = User(id=1, strava_athlete_id=99999)

    limiter.reset()
    app.dependency_overrides[get_current_user] = _stub_user(user)
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            responses = [client.post("/session/logout") for _ in range(11)]
        assert responses[-1].status_code == 429
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        limiter.reset()


# ---------------------------------------------------------------------------
# StravaOAuthService.revoke_tokens
# ---------------------------------------------------------------------------


def _make_service() -> StravaOAuthService:
    state_svc = MagicMock(spec=StateTokenService)
    crypto = MagicMock(spec=Crypto)
    crypto.decrypt.return_value = "decrypted_token"
    return StravaOAuthService(state_svc, crypto)


def _make_creds(user_id: int = 1) -> OAuthCredentials:
    return OAuthCredentials(
        id=1,
        user_id=user_id,
        access_token_encrypted="enc_access",
        refresh_token_encrypted="enc_refresh",
        token_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        scope="activity:read_all,profile:read_all",
    )


def _make_db(creds: OAuthCredentials | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = creds
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_revoke_tokens_calls_strava_and_deletes_credentials():
    service = _make_service()
    creds = _make_creds()
    db = _make_db(creds)

    with patch("backend.auth.strava_oauth_service.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_http
        mock_http.post.return_value = MagicMock(status_code=200)

        await service.revoke_tokens(db, user_id=1)

    mock_http.post.assert_called_once()
    call_kwargs = mock_http.post.call_args
    assert "deauthorize" in call_kwargs[0][0]
    assert call_kwargs[1]["data"]["access_token"] == "decrypted_token"

    db.delete.assert_called_once_with(creds)
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_tokens_is_idempotent_when_no_credentials():
    """If credentials were already deleted, revoke does nothing and returns cleanly."""
    service = _make_service()
    db = _make_db(creds=None)

    with patch("backend.auth.strava_oauth_service.httpx.AsyncClient") as mock_client_cls:
        await service.revoke_tokens(db, user_id=1)
        mock_client_cls.assert_not_called()

    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_tokens_deletes_credentials_even_if_strava_call_fails():
    """Local cleanup must succeed regardless of Strava API errors."""
    import httpx as _httpx

    service = _make_service()
    creds = _make_creds()
    db = _make_db(creds)

    with patch("backend.auth.strava_oauth_service.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_http
        mock_http.post.side_effect = _httpx.HTTPError("connection error")

        await service.revoke_tokens(db, user_id=1)

    db.delete.assert_called_once_with(creds)
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# POST /oauth/revoke
# ---------------------------------------------------------------------------


def test_revoke_returns_200_and_ok_when_authenticated():
    from backend.dependencies import get_strava_oauth_service
    from backend.main import app

    user = User(id=1, strava_athlete_id=99999)
    mock_svc = MagicMock()
    mock_svc.revoke_tokens = AsyncMock()

    app.dependency_overrides[get_current_user] = _stub_user(user)
    app.dependency_overrides[get_strava_oauth_service] = lambda: mock_svc
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.post("/oauth/revoke")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_svc.revoke_tokens.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_strava_oauth_service, None)


def test_revoke_returns_401_when_unauthenticated():
    from backend.main import app

    app.dependency_overrides[get_current_user] = _stub_401()
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/oauth/revoke")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
