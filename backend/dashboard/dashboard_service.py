import calendar
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.schemas import (
    ClubDashboardResponse,
    DailyDistancePoint,
    MemberProgressResponse,
    PersonalDashboardResponse,
)
from backend.shared.models import Activity, Club, ClubMembership, Goal, SyncState, User


class DashboardService:
    @staticmethod
    def _build_daily_series(
        rows: list[tuple[datetime, Decimal]],
    ) -> list[DailyDistancePoint]:
        daily_totals: dict[str, float] = defaultdict(float)
        for start_date, distance_meters in rows:
            date_str = start_date.date().isoformat()
            daily_totals[date_str] += float(distance_meters)

        series: list[DailyDistancePoint] = []
        cumulative = 0.0
        for date_str, day_meters in daily_totals.items():
            cumulative += day_meters / 1000
            series.append(DailyDistancePoint(date=date_str, cumulative_km=round(cumulative, 3)))
        return series

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

        daily_series = self._build_daily_series(
            [(row.start_date, row.distance_meters) for row in rows]
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

    async def get_club_dashboard(
        self, db: AsyncSession, requesting_user_id: int, club_id: int
    ) -> ClubDashboardResponse:
        membership_result = await db.execute(
            select(ClubMembership).where(
                ClubMembership.user_id == requesting_user_id,
                ClubMembership.club_id == club_id,
            )
        )
        if membership_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="not_a_member")

        club_result = await db.execute(select(Club).where(Club.id == club_id))
        club = club_result.scalar_one_or_none()
        if club is None:
            raise HTTPException(status_code=404, detail="club_not_found")

        members_result = await db.execute(
            select(User)
            .join(ClubMembership, ClubMembership.user_id == User.id)
            .where(ClubMembership.club_id == club_id)
        )
        members = list(members_result.scalars().all())
        member_ids = [m.id for m in members]

        if not member_ids:
            return ClubDashboardResponse(club_id=club.id, club_name=club.name, members=[])

        now = datetime.now(UTC)
        year_start = datetime(now.year, 1, 1, tzinfo=UTC)

        activity_result = await db.execute(
            select(
                Activity.user_id,
                func.sum(Activity.distance_meters).label("total_meters"),
            )
            .where(
                Activity.user_id.in_(member_ids),
                Activity.start_date >= year_start,
            )
            .group_by(Activity.user_id)
        )
        distance_by_user: dict[int, float] = {
            row.user_id: float(row.total_meters) for row in activity_result.all()
        }

        goals_result = await db.execute(select(Goal).where(Goal.user_id.in_(member_ids)))
        goal_by_user: dict[int, Goal] = {g.user_id: g for g in goals_result.scalars().all()}

        progress_list: list[MemberProgressResponse] = []
        for member in members:
            goal = goal_by_user.get(member.id)
            if goal is None:
                continue
            goal_km = float(goal.yearly_running_goal_km)
            distance_km = distance_by_user.get(member.id, 0.0) / 1000
            progress_pct = round(distance_km / goal_km * 100, 2)
            progress_list.append(
                MemberProgressResponse(
                    strava_athlete_id=member.strava_athlete_id,
                    display_name=member.display_name,
                    distance_to_date_km=distance_km,
                    goal_km=goal_km,
                    progress_pct=progress_pct,
                )
            )

        return ClubDashboardResponse(
            club_id=club.id,
            club_name=club.name,
            members=progress_list,
        )
