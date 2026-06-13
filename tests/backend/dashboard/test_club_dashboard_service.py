from datetime import UTC, datetime
from decimal import Decimal

import pytest
from backend.dashboard.dashboard_service import DashboardService
from backend.shared.models import Activity, Club, ClubMembership, Goal, User
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


async def _seed_user(db: AsyncSession, strava_athlete_id: int, display_name: str = "") -> User:
    user = User(strava_athlete_id=strava_athlete_id, display_name=display_name)
    db.add(user)
    await db.flush()
    return user


async def _seed_club(db: AsyncSession, club_id: int, name: str) -> Club:
    club = Club(id=club_id, name=name, updated_at=datetime.now(UTC))
    db.add(club)
    await db.flush()
    return club


async def _seed_membership(db: AsyncSession, user_id: int, club_id: int) -> ClubMembership:
    membership = ClubMembership(user_id=user_id, club_id=club_id, synced_at=datetime.now(UTC))
    db.add(membership)
    await db.flush()
    return membership


async def _seed_goal(db: AsyncSession, user_id: int, yearly_km: float) -> Goal:
    goal = Goal(user_id=user_id, yearly_running_goal_km=Decimal(str(yearly_km)))
    db.add(goal)
    await db.flush()
    return goal


_counter = 0


async def _seed_activity(
    db: AsyncSession, user_id: int, distance_meters: float, start_date: datetime
) -> Activity:
    global _counter
    _counter += 1
    activity = Activity(
        user_id=user_id,
        strava_activity_id=_counter,
        name="Morning Run",
        sport_type="Run",
        distance_meters=Decimal(str(distance_meters)),
        moving_time_seconds=3600,
        start_date=start_date,
    )
    db.add(activity)
    await db.flush()
    return activity


async def test_get_club_dashboard_returns_progress_for_all_members(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=1, name="Road Runners")
    user_a = await _seed_user(db, strava_athlete_id=100, display_name="Alice A.")
    user_b = await _seed_user(db, strava_athlete_id=200, display_name="Bob B.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    await _seed_goal(db, user_b.id, yearly_km=200.0)
    this_year = datetime(datetime.now(UTC).year, 3, 1, tzinfo=UTC)
    await _seed_activity(db, user_a.id, distance_meters=10_000, start_date=this_year)
    await _seed_activity(db, user_b.id, distance_meters=20_000, start_date=this_year)

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    assert result.club_id == club.id
    assert result.club_name == "Road Runners"
    assert len(result.members) == 2
    by_athlete = {m.strava_athlete_id: m for m in result.members}
    assert by_athlete[100].distance_to_date_km == 10.0
    assert by_athlete[100].goal_km == 100.0
    assert by_athlete[100].progress_pct == 10.0
    assert by_athlete[100].display_name == "Alice A."
    assert by_athlete[200].distance_to_date_km == 20.0
    assert by_athlete[200].goal_km == 200.0
    assert by_athlete[200].progress_pct == 10.0
    assert by_athlete[200].display_name == "Bob B."


async def test_get_club_dashboard_raises_403_if_requesting_user_not_a_member(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=2, name="Trail Blazers")
    user = await _seed_user(db, strava_athlete_id=300)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert exc_info.value.status_code == 403


async def test_get_club_dashboard_excludes_members_without_goal(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=3, name="Sprinters")
    user_a = await _seed_user(db, strava_athlete_id=400, display_name="Alice A.")
    user_b = await _seed_user(db, strava_athlete_id=500, display_name="Bob B.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    # user_b intentionally has no goal

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    assert len(result.members) == 1
    assert result.members[0].strava_athlete_id == 400


async def test_get_club_dashboard_includes_member_with_goal_but_no_activities(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=4, name="Beginners")
    user = await _seed_user(db, strava_athlete_id=600, display_name="Carol C.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert len(result.members) == 1
    assert result.members[0].distance_to_date_km == 0.0
    assert result.members[0].progress_pct == 0.0


async def test_get_club_dashboard_ignores_previous_year_activities(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=5, name="Marathoners")
    user = await _seed_user(db, strava_athlete_id=700, display_name="Dave D.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)
    last_year = datetime(datetime.now(UTC).year - 1, 6, 1, tzinfo=UTC)
    await _seed_activity(db, user.id, distance_meters=50_000, start_date=last_year)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert result.members[0].distance_to_date_km == 0.0


async def test_get_club_dashboard_raises_403_for_club_user_is_not_in(db: AsyncSession) -> None:
    svc = DashboardService()
    club_a = await _seed_club(db, club_id=6, name="Club A")
    club_b = await _seed_club(db, club_id=7, name="Club B")
    user = await _seed_user(db, strava_athlete_id=800)
    await _seed_membership(db, user.id, club_a.id)
    # user is in club_a but NOT club_b

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club_b.id)

    assert exc_info.value.status_code == 403


async def test_get_club_dashboard_includes_daily_series(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=10, name="Series Club")
    user_a = await _seed_user(db, strava_athlete_id=1000, display_name="Eve E.")
    user_b = await _seed_user(db, strava_athlete_id=1001, display_name="Frank F.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    await _seed_goal(db, user_b.id, yearly_km=200.0)
    year = datetime.now(UTC).year
    await _seed_activity(db, user_a.id, 10_000, datetime(year, 1, 5, tzinfo=UTC))
    await _seed_activity(db, user_a.id, 5_000, datetime(year, 1, 10, tzinfo=UTC))
    await _seed_activity(db, user_b.id, 20_000, datetime(year, 1, 10, tzinfo=UTC))

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    by_athlete = {m.strava_athlete_id: m for m in result.members}
    series_a = by_athlete[1000].daily_series
    assert len(series_a) == 2
    assert series_a[0].date == f"{year}-01-05"
    assert series_a[0].cumulative_km == 10.0
    assert series_a[1].date == f"{year}-01-10"
    assert series_a[1].cumulative_km == 15.0

    series_b = by_athlete[1001].daily_series
    assert len(series_b) == 1
    assert series_b[0].cumulative_km == 20.0


async def test_get_club_dashboard_empty_series_for_member_without_activities(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=11, name="Ghost Club")
    user = await _seed_user(db, strava_athlete_id=1100, display_name="Ghost G.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert result.members[0].daily_series == []
