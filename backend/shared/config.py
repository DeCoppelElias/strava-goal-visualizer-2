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
    "STRAVA_REDIRECT_URI",
    # EPIC-2:   "SESSION_SECRET_KEY",
    # EPIC-2:   "STRAVA_CLIENT_SECRET",
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
    strava_redirect_uri: str


settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=os.environ["DATABASE_URL"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
)
