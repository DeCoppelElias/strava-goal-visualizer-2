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
    return WebhookChallengeResponse(hub_challenge=hub_challenge)


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
