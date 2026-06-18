import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.privacy.schemas import (
    ExportActivity,
    ExportClubMembership,
    ExportGoal,
    ExportSyncState,
    ExportUser,
    UserExportResponse,
)
from backend.shared.models import (
    Activity,
    ClubMembership,
    DeletionEvent,
    DeletionReason,
    Goal,
    OAuthCredentials,
    SyncState,
    User,
)

logger = logging.getLogger(__name__)


class PrivacyService:
    async def delete_user_data(
        self, db: AsyncSession, user_id: int, reason: DeletionReason
    ) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return

        strava_athlete_id = user.strava_athlete_id

        await db.execute(delete(Activity).where(Activity.user_id == user_id))
        await db.execute(delete(ClubMembership).where(ClubMembership.user_id == user_id))
        await db.execute(delete(OAuthCredentials).where(OAuthCredentials.user_id == user_id))
        await db.execute(delete(SyncState).where(SyncState.user_id == user_id))
        await db.execute(delete(Goal).where(Goal.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))

        db.add(DeletionEvent(user_id=strava_athlete_id, reason=reason))

        logger.info("User data deleted")

    async def export_user_data(self, db: AsyncSession, user_id: int) -> UserExportResponse:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        goal = (await db.execute(select(Goal).where(Goal.user_id == user_id))).scalar_one_or_none()
        sync = (
            await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        ).scalar_one_or_none()
        activities = (
            (await db.execute(select(Activity).where(Activity.user_id == user_id))).scalars().all()
        )
        memberships = (
            (await db.execute(select(ClubMembership).where(ClubMembership.user_id == user_id)))
            .scalars()
            .all()
        )

        return UserExportResponse(
            exported_at=datetime.now(UTC),
            user=ExportUser(
                strava_athlete_id=user.strava_athlete_id,
                display_name=user.display_name,
                created_at=user.created_at,
            ),
            goal=(
                ExportGoal(yearly_running_goal_km=float(goal.yearly_running_goal_km))
                if goal
                else None
            ),
            sync_state=(
                ExportSyncState(last_sync_completed_at=sync.last_sync_completed_at)
                if sync
                else None
            ),
            activities=[
                ExportActivity(
                    strava_activity_id=a.strava_activity_id,
                    name=a.name,
                    sport_type=a.sport_type,
                    distance_meters=float(a.distance_meters),
                    moving_time_seconds=a.moving_time_seconds,
                    start_date=a.start_date,
                )
                for a in activities
            ],
            club_memberships=[
                ExportClubMembership(club_id=m.club_id, synced_at=m.synced_at) for m in memberships
            ],
        )
