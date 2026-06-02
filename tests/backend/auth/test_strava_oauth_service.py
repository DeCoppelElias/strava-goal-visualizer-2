from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from backend.auth.exceptions import InsufficientScopeError, OAuthStateError, StravaAPIError
from backend.auth.strava_oauth_service import SCOPES, STRAVA_AUTH_URL, StravaOAuthService


def test_strava_api_error_is_same_class_in_auth_and_sync():
    from backend.auth.exceptions import StravaAPIError as AuthErr
    from backend.sync.exceptions import StravaAPIError as SyncErr

    assert AuthErr is SyncErr


_VALID_STRAVA_TOKEN_RESPONSE = {
    "access_token": "access_abc",
    "refresh_token": "refresh_xyz",
    "expires_at": 9999999999,
    "athlete": {"id": 11111111},
    "scope": "activity:read_all,profile:read_all",
}


@pytest.fixture
def mock_settings():
    with patch("backend.auth.strava_oauth_service.settings") as mock:
        mock.strava_client_id = "test_client_id"
        mock.strava_client_secret = "test_client_secret"
        mock.strava_redirect_uri = "http://localhost/callback"
        yield mock


@pytest.fixture
def mock_crypto():
    crypto = MagicMock()
    crypto.encrypt.side_effect = lambda s: f"enc_{s}"
    return crypto


def _patch_httpx(
    response_json: dict | None = None, raise_for_status: Exception | None = None
) -> MagicMock:
    """Returns a patch context manager for httpx.AsyncClient used in strava_oauth_service."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_json or {}
    if raise_for_status is not None:
        mock_response.raise_for_status.side_effect = raise_for_status

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("backend.auth.strava_oauth_service.httpx.AsyncClient", mock_cls)


def _make_db(existing_user=None, existing_creds=None) -> AsyncMock:
    """Returns a mocked AsyncSession with configurable SELECT results."""
    db = AsyncMock()
    db.add = MagicMock()  # add() is sync in SQLAlchemy

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = existing_user
    creds_result = MagicMock()
    creds_result.scalar_one_or_none.return_value = existing_creds
    db.execute.side_effect = [user_result, creds_result]

    return db


@pytest.mark.asyncio
async def test_create_authorization_url_returns_strava_base_url(mock_settings, mock_crypto):
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "test_state_token"

    service = StravaOAuthService(state_token_service, mock_crypto)

    url = await service.create_authorization_url(db)

    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == STRAVA_AUTH_URL


@pytest.mark.asyncio
async def test_create_authorization_url_includes_correct_query_params(mock_settings, mock_crypto):
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "test_state_token"

    service = StravaOAuthService(state_token_service, mock_crypto)

    url = await service.create_authorization_url(db)

    params = parse_qs(urlparse(url).query)
    assert params["client_id"] == ["test_client_id"]
    assert params["redirect_uri"] == ["http://localhost/callback"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == [SCOPES]
    assert params["state"] == ["test_state_token"]


@pytest.mark.asyncio
async def test_create_authorization_url_uses_state_from_token_service(mock_settings, mock_crypto):
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "unique_state_xyz"

    service = StravaOAuthService(state_token_service, mock_crypto)

    url = await service.create_authorization_url(db)

    state_token_service.create_state_token.assert_called_once_with(db)
    params = parse_qs(urlparse(url).query)
    assert params["state"] == ["unique_state_xyz"]


@pytest.mark.asyncio
async def test_create_authorization_url_passes_db_to_token_service(mock_settings, mock_crypto):
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "some_state"

    service = StravaOAuthService(state_token_service, mock_crypto)

    await service.create_authorization_url(db)

    state_token_service.create_state_token.assert_called_once_with(db)


# ---------------------------------------------------------------------------
# process_callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_callback_raises_on_invalid_state(mock_settings, mock_crypto):
    state_token_service = AsyncMock()
    state_token_service.validate_and_consume_state_token.return_value = False

    service = StravaOAuthService(state_token_service, mock_crypto)

    with pytest.raises(OAuthStateError):
        await service.process_callback(_make_db(), code="code", state="bad_state")


@pytest.mark.asyncio
async def test_process_callback_raises_on_strava_http_error(mock_settings, mock_crypto):
    state_token_service = AsyncMock()
    state_token_service.validate_and_consume_state_token.return_value = True

    service = StravaOAuthService(state_token_service, mock_crypto)

    http_error = httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock())
    with _patch_httpx(raise_for_status=http_error), pytest.raises(StravaAPIError):
        await service.process_callback(_make_db(), code="code", state="valid_state")


@pytest.mark.asyncio
async def test_process_callback_raises_on_insufficient_scope(mock_settings, mock_crypto):
    state_token_service = AsyncMock()
    state_token_service.validate_and_consume_state_token.return_value = True

    partial_scope_response = {**_VALID_STRAVA_TOKEN_RESPONSE, "scope": "profile:read_all"}

    service = StravaOAuthService(state_token_service, mock_crypto)

    with _patch_httpx(response_json=partial_scope_response), pytest.raises(InsufficientScopeError):
        await service.process_callback(_make_db(), code="code", state="valid_state")


@pytest.mark.asyncio
async def test_process_callback_creates_new_user_on_first_login(mock_settings, mock_crypto):
    state_token_service = AsyncMock()
    state_token_service.validate_and_consume_state_token.return_value = True

    db = _make_db(existing_user=None, existing_creds=None)
    service = StravaOAuthService(state_token_service, mock_crypto)

    with _patch_httpx(response_json=_VALID_STRAVA_TOKEN_RESPONSE):
        user = await service.process_callback(db, code="code", state="valid_state")

    assert user.strava_athlete_id == _VALID_STRAVA_TOKEN_RESPONSE["athlete"]["id"]
    db.add.assert_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_callback_stores_encrypted_tokens(mock_settings, mock_crypto):
    state_token_service = AsyncMock()
    state_token_service.validate_and_consume_state_token.return_value = True

    db = _make_db(existing_user=None, existing_creds=None)
    service = StravaOAuthService(state_token_service, mock_crypto)

    with _patch_httpx(response_json=_VALID_STRAVA_TOKEN_RESPONSE):
        await service.process_callback(db, code="code", state="valid_state")

    mock_crypto.encrypt.assert_any_call("access_abc")
    mock_crypto.encrypt.assert_any_call("refresh_xyz")


# ---------------------------------------------------------------------------
# ensure_fresh_token
# ---------------------------------------------------------------------------


def _make_creds(*, expires_in_seconds: float) -> MagicMock:
    """Returns a mock OAuthCredentials with configurable expiry."""
    creds = MagicMock()
    creds.access_token_encrypted = "enc_access_abc"
    creds.refresh_token_encrypted = "enc_refresh_xyz"
    creds.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
    return creds


def _make_creds_db(creds: MagicMock | None) -> AsyncMock:
    """Returns a mocked AsyncSession whose single execute() returns the given creds."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = creds
    db.execute.return_value = result
    return db


def _patch_httpx_refresh(
    status_code: int = 200,
    response_json: dict | None = None,
) -> MagicMock:
    """Patches httpx.AsyncClient for the Strava token refresh POST call."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = response_json or {}
    if status_code not in (200, 401):
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("backend.auth.strava_oauth_service.httpx.AsyncClient", mock_cls)


@pytest.mark.asyncio
async def test_ensure_fresh_token_returns_token_without_refresh_when_not_expired(
    mock_settings, mock_crypto
):
    creds = _make_creds(expires_in_seconds=3600)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    token = await service.ensure_fresh_token(db, user_id=1)

    assert token == "access_abc"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_fresh_token_calls_strava_and_updates_db_when_expired(
    mock_settings, mock_crypto
):
    creds = _make_creds(expires_in_seconds=60)  # within 5-min buffer
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")
    mock_crypto.encrypt.side_effect = lambda s: f"enc_{s}"

    refresh_response = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_at": 9999999999,
    }
    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=200, response_json=refresh_response):
        token = await service.ensure_fresh_token(db, user_id=1)

    assert token == "new_access"
    assert creds.access_token_encrypted == "enc_new_access"
    assert creds.refresh_token_encrypted == "enc_new_refresh"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_when_no_credentials(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    db = _make_creds_db(None)
    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=99)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_on_strava_401(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=401), pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=1)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_on_strava_server_error(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=500), pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=1)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_token_refresh_error_on_network_error(
    mock_settings, mock_crypto
):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(
        side_effect=httpx.ConnectError("connection refused")
    )
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with (
        patch("backend.auth.strava_oauth_service.httpx.AsyncClient", mock_cls),
        pytest.raises(TokenRefreshError),
    ):
        await service.ensure_fresh_token(db, user_id=1)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_on_malformed_response_body(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with (
        _patch_httpx_refresh(status_code=200, response_json={}),
        pytest.raises(TokenRefreshError, match="missing expected fields"),
    ):
        await service.ensure_fresh_token(db, user_id=1)
