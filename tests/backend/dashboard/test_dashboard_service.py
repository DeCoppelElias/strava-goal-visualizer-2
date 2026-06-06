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


def _make_db_for_dashboard(sync_state: object, goal: object, sum_meters: object) -> AsyncMock:
    """Mock db for get_personal_dashboard: 3 sequential execute() calls."""
    sync_result = MagicMock()
    sync_result.scalar_one_or_none.return_value = sync_state

    goal_result = MagicMock()
    goal_result.scalar_one_or_none.return_value = goal

    sum_result = MagicMock()
    sum_result.scalar.return_value = sum_meters

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[sync_result, goal_result, sum_result])
    return db


_FIXED_NOW = _real_datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
# 2026-06-06 is day 157 of 365 (non-leap year)
# expected_pct = round(157/365*100, 2) = 43.01
# expected_km  = 365 * (157/365)       = 157.0


async def test_get_personal_dashboard_raises_404_when_no_sync_state():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=None, goal=_make_goal(), sum_meters=None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not_synced"


async def test_get_personal_dashboard_raises_404_when_no_goal():
    svc = DashboardService()
    db = _make_db_for_dashboard(sync_state=_make_sync_state(), goal=None, sum_meters=None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_personal_dashboard(db, user_id=1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Goal not found"


async def test_get_personal_dashboard_returns_zero_when_no_activities():
    svc = DashboardService()
    db = _make_db_for_dashboard(
        sync_state=_make_sync_state(),
        goal=_make_goal(365.0),
        sum_meters=None,
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
        sum_meters=Decimal("200000"),
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
        sum_meters=Decimal("142500"),
    )
    with patch("backend.dashboard.dashboard_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.side_effect = _real_datetime
        result = await svc.get_personal_dashboard(db, user_id=1)
    assert result.distance_to_date_km == 142.5
    assert result.progress_pct == 39.04
    assert result.on_pace is False
    assert result.expected_pct == 43.01
