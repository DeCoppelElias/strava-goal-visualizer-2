from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import Goal


class GoalService:
    async def get_goal(self, db: AsyncSession, user_id: int) -> Goal:
        result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal

    async def update_goal(self, db: AsyncSession, user_id: int, km: float) -> Goal:
        result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")
        goal.yearly_running_goal_km = Decimal(str(km))
        return goal
