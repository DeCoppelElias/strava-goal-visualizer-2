from fastapi import Depends

from backend.helpers.config import settings
from backend.helpers.crypto import Crypto
from backend.services.state_token_service import StateTokenService
from backend.services.strava_oauth_service import StravaOAuthService

_crypto = Crypto(settings.token_encryption_key)


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_crypto() -> Crypto:
    return _crypto


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service)
