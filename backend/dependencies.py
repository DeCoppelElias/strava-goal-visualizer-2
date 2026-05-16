from fastapi import Depends

from backend.services.state_token_service import StateTokenService
from backend.services.strava_oauth_service import StravaOAuthService


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(StateTokenService),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service)
