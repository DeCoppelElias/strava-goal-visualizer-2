from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.goals.goals_service import GoalService
from backend.shared.models import Goal
from fastapi import HTTPException


def _make_db_with_goal(goal: object) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = goal
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _make_goal(km: float = 365.0) -> Goal:
    goal = Goal()
    goal.user_id = 1
    goal.yearly_running_goal_km = Decimal(str(km))
    return goal


async def test_get_goal_returns_goal_when_found():
    svc = GoalService()
    goal = _make_goal()
    db = _make_db_with_goal(goal)
    result = await svc.get_goal(db, user_id=1)
    assert result is goal


async def test_get_goal_raises_404_when_not_found():
    svc = GoalService()
    db = _make_db_with_goal(None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_goal(db, user_id=1)
    assert exc_info.value.status_code == 404


async def test_update_goal_sets_km_and_returns_goal():
    svc = GoalService()
    goal = _make_goal(365.0)
    db = _make_db_with_goal(goal)
    result = await svc.update_goal(db, user_id=1, km=500.0)
    assert result.yearly_running_goal_km == Decimal("500.0")
    assert result is goal


async def test_update_goal_raises_404_when_not_found():
    svc = GoalService()
    db = _make_db_with_goal(None)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update_goal(db, user_id=1, km=500.0)
    assert exc_info.value.status_code == 404


async def test_update_goal_does_not_commit():
    svc = GoalService()
    goal = _make_goal(365.0)
    db = _make_db_with_goal(goal)
    await svc.update_goal(db, user_id=1, km=500.0)
    db.commit.assert_not_called()
