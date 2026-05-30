from datetime import UTC, datetime
from decimal import Decimal

from backend.shared.models import Activity, SyncState, User
from sqlalchemy import Index, UniqueConstraint


def test_activity_model_has_required_columns():
    activity = Activity(
        user_id=1,
        strava_activity_id=123456789,
        name="Morning Run",
        sport_type="Run",
        distance_meters=Decimal("5000.5"),
        moving_time_seconds=1800,
        start_date=datetime(2026, 1, 15, 7, 0, 0, tzinfo=UTC),
    )

    assert activity.user_id == 1
    assert activity.strava_activity_id == 123456789
    assert activity.name == "Morning Run"
    assert activity.sport_type == "Run"
    assert activity.distance_meters == Decimal("5000.5")
    assert activity.moving_time_seconds == 1800
    assert activity.start_date == datetime(2026, 1, 15, 7, 0, 0, tzinfo=UTC)


def test_activity_model_has_unique_constraint_on_user_and_strava_id():
    table_args = Activity.__table_args__
    unique_constraints = [a for a in table_args if isinstance(a, UniqueConstraint)]
    assert len(unique_constraints) == 1
    constraint = unique_constraints[0]
    col_names = {c.key for c in constraint.columns}
    assert col_names == {"user_id", "strava_activity_id"}


def test_activity_model_has_index_on_user_and_start_date():
    table_args = Activity.__table_args__
    indexes = [a for a in table_args if isinstance(a, Index)]
    assert len(indexes) == 1
    index = indexes[0]
    col_names = {c.key for c in index.columns}
    assert col_names == {"user_id", "start_date"}


def test_sync_state_model_has_required_columns():
    ts = datetime(2026, 5, 30, 10, 0, 0, tzinfo=UTC)
    state = SyncState(user_id=1, last_sync_completed_at=ts)

    assert state.user_id == 1
    assert state.last_sync_completed_at == ts


def test_sync_state_user_id_is_primary_key():
    pk_cols = {c.key for c in SyncState.__table__.primary_key.columns}
    assert pk_cols == {"user_id"}


def test_user_has_activities_relationship():
    assert hasattr(User, "activities")


def test_user_has_sync_state_relationship():
    assert hasattr(User, "sync_state")


def test_activity_has_created_at_and_updated_at():
    activity = Activity(
        user_id=1,
        strava_activity_id=42,
        name="Run",
        sport_type="Run",
        distance_meters=Decimal("1000"),
        moving_time_seconds=300,
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert hasattr(activity, "created_at")
    assert hasattr(activity, "updated_at")
