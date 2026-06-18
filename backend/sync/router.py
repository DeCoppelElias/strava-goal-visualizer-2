import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.exceptions import TokenRefreshError
from backend.dependencies import get_sync_service
from backend.shared.db import get_db
from backend.shared.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.shared.models import User
from backend.shared.rate_limit import limiter
from backend.sync.exceptions import SyncCooldownError
from backend.sync.schemas import SyncResponse
from backend.sync.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
@limiter.limit("2/minute")
async def sync_activities(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    sync_service: SyncService = Depends(get_sync_service),  # noqa: B008
) -> SyncResponse:
    try:
        return await sync_service.run_sync(db, current_user.id)
    except SyncCooldownError as exc:
        raise HTTPException(
            status_code=429,
            detail="Sync cooldown active",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except TokenRefreshError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token refresh failed — please log in again",
        ) from exc
    except StravaUnauthorizedError as exc:
        raise HTTPException(
            status_code=401,
            detail="Strava authorization invalid — please log in again",
        ) from exc
    except StravaAPIError as exc:
        logger.error("Strava API error during sync for user %d: %s", current_user.id, exc)
        raise HTTPException(status_code=502, detail="Strava API error") from exc
