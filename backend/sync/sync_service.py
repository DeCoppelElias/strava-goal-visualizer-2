from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.config import settings
from backend.shared.models import Activity, SyncState
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from backend.sync.strava_client import fetch_all_activities

COOLDOWN_SECONDS = settings.sync_cooldown_seconds


def _jan1_unix_timestamp() -> int:
    now = datetime.now(UTC)
    return int(datetime(now.year, 1, 1, tzinfo=UTC).timestamp())


class SyncService:
    def __init__(self, oauth_service: StravaOAuthService) -> None:
        self.oauth_service = oauth_service

    async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse:
        await self._check_cooldown(db, user_id)
        access_token = await self.oauth_service.ensure_fresh_token(db, user_id)
        raw = await fetch_all_activities(access_token, after=_jan1_unix_timestamp())
        runs = [a for a in raw if a.get("sport_type") == "Run"]
        if runs:
            await self._upsert_activities(db, user_id, runs)
        now = datetime.now(UTC)
        await self._upsert_sync_state(db, user_id, now)
        return SyncResponse(synced_activities=len(runs), last_sync_completed_at=now)

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
        now = datetime.now(UTC)
        rows = [
            {
                "user_id": user_id,
                "strava_activity_id": a["id"],
                "name": a["name"],
                "sport_type": a["sport_type"],
                "distance_meters": a["distance"],
                "moving_time_seconds": a["moving_time"],
                "start_date": datetime.fromisoformat(a["start_date"]),
                "updated_at": now,
            }
            for a in activities
        ]
        stmt = insert(Activity).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "strava_activity_id"],
            set_={
                "name": stmt.excluded.name,
                "sport_type": stmt.excluded.sport_type,
                "distance_meters": stmt.excluded.distance_meters,
                "moving_time_seconds": stmt.excluded.moving_time_seconds,
                "start_date": stmt.excluded.start_date,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await db.execute(stmt)

    async def _upsert_sync_state(
        self, db: AsyncSession, user_id: int, completed_at: datetime
    ) -> None:
        result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        state = result.scalar_one_or_none()
        if state is None:
            db.add(SyncState(user_id=user_id, last_sync_completed_at=completed_at))
        else:
            state.last_sync_completed_at = completed_at
