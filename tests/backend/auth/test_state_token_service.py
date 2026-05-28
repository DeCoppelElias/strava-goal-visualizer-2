from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.auth.state_token_service import TOKEN_TTL_MINUTES, StateTokenService
from backend.shared.models import OAuthStateToken


def _mock_db_with_token(token_obj: OAuthStateToken | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = token_obj
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_create_state_token_stores_token_and_expiration():
    db = AsyncMock()
    before = datetime.now(UTC)

    service = StateTokenService()
    token = await service.create_state_token(db)

    after = datetime.now(UTC)

    assert isinstance(token, str)
    assert len(token) > 0

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, OAuthStateToken)
    assert added.token == token

    expected_min = before + timedelta(minutes=TOKEN_TTL_MINUTES)
    expected_max = after + timedelta(minutes=TOKEN_TTL_MINUTES)
    assert expected_min <= added.expires_at <= expected_max

    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_validate_valid_token_returns_true_and_deletes_token():
    future_expiry = datetime.now(UTC) + timedelta(minutes=5)
    token_obj = OAuthStateToken(token="valid-token", expires_at=future_expiry)  # noqa: S106
    db = _mock_db_with_token(token_obj)

    service = StateTokenService()
    result = await service.validate_and_consume_state_token(db, "valid-token")

    assert result is True
    db.delete.assert_called_once_with(token_obj)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_validate_unknown_token_returns_false():
    db = _mock_db_with_token(None)

    service = StateTokenService()
    result = await service.validate_and_consume_state_token(db, "unknown-token")

    assert result is False
    db.delete.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_validate_expired_token_returns_false_and_deletes_token():
    expired = datetime.now(UTC) - timedelta(minutes=5)
    token_obj = OAuthStateToken(token="expired-token", expires_at=expired)  # noqa: S106
    db = _mock_db_with_token(token_obj)

    service = StateTokenService()
    result = await service.validate_and_consume_state_token(db, "expired-token")

    assert result is False
    db.delete.assert_called_once_with(token_obj)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_consumed_token_cannot_be_reused():
    future_expiry = datetime.now(UTC) + timedelta(minutes=5)
    token_obj = OAuthStateToken(token="token", expires_at=future_expiry)  # noqa: S106

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = token_obj

    second_result = MagicMock()
    second_result.scalar_one_or_none.return_value = None

    db = AsyncMock()
    db.execute.side_effect = [first_result, second_result]

    service = StateTokenService()
    first_call = await service.validate_and_consume_state_token(db, "token")
    second_call = await service.validate_and_consume_state_token(db, "token")

    assert first_call is True
    assert second_call is False
