from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from backend.services.strava_oauth_service import SCOPES, STRAVA_AUTH_URL, StravaOAuthService


@pytest.fixture
def mock_settings():
    with patch("backend.services.strava_oauth_service.settings") as mock:
        mock.strava_client_id = "test_client_id"
        mock.strava_redirect_uri = "http://localhost/callback"
        yield mock


@pytest.mark.asyncio
async def test_create_authorization_url_returns_strava_base_url(mock_settings):
    # Arrange
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "test_state_token"

    service = StravaOAuthService(state_token_service)

    # Act
    url = await service.create_authorization_url(db)

    # Assert
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == STRAVA_AUTH_URL


@pytest.mark.asyncio
async def test_create_authorization_url_includes_correct_query_params(mock_settings):
    # Arrange
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "test_state_token"

    service = StravaOAuthService(state_token_service)

    # Act
    url = await service.create_authorization_url(db)

    # Assert
    params = parse_qs(urlparse(url).query)
    assert params["client_id"] == ["test_client_id"]
    assert params["redirect_uri"] == ["http://localhost/callback"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == [SCOPES]
    assert params["state"] == ["test_state_token"]


@pytest.mark.asyncio
async def test_create_authorization_url_uses_state_from_token_service(mock_settings):
    # Arrange
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "unique_state_xyz"

    service = StravaOAuthService(state_token_service)

    # Act
    url = await service.create_authorization_url(db)

    # Assert
    state_token_service.create_state_token.assert_called_once_with(db)
    params = parse_qs(urlparse(url).query)
    assert params["state"] == ["unique_state_xyz"]


@pytest.mark.asyncio
async def test_create_authorization_url_passes_db_to_token_service(mock_settings):
    # Arrange
    db = AsyncMock()
    state_token_service = AsyncMock()
    state_token_service.create_state_token.return_value = "some_state"

    service = StravaOAuthService(state_token_service)

    # Act
    await service.create_authorization_url(db)

    # Assert
    state_token_service.create_state_token.assert_called_once_with(db)
