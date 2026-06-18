from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dashboard.dashboard_service import DashboardService
from backend.dashboard.schemas import ClubDashboardResponse, PersonalDashboardResponse
from backend.dependencies import get_dashboard_service
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.get("/dashboard/personal", response_model=PersonalDashboardResponse)
@limiter.limit("30/minute")
async def get_personal_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    dashboard_service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> PersonalDashboardResponse:
    return await dashboard_service.get_personal_dashboard(db, current_user.id)


@router.get("/dashboard/club/{club_id}", response_model=ClubDashboardResponse)
@limiter.limit("30/minute")
async def get_club_dashboard(
    request: Request,
    club_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    dashboard_service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> ClubDashboardResponse:
    return await dashboard_service.get_club_dashboard(db, current_user.id, club_id)
