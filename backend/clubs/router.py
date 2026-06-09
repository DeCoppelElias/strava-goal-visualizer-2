from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.clubs.clubs_service import ClubsService
from backend.clubs.schemas import ClubResponse
from backend.dependencies import get_clubs_service
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.get("/clubs", response_model=list[ClubResponse])
@limiter.limit("30/minute")  # type: ignore[misc]
async def get_clubs(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    clubs_service: ClubsService = Depends(get_clubs_service),  # noqa: B008
) -> list[ClubResponse]:
    clubs = await clubs_service.get_clubs(db, current_user.id)
    return [ClubResponse(id=c.id, name=c.name) for c in clubs]
