from datetime import UTC
from datetime import datetime as _real_datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.dashboard.dashboard_service import DashboardService
from backend.shared.models import Goal, SyncState
from fastapi import HTTPException


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


def _make_sync_state() -> SyncState:
    state = SyncState()
    state.user_id = 1
    state.last_sync_completed_at = _real_datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    return state


def _make_activity_row(dt: _real_datetime, meters: float) -> MagicMock:
    row = MagicMock()
    row.start_date = dt
    row.distance_meters = Decimal(str(meters))
    return row


def _make_db_for_dashboard(sync_state: object, goal: object, activity_rows: list) -> AsyncMock:
    """Mock db for get_personal_dashboard: 3 sequential execute() calls."""
    sync_result = MagicMock()
    sync_result.scalar_one_or_none.return_value = sync_state

    goal_result = MagicMock()
    goal_result.scalar_one_or_none.return_value = goal

    activities_result = MagicMock()
    activities_result.all.return_value = activity_rows

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[sync_result, goal_result, activities_result])
    return db


_FIXED_NOW = _real_datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
# 2026-06-06 is day 157 of 365 (non-leap year)
# expected_pct = round(157/365*100, 2) = 43.01
# expected_km  = 365 * (157/365)       = 157.0


async def test_get_personal_dashboard_raises_404_when_no_sync_state():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=None, goal=_make_goal(), activity_rows=[])
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not_synced"


async def test_get_personal_dashboard_raises_404_when_no_goal():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=_make_sync_state(), goal=None, activity_rows=[])
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Goal not found"


async def test_get_personal_dashboard_returns_zero_when_no_activities():
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=[],
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 0.0
    assert result.progress_pct == 0.0
    assert result.on_pace is False


async def test_get_personal_dashboard_on_pace_true_when_ahead():
    # 200 km done, expected = 157.0 km → on pace
    # progress_pct = round(200/365*100, 2) = 54.79
    svc = DashboardService()
    sync = _make_sync_state()
    db = _make_db_for_dashboard(
        sync_state=sync,
        goal=_make_goal(365.0),
        activity_rows=[
            _make_activity_row(_real_datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC), 200_000)
        ],
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.goal_km == 365.0
    assert result.distance_to_date_km == 200.0
    assert result.progress_pct == 54.79
    assert result.on_pace is True
    assert result.expected_pct == 43.01
    assert result.last_sync_completed_at == sync.last_sync_completed_at


async def test_get_personal_dashboard_on_pace_false_when_behind():
    # 142.5 km done, expected = 157.0 km → behind
    # progress_pct = round(142.5/365*100, 2) = 39.04
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=[
            _make_activity_row(_real_datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC), 142_500)
        ],
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 142.5
    assert result.progress_pct == 39.04
    assert result.on_pace is False
    assert result.expected_pct == 43.01


async def test_daily_series_empty_when_no_activities():
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=[],
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.daily_series == []


async def test_daily_series_single_activity():
    svc = DashboardService()
    act = _make_activity_row(_real_datetime(2026, 3, 15, 8, 0, 0, tzinfo=UTC), 10_000)
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=[act],
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert len(result.daily_series) == 1
    assert result.daily_series[0].date == "2026-03-15"
    assert result.daily_series[0].cumulative_km == 10.0


async def test_daily_series_multiple_days_cumulative():
    svc = DashboardService()
    rows = [
        _make_activity_row(_real_datetime(2026, 3, 1, 8, 0, 0, tzinfo=UTC), 5_000),
        _make_activity_row(_real_datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC), 10_000),
    ]
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=rows,
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert len(result.daily_series) == 2
    assert result.daily_series[0].date == "2026-03-01"
    assert result.daily_series[0].cumulative_km == 5.0
    assert result.daily_series[1].date == "2026-04-01"
    assert result.daily_series[1].cumulative_km == 15.0


async def test_daily_series_two_runs_same_day_merged():
    svc = DashboardService()
    rows = [
        _make_activity_row(_real_datetime(2026, 5, 10, 7, 0, 0, tzinfo=UTC), 3_000),
        _make_activity_row(_real_datetime(2026, 5, 10, 18, 0, 0, tzinfo=UTC), 7_000),
    ]
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        activity_rows=rows,
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert len(result.daily_series) == 1
    assert result.daily_series[0].date == "2026-05-10"
    assert result.daily_series[0].cumulative_km == 10.0
