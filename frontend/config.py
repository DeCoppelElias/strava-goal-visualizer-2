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
    "API_BASE_URL",
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)


@dataclass(frozen=True)
class Settings:
    api_base_url: str


settings = Settings(
    api_base_url=os.environ["API_BASE_URL"],
)
