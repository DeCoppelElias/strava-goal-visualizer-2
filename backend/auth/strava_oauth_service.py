from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.exceptions import InsufficientScopeError, OAuthStateError, StravaAPIError
from backend.auth.state_token_service import StateTokenService
from backend.shared.config import settings
from backend.shared.crypto import Crypto
from backend.shared.models import OAuthCredentials, User

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"  # noqa: S105
SCOPES = "activity:read_all,profile:read_all"
_REQUIRED_SCOPES = {"activity:read_all", "profile:read_all"}


class StravaOAuthService:
    def __init__(self, state_token_service: StateTokenService, crypto: Crypto) -> None:
        self.state_token_service = state_token_service
        self.crypto = crypto

    async def create_authorization_url(self, db: AsyncSession) -> str:
        state = await self.state_token_service.create_state_token(db)

        params = {
            "client_id": settings.strava_client_id,
            "redirect_uri": settings.strava_redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
        }

        return f"{STRAVA_AUTH_URL}?{urlencode(params)}"

    async def process_callback(self, db: AsyncSession, code: str, state: str) -> User:
        valid = await self.state_token_service.validate_and_consume_state_token(db, state)
        if not valid:
            raise OAuthStateError("Invalid or expired OAuth state token")

        token_data = await self._exchange_code_for_tokens(code)
        self._validate_scopes(token_data["scope"])

        athlete_id: int = token_data["athlete"]["id"]
        user = await self._upsert_user(db, athlete_id)
        await self._upsert_credentials(db, user, token_data)
        await db.commit()

        return user

    async def _exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    STRAVA_TOKEN_URL,
                    data={
                        "client_id": settings.strava_client_id,
                        "client_secret": settings.strava_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                    },
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as exc:
            raise StravaAPIError(f"Strava token exchange failed: {exc}") from exc

    def _validate_scopes(self, granted_scope: str) -> None:
        granted = set(granted_scope.split(","))
        if not _REQUIRED_SCOPES.issubset(granted):
            raise InsufficientScopeError(
                f"Required scopes {_REQUIRED_SCOPES} not granted; got: {granted_scope}"
            )

    async def _upsert_user(self, db: AsyncSession, strava_athlete_id: int) -> User:
        result = await db.execute(select(User).where(User.strava_athlete_id == strava_athlete_id))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(strava_athlete_id=strava_athlete_id)
            db.add(user)
            await db.flush()

        return user

    async def _upsert_credentials(
        self, db: AsyncSession, user: User, token_data: dict[str, Any]
    ) -> None:
        result = await db.execute(
            select(OAuthCredentials).where(OAuthCredentials.user_id == user.id)
        )
        creds = result.scalar_one_or_none()

        expires_at = datetime.fromtimestamp(token_data["expires_at"], tz=UTC)

        if creds is None:
            creds = OAuthCredentials(
                user_id=user.id,
                access_token_encrypted=self.crypto.encrypt(token_data["access_token"]),
                refresh_token_encrypted=self.crypto.encrypt(token_data["refresh_token"]),
                token_expires_at=expires_at,
                scope=token_data["scope"],
            )
            db.add(creds)
        else:
            creds.access_token_encrypted = self.crypto.encrypt(token_data["access_token"])
            creds.refresh_token_encrypted = self.crypto.encrypt(token_data["refresh_token"])
            creds.token_expires_at = expires_at
            creds.scope = token_data["scope"]
