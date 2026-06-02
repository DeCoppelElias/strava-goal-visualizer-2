from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.sync.exceptions import SyncCooldownError
from backend.sync.sync_service import COOLDOWN_SECONDS, SyncService


def test_sync_cooldown_error_stores_retry_after_seconds():
    exc = SyncCooldownError(retry_after_seconds=300)
    assert exc.retry_after_seconds == 300


def test_sync_cooldown_error_is_exception():
    assert issubclass(SyncCooldownError, Exception)


# ---------------------------------------------------------------------------
# SyncService._check_cooldown
# ---------------------------------------------------------------------------


def _make_service() -> SyncService:
    mock_oauth = MagicMock()
    return SyncService(mock_oauth)


def _make_db_with_state(state: object) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = state
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


async def test_check_cooldown_does_not_raise_when_no_sync_state():
    svc = _make_service()
    db = _make_db_with_state(None)
    await svc._check_cooldown(db, user_id=1)  # must not raise


async def test_check_cooldown_raises_when_last_sync_was_recent():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=5)
    db = _make_db_with_state(state)

    with pytest.raises(SyncCooldownError) as exc_info:
        await svc._check_cooldown(db, user_id=1)

    assert 0 < exc_info.value.retry_after_seconds <= COOLDOWN_SECONDS


async def test_check_cooldown_does_not_raise_when_cooldown_expired():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=11)
    db = _make_db_with_state(state)

    await svc._check_cooldown(db, user_id=1)  # must not raise
