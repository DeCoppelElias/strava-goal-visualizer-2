from fastapi import Depends

from backend.auth.state_token_service import StateTokenService
from backend.auth.strava_oauth_service import StravaOAuthService
from backend.clubs.clubs_service import ClubsService
from backend.dashboard.dashboard_service import DashboardService
from backend.goals.goals_service import GoalService
from backend.shared.config import settings
from backend.shared.crypto import Crypto
from backend.sync.sync_service import SyncService

_crypto = Crypto(settings.token_encryption_key)


def get_state_token_service() -> StateTokenService:
    return StateTokenService()


def get_crypto() -> Crypto:
    return _crypto


def get_strava_oauth_service(
    state_token_service: StateTokenService = Depends(get_state_token_service),  # noqa: B008
) -> StravaOAuthService:
    return StravaOAuthService(state_token_service, _crypto)


def get_sync_service(
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> SyncService:
    return SyncService(strava_oauth_service)


def get_goal_service() -> GoalService:
    return GoalService()


def get_dashboard_service() -> DashboardService:
    return DashboardService()


def get_clubs_service() -> ClubsService:
    return ClubsService()
