from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.privacy.privacy_service import PrivacyService
from backend.shared.models import (
    Activity,
    Club,
    ClubMembership,
    DeletionEvent,
    DeletionReason,
    Goal,
    OAuthCredentials,
    SyncState,
    User,
)


async def _seed_full_user(db: AsyncSession, strava_athlete_id: int = 99001) -> User:
    """Insert a User with one row in every child table."""
    user = User(strava_athlete_id=strava_athlete_id, display_name="Test User")
    db.add(user)
    await db.flush()

    db.add(
        OAuthCredentials(
            user_id=user.id,
            access_token_encrypted="enc_access",
            refresh_token_encrypted="enc_refresh",
            token_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            scope="activity:read_all,profile:read_all",
        )
    )
    db.add(
        Activity(
            user_id=user.id,
            strava_activity_id=1001,
            name="Morning Run",
            sport_type="Run",
            distance_meters=5000,
            moving_time_seconds=1800,
            start_date=datetime(2026, 3, 1, tzinfo=UTC),
        )
    )
    db.add(SyncState(user_id=user.id, last_sync_completed_at=datetime(2026, 3, 1, tzinfo=UTC)))
    db.add(Goal(user_id=user.id, yearly_running_goal_km=500))

    club = Club(id=77, name="Road Runners", updated_at=datetime(2026, 1, 1, tzinfo=UTC))
    db.add(club)
    await db.flush()
    db.add(ClubMembership(user_id=user.id, club_id=77, synced_at=datetime(2026, 3, 1, tzinfo=UTC)))

    await db.flush()
    return user


async def test_delete_user_data_removes_all_rows(db: AsyncSession) -> None:
    user = await _seed_full_user(db)
    svc = PrivacyService()

    await svc.delete_user_data(db, user_id=user.id, reason=DeletionReason.USER_INITIATED)
    await db.flush()

    assert (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none() is None
    assert (await db.execute(select(Activity).where(Activity.user_id == user.id))).scalars().all() == []
    assert (await db.execute(select(OAuthCredentials).where(OAuthCredentials.user_id == user.id))).scalar_one_or_none() is None
    assert (await db.execute(select(SyncState).where(SyncState.user_id == user.id))).scalar_one_or_none() is None
    assert (await db.execute(select(Goal).where(Goal.user_id == user.id))).scalar_one_or_none() is None
    assert (await db.execute(select(ClubMembership).where(ClubMembership.user_id == user.id))).scalars().all() == []


async def test_delete_user_data_writes_audit_event(db: AsyncSession) -> None:
    user = await _seed_full_user(db, strava_athlete_id=99002)
    svc = PrivacyService()

    await svc.delete_user_data(db, user_id=user.id, reason=DeletionReason.USER_INITIATED)
    await db.flush()

    events = (await db.execute(select(DeletionEvent).where(DeletionEvent.user_id == 99002))).scalars().all()
    assert len(events) == 1
    assert events[0].reason == "user_initiated"
    assert events[0].deleted_at is not None


async def test_delete_user_data_strava_deauth_reason(db: AsyncSession) -> None:
    user = await _seed_full_user(db, strava_athlete_id=99003)
    svc = PrivacyService()

    await svc.delete_user_data(db, user_id=user.id, reason=DeletionReason.STRAVA_DEAUTH)
    await db.flush()

    events = (await db.execute(select(DeletionEvent).where(DeletionEvent.user_id == 99003))).scalars().all()
    assert len(events) == 1
    assert events[0].reason == "strava_deauth"


async def test_export_user_data_happy_path(db: AsyncSession) -> None:
    user = await _seed_full_user(db, strava_athlete_id=99010)
    svc = PrivacyService()

    result = await svc.export_user_data(db, user_id=user.id)

    assert result.user.strava_athlete_id == 99010
    assert result.user.display_name == "Test User"
    assert result.user.created_at is not None
    assert result.goal is not None
    assert result.goal.yearly_running_goal_km == 500.0
    assert result.sync_state is not None
    assert result.sync_state.last_sync_completed_at is not None
    assert len(result.activities) == 1
    assert result.activities[0].strava_activity_id == 1001
    assert result.activities[0].name == "Morning Run"
    assert result.activities[0].distance_meters == 5000.0
    assert len(result.club_memberships) == 1
    assert result.club_memberships[0].club_id == 77
    assert result.exported_at is not None
    # No token fields anywhere
    dumped = result.model_dump_json()
    assert "access_token_encrypted" not in dumped
    assert "refresh_token_encrypted" not in dumped


async def test_export_user_data_sparse_user(db: AsyncSession) -> None:
    user = User(strava_athlete_id=99011, display_name="Sparse User")
    db.add(user)
    await db.flush()
    svc = PrivacyService()

    result = await svc.export_user_data(db, user_id=user.id)

    assert result.user.strava_athlete_id == 99011
    assert result.goal is None
    assert result.sync_state is None
    assert result.activities == []
    assert result.club_memberships == []


async def test_delete_user_data_idempotent(db: AsyncSession) -> None:
    user = await _seed_full_user(db, strava_athlete_id=99004)
    user_id = user.id
    svc = PrivacyService()

    await svc.delete_user_data(db, user_id=user_id, reason=DeletionReason.USER_INITIATED)
    await db.flush()

    # Second call — user no longer exists — must not raise and must not add a second audit event
    await svc.delete_user_data(db, user_id=user_id, reason=DeletionReason.USER_INITIATED)
    await db.flush()

    events = (await db.execute(select(DeletionEvent).where(DeletionEvent.user_id == 99004))).scalars().all()
    assert len(events) == 1
