from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from backend.oauth_state import (
    TOKEN_TTL_MINUTES,
    create_state_token,
    validate_and_consume_state_token,
)


@pytest.mark.asyncio
async def test_create_state_token_stores_token_and_expiration():
    # Arrange
    db = AsyncMock()
    before_creation = datetime.now(UTC)

    # Act
    token = await create_state_token(db)

    # Assert
    after_creation = datetime.now(UTC)

    assert isinstance(token, str)
    assert len(token) > 0

    db.execute.assert_called_once()
    db.commit.assert_called_once()

    # inspect SQL call
    query, params = db.execute.call_args.args

    assert "INSERT INTO oauth_state_tokens" in str(query)
    assert params["state_token"] == token

    expires_at = params["expires_at"]

    expected_min = before_creation + timedelta(minutes=TOKEN_TTL_MINUTES)
    expected_max = after_creation + timedelta(minutes=TOKEN_TTL_MINUTES)

    assert expected_min <= expires_at <= expected_max


@pytest.mark.asyncio
async def test_validate_valid_token_returns_true_and_deletes_token():
    # Arrange
    db = AsyncMock()

    future_expiry = datetime.now(UTC) + timedelta(minutes=5)

    result_mock = Mock()
    result_mock.fetchone.return_value = (future_expiry,)

    db.execute.return_value = result_mock

    # Act
    result = await validate_and_consume_state_token(
        db,
        "valid-token",
    )

    # Assert
    assert result is True
    assert db.execute.call_count == 2
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_validate_unknown_token_returns_false():
    # Arrange
    db = AsyncMock()

    result_mock = Mock()
    result_mock.fetchone.return_value = None

    db.execute.return_value = result_mock

    # Act
    result = await validate_and_consume_state_token(
        db,
        "unknown-token",
    )

    # Assert
    assert result is False
    db.execute.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_validate_expired_token_returns_false_and_deletes_token():
    # Arrange
    db = AsyncMock()

    expired_time = datetime.now(UTC) - timedelta(minutes=5)

    result_mock = Mock()
    result_mock.fetchone.return_value = (expired_time,)

    db.execute.return_value = result_mock

    # Act
    result = await validate_and_consume_state_token(
        db,
        "expired-token",
    )

    # Assert
    assert result is False
    assert db.execute.call_count == 2
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_consumed_token_cannot_be_reused():
    # Arrange
    db = AsyncMock()

    future_expiry = datetime.now(UTC) + timedelta(minutes=5)

    first_result = Mock()
    first_result.fetchone.return_value = (future_expiry,)

    second_result = Mock()
    second_result.fetchone.return_value = None

    db.execute.side_effect = [
        first_result,
        Mock(),  # DELETE
        second_result,  # second SELECT
    ]

    # Act
    first_call = await validate_and_consume_state_token(db, "token")
    second_call = await validate_and_consume_state_token(db, "token")

    # Assert
    assert first_call is True
    assert second_call is False
