import logging
from typing import Any

import httpx

from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError

logger = logging.getLogger(__name__)

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


async def fetch_activities(
    access_token: str,
    *,
    after: int | None = None,
    page: int = 1,
    per_page: int = 200,
) -> list[dict[str, Any]]:
    params: dict[str, int] = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after

    logger.info("Fetching Strava activities page=%d", page)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                STRAVA_ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            if response.status_code == 401:
                raise StravaUnauthorizedError("Strava returned 401 — token invalid or expired")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise StravaAPIError(f"Strava API error: {exc}") from exc
            return response.json()  # type: ignore[no-any-return]
    except httpx.RequestError as exc:
        raise StravaAPIError(f"Network error fetching Strava activities: {exc}") from exc


async def fetch_all_activities(
    access_token: str,
    *,
    after: int | None = None,
) -> list[dict[str, Any]]:
    all_activities: list[dict[str, Any]] = []
    page = 1
    per_page = 200
    while True:
        page_results = await fetch_activities(
            access_token,
            after=after,
            page=page,
            per_page=per_page,
        )
        all_activities.extend(page_results)
        if len(page_results) < per_page:
            break
        page += 1
    return all_activities
