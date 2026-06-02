from backend.sync.exceptions import SyncCooldownError


def test_sync_cooldown_error_stores_retry_after_seconds():
    exc = SyncCooldownError(retry_after_seconds=300)
    assert exc.retry_after_seconds == 300


def test_sync_cooldown_error_is_exception():
    assert issubclass(SyncCooldownError, Exception)
