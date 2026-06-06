import calendar
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.goals.schemas import PersonalDashboardResponse
from backend.shared.models import Activity, Goal, SyncState


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

    async def get_personal_dashboard(
        self, db: AsyncSession, user_id: int
    ) -> PersonalDashboardResponse:
        sync_result = await db.execute(select(SyncState).where(SyncState.user_id == user_id))
        sync_state = sync_result.scalar_one_or_none()
        if sync_state is None:
            raise HTTPException(status_code=404, detail="not_synced")

        goal_result = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goal = goal_result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")

        now = datetime.now(UTC)
        year_start = datetime(now.year, 1, 1, tzinfo=UTC)

        sum_result = await db.execute(
            select(func.sum(Activity.distance_meters)).where(
                Activity.user_id == user_id,
                Activity.start_date >= year_start,
            )
        )
        sum_meters = sum_result.scalar()

        goal_km = float(goal.yearly_running_goal_km)
        distance_to_date_km = float(sum_meters or 0) / 1000
        progress_pct = round(distance_to_date_km / goal_km * 100, 2)

        today = now.date()
        days_in_year = 366 if calendar.isleap(today.year) else 365
        day_of_year = today.timetuple().tm_yday
        expected_pct = round(day_of_year / days_in_year * 100, 2)
        on_pace = distance_to_date_km >= goal_km * (day_of_year / days_in_year)

        return PersonalDashboardResponse(
            goal_km=goal_km,
            distance_to_date_km=distance_to_date_km,
            progress_pct=progress_pct,
            on_pace=on_pace,
            expected_pct=expected_pct,
            last_sync_completed_at=sync_state.last_sync_completed_at,
        )
