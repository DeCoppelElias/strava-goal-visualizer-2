from backend.shared.exceptions import StravaAPIError as StravaAPIError
from backend.shared.exceptions import StravaUnauthorizedError as StravaUnauthorizedError


class SyncCooldownError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Sync cooldown active — retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds
