import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TOKEN_TTL_MINUTES = 10


class StateTokenService:
    def __init__(self, ttl_minutes: int = TOKEN_TTL_MINUTES) -> None:
        self.ttl_minutes = ttl_minutes

    async def create_state_token(self, db: AsyncSession) -> str:
        token = self._generate_state_token()
        expires_at = self._get_expiration_time()

        await self._store_state_token(db, token, expires_at)
        await db.commit()

        return token

    async def validate_and_consume_state_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> bool:
        expires_at = await self._get_state_token_expiry(db, token)

        if expires_at is None:
            return False

        await self._delete_state_token(db, token)
        await db.commit()

        return expires_at >= datetime.now(UTC)

    def _generate_state_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _get_expiration_time(self) -> datetime:
        return datetime.now(UTC) + timedelta(minutes=self.ttl_minutes)

    async def _store_state_token(
        self,
        db: AsyncSession,
        token: str,
        expires_at: datetime,
    ) -> None:
        await db.execute(
            text("""
                INSERT INTO oauth_state_tokens (
                    token,
                    expires_at
                )
                VALUES (
                    :token,
                    :expires_at
                )
            """),
            {
                "token": token,
                "expires_at": expires_at,
            },
        )

    async def _get_state_token_expiry(
        self,
        db: AsyncSession,
        token: str,
    ) -> datetime | None:
        result = await db.execute(
            text("""
                SELECT expires_at
                FROM oauth_state_tokens
                WHERE token = :token
            """),
            {"token": token},
        )

        row = result.fetchone()
        return None if row is None else row[0]

    async def _delete_state_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> None:
        await db.execute(
            text("""
                DELETE FROM oauth_state_tokens
                WHERE token = :token
            """),
            {"token": token},
        )
