import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TOKEN_TTL_MINUTES = 10


async def create_state_token(db: AsyncSession) -> str:
    token = _generate_state_token()
    expires_at = _get_expiration_time()

    await _store_state_token(db, token, expires_at)
    await db.commit()

    return token


async def validate_and_consume_state_token(
    db: AsyncSession,
    token: str,
) -> bool:
    expires_at = await _get_state_token_expiry(db, token)

    if expires_at is None:
        return False

    await _delete_state_token(db, token)
    await db.commit()

    return expires_at >= datetime.now(UTC)


def _generate_state_token() -> str:
    return secrets.token_urlsafe(32)


def _get_expiration_time() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=TOKEN_TTL_MINUTES)


async def _store_state_token(
    db: AsyncSession,
    token: str,
    expires_at: datetime,
) -> None:
    await db.execute(
        text("""
            INSERT INTO oauth_state_tokens (
                state_token,
                expires_at
            )
            VALUES (
                :state_token,
                :expires_at
            )
        """),
        {
            "state_token": token,
            "expires_at": expires_at,
        },
    )


async def _get_state_token_expiry(
    db: AsyncSession,
    token: str,
) -> datetime | None:
    result = await db.execute(
        text("""
            SELECT expires_at
            FROM oauth_state_tokens
            WHERE state_token = :state_token
        """),
        {"state_token": token},
    )

    row = result.fetchone()

    return None if row is None else row[0]


async def _delete_state_token(
    db: AsyncSession,
    token: str,
) -> None:
    await db.execute(
        text("""
            DELETE FROM oauth_state_tokens
            WHERE state_token = :state_token
        """),
        {"state_token": token},
    )
