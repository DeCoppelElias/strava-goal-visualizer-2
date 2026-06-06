from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_goal_service
from backend.goals.goals_service import GoalService
from backend.goals.schemas import GoalResponse, PersonalDashboardResponse, UpdateGoalRequest
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.get("/goals", response_model=GoalResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_goals(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> GoalResponse:
    goal = await goal_service.get_goal(db, current_user.id)
    return GoalResponse(yearly_running_goal_km=float(goal.yearly_running_goal_km))


@router.put("/goals", response_model=GoalResponse)
@limiter.limit("10/minute")  # type: ignore[misc]
async def update_goals(
    request: Request,
    body: UpdateGoalRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> GoalResponse:
    goal = await goal_service.update_goal(db, current_user.id, body.yearly_running_goal_km)
    return GoalResponse(yearly_running_goal_km=float(goal.yearly_running_goal_km))


@router.get("/dashboard/personal", response_model=PersonalDashboardResponse)
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_personal_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    goal_service: GoalService = Depends(get_goal_service),  # noqa: B008
) -> PersonalDashboardResponse:
    return await goal_service.get_personal_dashboard(db, current_user.id)
