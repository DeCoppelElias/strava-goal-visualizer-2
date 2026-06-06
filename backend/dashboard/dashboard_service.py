import calendar
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.schemas import DailyDistancePoint, PersonalDashboardResponse
from backend.shared.models import Activity, Goal, SyncState


class DashboardService:
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

        activities_result = await db.execute(
            select(Activity.start_date, Activity.distance_meters)
            .where(
                Activity.user_id == user_id,
                Activity.start_date >= year_start,
            )
            .order_by(Activity.start_date.asc())
        )
        rows = activities_result.all()

        # Group by calendar date (multiple runs on the same day are merged).
        # Rows are DB-sorted ASC so dict insertion order is chronological.
        daily_totals: dict[str, float] = defaultdict(float)
        for row in rows:
            date_str = row.start_date.date().isoformat()
            daily_totals[date_str] += float(row.distance_meters)

        daily_series: list[DailyDistancePoint] = []
        cumulative = 0.0
        for date_str, day_meters in daily_totals.items():
            cumulative += day_meters / 1000
            daily_series.append(
                DailyDistancePoint(date=date_str, cumulative_km=round(cumulative, 3))
            )

        sum_meters = sum(float(r.distance_meters) for r in rows)
        goal_km = float(goal.yearly_running_goal_km)
        distance_to_date_km = sum_meters / 1000
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
            daily_series=daily_series,
        )
