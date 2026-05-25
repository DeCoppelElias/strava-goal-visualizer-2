from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.db import get_db
from backend.shared.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    user_id: int | None = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user
