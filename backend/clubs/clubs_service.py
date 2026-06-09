from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import Club, ClubMembership


class ClubsService:
    async def get_clubs(self, db: AsyncSession, user_id: int) -> list[Club]:
        result = await db.execute(
            select(Club)
            .join(ClubMembership, ClubMembership.club_id == Club.id)
            .where(ClubMembership.user_id == user_id)
        )
        return list(result.scalars().all())
