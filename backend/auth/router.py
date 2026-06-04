import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.exceptions import InsufficientScopeError, OAuthStateError, StravaAPIError
from backend.auth.schemas import (
    AuthorizeResponse,
    LogoutResponse,
    RevokeResponse,
    SessionMeResponse,
)
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.dependencies import get_strava_oauth_service
from backend.shared.config import settings
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

logger = logging.getLogger(__name__)

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


@router.get("/oauth/callback")
@limiter.limit("10/minute")  # type: ignore[misc]
async def oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    scope: str = "",
    db: AsyncSession = Depends(get_db),  # noqa: B008
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> RedirectResponse:
    frontend = settings.frontend_origin

    if error:
        logger.warning("Strava OAuth returned error: %s", error)
        return RedirectResponse(url=f"{frontend}?error=strava_error")

    try:
        user = await strava_oauth_service.process_callback(db, code=code, state=state, scope=scope)
    except OAuthStateError:
        logger.warning("OAuth state validation failed — potential CSRF attempt")
        return RedirectResponse(url=f"{frontend}?error=auth_failed")
    except InsufficientScopeError:
        logger.warning("Insufficient Strava scopes granted")
        authorization_url = await strava_oauth_service.create_authorization_url(db)
        return RedirectResponse(url=authorization_url)
    except StravaAPIError as exc:
        logger.error("Strava API error during token exchange: %s", exc)
        return RedirectResponse(url=f"{frontend}?error=strava_error")

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(url=frontend)


@router.get("/session/me", response_model=SessionMeResponse)
async def session_me(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> SessionMeResponse:
    return SessionMeResponse(
        strava_athlete_id=current_user.strava_athlete_id,
        created_at=current_user.created_at,
    )


@router.post("/session/logout", response_model=LogoutResponse)
async def session_logout(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> LogoutResponse:
    request.session.clear()
    return LogoutResponse(ok=True)


@router.post("/oauth/revoke", response_model=RevokeResponse)
@limiter.limit("10/minute")  # type: ignore[misc]
async def oauth_revoke(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> RevokeResponse:
    await strava_oauth_service.revoke_tokens(db, user_id=current_user.id)
    request.session.clear()
    return RevokeResponse(ok=True)
