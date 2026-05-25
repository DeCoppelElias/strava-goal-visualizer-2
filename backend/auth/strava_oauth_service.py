from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.state_token_service import StateTokenService
from backend.shared.config import settings

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
SCOPES = "activity:read_all,profile:read_all"


class StravaOAuthService:
    def __init__(self, state_token_service: StateTokenService) -> None:
        self.state_token_service = state_token_service

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
