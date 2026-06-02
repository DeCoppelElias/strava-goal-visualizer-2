from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.models import SyncState
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse

COOLDOWN_SECONDS = 600


def _jan1_unix_timestamp() -> int:
    now = datetime.now(UTC)
    return int(datetime(now.year, 1, 1, tzinfo=UTC).timestamp())


class SyncService:
    def __init__(self, oauth_service: StravaOAuthService) -> None:
        self.oauth_service = oauth_service

    async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse:
        raise NotImplementedError

    async def _check_cooldown(self, db: AsyncSession, user_id: int) -> None:
        result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        state = result.scalar_one_or_none()
        if state is None:
            return
        elapsed = datetime.now(UTC) - state.last_sync_completed_at
        if elapsed < timedelta(seconds=COOLDOWN_SECONDS):
            raise SyncCooldownError(COOLDOWN_SECONDS - int(elapsed.total_seconds()))

    async def _upsert_activities(
        self, db: AsyncSession, user_id: int, activities: list[dict[str, Any]]
    ) -> None:
        raise NotImplementedError

    async def _upsert_sync_state(
        self, db: AsyncSession, user_id: int, completed_at: datetime
    ) -> None:
        raise NotImplementedError
