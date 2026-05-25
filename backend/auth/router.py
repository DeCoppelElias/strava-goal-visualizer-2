from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import AuthorizeResponse
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.dependencies import get_strava_oauth_service
from backend.shared.db import get_db
from backend.shared.rate_limit import limiter

router = APIRouter()


@router.post("/oauth/authorize", response_model=AuthorizeResponse)
@limiter.limit("10/minute")  # type: ignore[misc]
async def oauth_authorize(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> AuthorizeResponse:
    authorization_url = await strava_oauth_service.create_authorization_url(db)
    return AuthorizeResponse(authorization_url=authorization_url)
