from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.shared.models import Club, ClubMembership, SyncState, User
from backend.sync.exceptions import SyncCooldownError
from backend.sync.sync_service import COOLDOWN_SECONDS, SyncService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def test_sync_cooldown_error_stores_retry_after_seconds():
    exc = SyncCooldownError(retry_after_seconds=300)
    assert exc.retry_after_seconds == 300


def test_sync_cooldown_error_is_exception():
    assert issubclass(SyncCooldownError, Exception)


# ---------------------------------------------------------------------------
# SyncService._check_cooldown
# ---------------------------------------------------------------------------


def _make_service() -> SyncService:
    mock_oauth = MagicMock()
    mock_oauth.ensure_fresh_token = AsyncMock(return_value="test-token")
    return SyncService(mock_oauth)


async def seed_user(db: AsyncSession, strava_athlete_id: int = 12345) -> User:
    """Insert a User row and flush so its autoincrement id is available for FKs."""
    user = User(strava_athlete_id=strava_athlete_id)
    db.add(user)
    await db.flush()
    return user


def _make_db_with_state(state: object) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = state
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


async def test_check_cooldown_does_not_raise_when_no_sync_state():
    svc = _make_service()
    db = _make_db_with_state(None)
    await svc._check_cooldown(db, user_id=1)  # must not raise


async def test_check_cooldown_raises_when_last_sync_was_recent():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=5)
    db = _make_db_with_state(state)

    with pytest.raises(SyncCooldownError) as exc_info:
        await svc._check_cooldown(db, user_id=1)

    assert 0 < exc_info.value.retry_after_seconds <= COOLDOWN_SECONDS


async def test_check_cooldown_does_not_raise_when_cooldown_expired():
    svc = _make_service()
    state = MagicMock()
    state.last_sync_completed_at = datetime.now(UTC) - timedelta(minutes=11)
    db = _make_db_with_state(state)

    await svc._check_cooldown(db, user_id=1)  # must not raise


# ---------------------------------------------------------------------------
# SyncService.run_sync — filter + return value
# ---------------------------------------------------------------------------


def _make_db_no_state() -> AsyncMock:
    """Returns a mock DB where all scalar lookups return None (first sync scenario)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


async def test_run_sync_returns_zero_count_when_no_activities():
    svc = _make_service()
    db = _make_db_no_state()

    with (
        patch("backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=[])),
        patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=[])),
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 0


async def test_run_sync_counts_only_run_activities():
    svc = _make_service()
    db = _make_db_no_state()

    mixed = [
        {
            "id": 1,
            "sport_type": "Run",
            "name": "Morning Run",
            "distance": 5000.0,
            "moving_time": 1800,
            "start_date": "2026-01-15T08:00:00Z",
        },
        {
            "id": 2,
            "sport_type": "Ride",
            "name": "Bike Ride",
            "distance": 20000.0,
            "moving_time": 3600,
            "start_date": "2026-01-16T09:00:00Z",
        },
        {
            "id": 3,
            "sport_type": "Run",
            "name": "Evening Run",
            "distance": 8000.0,
            "moving_time": 2700,
            "start_date": "2026-01-17T18:00:00Z",
        },
    ]

    with (
        patch("backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=mixed)),
        patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=[])),
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 2


async def test_run_sync_returns_zero_when_all_non_run():
    svc = _make_service()
    db = _make_db_no_state()

    activities = [
        {
            "id": 1,
            "sport_type": "Swim",
            "name": "Pool",
            "distance": 1000.0,
            "moving_time": 1200,
            "start_date": "2026-01-01T07:00:00Z",
        }
    ]

    with (
        patch("backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=activities)),
        patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=[])),
    ):
        result = await svc.run_sync(db, user_id=1)

    assert result.synced_activities == 0


async def test_upsert_sync_state_inserts_when_no_existing_state():
    svc = _make_service()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    now = datetime.now(UTC)
    await svc._upsert_sync_state(db, user_id=1, completed_at=now)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, SyncState)
    assert added.user_id == 1
    assert added.last_sync_completed_at == now


async def test_upsert_sync_state_updates_existing_state():
    svc = _make_service()
    existing_state = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_state
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    now = datetime.now(UTC)
    await svc._upsert_sync_state(db, user_id=1, completed_at=now)

    db.add.assert_not_called()
    assert existing_state.last_sync_completed_at == now


async def test_run_sync_propagates_token_refresh_error():
    from backend.auth.exceptions import TokenRefreshError

    mock_oauth = MagicMock()
    mock_oauth.ensure_fresh_token = AsyncMock(side_effect=TokenRefreshError("failed"))
    svc = SyncService(mock_oauth)
    db = _make_db_no_state()

    with pytest.raises(TokenRefreshError):
        await svc.run_sync(db, user_id=1)


# ---------------------------------------------------------------------------
# SyncService._sync_clubs
# ---------------------------------------------------------------------------


async def test_run_sync_calls_sync_clubs_with_access_token():
    """run_sync passes the resolved access token to _sync_clubs."""
    svc = _make_service()  # mock_oauth returns "test-token"
    db = _make_db_no_state()

    with (
        patch("backend.sync.sync_service.fetch_all_activities", AsyncMock(return_value=[])),
        patch.object(svc, "_sync_clubs", AsyncMock()) as mock_sync_clubs,
    ):
        await svc.run_sync(db, user_id=1)

    mock_sync_clubs.assert_called_once_with(db, 1, "test-token")


# ---------------------------------------------------------------------------
# SyncService._sync_clubs — integration tests (real PostgreSQL via `db` fixture)
# ---------------------------------------------------------------------------


async def test_sync_clubs_inserts_clubs_and_memberships(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()
    clubs = [{"id": 10, "name": "Club A"}, {"id": 20, "name": "Club B"}]

    with patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=clubs)):
        await svc._sync_clubs(db, user.id, "token")

    club_rows = (await db.execute(select(Club).order_by(Club.id))).scalars().all()
    assert [(c.id, c.name) for c in club_rows] == [(10, "Club A"), (20, "Club B")]

    membership_ids = (
        (
            await db.execute(
                select(ClubMembership.club_id)
                .where(ClubMembership.user_id == user.id)
                .order_by(ClubMembership.club_id)
            )
        )
        .scalars()
        .all()
    )
    assert membership_ids == [10, 20]


async def test_sync_clubs_removes_memberships_when_no_clubs(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "Club A"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")

    with patch("backend.sync.sync_service.fetch_athlete_clubs", AsyncMock(return_value=[])):
        await svc._sync_clubs(db, user.id, "token")

    remaining = (
        (await db.execute(select(ClubMembership).where(ClubMembership.user_id == user.id)))
        .scalars()
        .all()
    )
    assert remaining == []


async def test_sync_clubs_replaces_membership_set(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "A"}, {"id": 20, "name": "B"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 20, "name": "B"}, {"id": 30, "name": "C"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")

    membership_ids = (
        (
            await db.execute(
                select(ClubMembership.club_id)
                .where(ClubMembership.user_id == user.id)
                .order_by(ClubMembership.club_id)
            )
        )
        .scalars()
        .all()
    )
    assert membership_ids == [20, 30]


async def test_sync_clubs_upserts_club_name(db: AsyncSession) -> None:
    user = await seed_user(db)
    svc = _make_service()

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "Old Name"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")

    with patch(
        "backend.sync.sync_service.fetch_athlete_clubs",
        AsyncMock(return_value=[{"id": 10, "name": "New Name"}]),
    ):
        await svc._sync_clubs(db, user.id, "token")

    clubs = (await db.execute(select(Club).where(Club.id == 10))).scalars().all()
    assert len(clubs) == 1
    assert clubs[0].name == "New Name"
