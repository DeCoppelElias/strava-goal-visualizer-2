from datetime import UTC, datetime

from backend.clubs.clubs_service import ClubsService
from backend.shared.models import Club, ClubMembership, User
from sqlalchemy.ext.asyncio import AsyncSession


async def _seed_user(db: AsyncSession, strava_athlete_id: int) -> User:
    user = User(strava_athlete_id=strava_athlete_id)
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


async def test_get_clubs_returns_clubs_for_user(db: AsyncSession) -> None:
    svc = ClubsService()
    user = await _seed_user(db, strava_athlete_id=111)
    club_a = await _seed_club(db, club_id=1, name="Club A")
    club_b = await _seed_club(db, club_id=2, name="Club B")
    await _seed_membership(db, user_id=user.id, club_id=club_a.id)
    await _seed_membership(db, user_id=user.id, club_id=club_b.id)

    clubs = await svc.get_clubs(db, user.id)

    assert len(clubs) == 2
    assert {c.name for c in clubs} == {"Club A", "Club B"}


async def test_get_clubs_returns_empty_list_when_no_memberships(db: AsyncSession) -> None:
    svc = ClubsService()
    user = await _seed_user(db, strava_athlete_id=222)

    clubs = await svc.get_clubs(db, user.id)

    assert clubs == []


async def test_get_clubs_does_not_return_other_users_clubs(db: AsyncSession) -> None:
    svc = ClubsService()
    user_a = await _seed_user(db, strava_athlete_id=333)
    user_b = await _seed_user(db, strava_athlete_id=444)
    club = await _seed_club(db, club_id=3, name="User B Club")
    await _seed_membership(db, user_id=user_b.id, club_id=club.id)

    clubs = await svc.get_clubs(db, user_a.id)

    assert clubs == []
