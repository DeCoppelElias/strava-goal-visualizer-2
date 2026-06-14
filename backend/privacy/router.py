import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.dependencies import get_privacy_service
from backend.privacy.privacy_service import PrivacyService
from backend.shared.db import get_db
from backend.shared.models import User
from backend.shared.rate_limit import limiter

router = APIRouter()


def _serialize(obj: object) -> object:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


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
