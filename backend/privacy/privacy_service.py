import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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
