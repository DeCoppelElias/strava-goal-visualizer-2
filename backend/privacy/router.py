import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.privacy.privacy_service import PrivacyService
from backend.privacy.schemas import (
    DeauthResponse,
    DeleteResponse,
    StravaWebhookPayload,
    WebhookChallengeResponse,
)
from backend.shared.config import settings
from backend.shared.db import get_db
from backend.shared.models import DeletionReason, User
from backend.shared.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize(obj: object) -> object:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@router.get("/strava/deauth", response_model=WebhookChallengeResponse)
@limiter.limit("20/minute")
async def strava_webhook_challenge(
    request: Request,
    hub_challenge: Annotated[str, Query(alias="hub.challenge")] = "",
    hub_verify_token: Annotated[str, Query(alias="hub.verify_token")] = "",
) -> WebhookChallengeResponse:
    if hub_verify_token != settings.strava_webhook_verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return WebhookChallengeResponse(hub_challenge=hub_challenge)  # type: ignore[call-arg]


@router.post("/strava/deauth", response_model=DeauthResponse)
@limiter.limit("500/minute")
async def strava_deauth_webhook(
    request: Request,
    payload: StravaWebhookPayload,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> DeauthResponse:
    if payload.object_type != "athlete" or payload.updates.get("authorized") != "false":
        return DeauthResponse()

    logger.info("Strava deauth webhook received for athlete %s", payload.owner_id)

    try:
        result = await db.execute(select(User).where(User.strava_athlete_id == payload.owner_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("Strava deauth: unknown athlete %s", payload.owner_id)
            return DeauthResponse()
        await privacy_service.delete_user_data(
            db, user_id=user.id, reason=DeletionReason.STRAVA_DEAUTH
        )
    except Exception as exc:
        logger.error("Strava deauth failed for athlete %s: %s", payload.owner_id, exc)

    return DeauthResponse()


@router.post("/privacy/export")
@limiter.limit("5/hour")
async def export_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> Response:
    data = await privacy_service.export_user_data(db, user_id=current_user.id)
    payload = json.dumps(data.model_dump(), default=_serialize, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="strava-export.json"'},
    )


@router.post("/privacy/delete", response_model=DeleteResponse)
@limiter.limit("5/hour")
async def delete_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> DeleteResponse:
    await privacy_service.delete_user_data(
        db, user_id=current_user.id, reason=DeletionReason.USER_INITIATED
    )
    request.session.clear()
    return DeleteResponse(deleted=True)
