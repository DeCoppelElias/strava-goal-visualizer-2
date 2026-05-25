from fastapi import Depends

from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.shared.config import settings
from backend.shared.crypto import Crypto

_crypto = Crypto(settings.token_encryption_key)


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_crypto() -> Crypto:
    return _crypto


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service)
