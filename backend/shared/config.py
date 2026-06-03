import logging
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required environment variables.
# Add new required variables here as they are introduced in later tasks.
# ---------------------------------------------------------------------------
_REQUIRED_ENV_VARS: list[str] = [
    "FRONTEND_ORIGIN",
    "DATABASE_URL",
    "TOKEN_ENCRYPTION_KEY",
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REDIRECT_URI",
    "SESSION_SECRET_KEY",
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)


@dataclass(frozen=True)
class Settings:
    frontend_origin: str
    database_url: str
    token_encryption_key: str
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str
    session_secret_key: str
    sync_cooldown_seconds: int = 600


settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=os.environ["DATABASE_URL"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
    session_secret_key=os.environ["SESSION_SECRET_KEY"],
    sync_cooldown_seconds=int(os.environ.get("SYNC_COOLDOWN_SECONDS", "600")),
)
