import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import OAuthStateToken

TOKEN_TTL_MINUTES = 10


class StateTokenService:
    def __init__(self, ttl_minutes: int = TOKEN_TTL_MINUTES) -> None:
        self.ttl_minutes = ttl_minutes

    async def create_state_token(self, db: AsyncSession) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=self.ttl_minutes)
        db.add(OAuthStateToken(token=token, expires_at=expires_at))
        return token

    async def validate_and_consume_state_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> bool:
        result = await db.execute(select(OAuthStateToken).where(OAuthStateToken.token == token))
        token_obj = result.scalar_one_or_none()

        if token_obj is None:
            return False

        await db.delete(token_obj)

        return token_obj.expires_at >= datetime.now(UTC)
