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
    # TASK-1.4: "DATABASE_URL"
    # EPIC-2:   "SESSION_SECRET_KEY", "TOKEN_ENCRYPTION_KEY"
    # EPIC-2:   "STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REDIRECT_URI"
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)


@dataclass(frozen=True)
class Settings:
    frontend_origin: str


settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
)
