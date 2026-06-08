import httpx
import pytest
from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError
from backend.sync.strava_client import (
    STRAVA_ACTIVITIES_URL,
    STRAVA_CLUBS_URL,
    fetch_activities,
    fetch_all_activities,
    fetch_athlete_clubs,
)

SAMPLE_ACTIVITIES = [{"id": 1, "name": "Morning Run"}, {"id": 2, "name": "Evening Run"}]


def test_strava_unauthorized_error_is_exception():
    assert issubclass(StravaUnauthorizedError, Exception)


def test_strava_api_error_is_exception():
    assert issubclass(StravaAPIError, Exception)


async def test_fetch_activities_returns_activity_list(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=SAMPLE_ACTIVITIES)
    )
    result = await fetch_activities("my-token")
    assert result == SAMPLE_ACTIVITIES


async def test_fetch_activities_sends_after_param_when_provided(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    await fetch_activities("my-token", after=1735689600)
    assert respx_mock.calls.last.request.url.params["after"] == "1735689600"


async def test_fetch_activities_omits_after_param_when_not_provided(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    await fetch_activities("my-token")
    assert "after" not in respx_mock.calls.last.request.url.params


async def test_fetch_activities_returns_empty_list_when_page_exhausted(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    result = await fetch_activities("my-token")
    assert result == []


async def test_fetch_activities_raises_unauthorized_on_401(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(StravaUnauthorizedError):
        await fetch_activities("bad-token")


async def test_fetch_activities_raises_api_error_on_500(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(StravaAPIError):
        await fetch_activities("my-token")


def test_strava_unauthorized_error_is_same_class_as_shared():
    from backend.shared.exceptions import StravaUnauthorizedError as SharedErr
    from backend.sync.exceptions import StravaUnauthorizedError as SyncErr

    assert SyncErr is SharedErr


async def test_fetch_activities_raises_api_error_on_network_error(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    with pytest.raises(StravaAPIError):
        await fetch_activities("my-token")


async def test_fetch_all_activities_combines_multiple_pages(respx_mock):
    page1 = [{"id": i} for i in range(200)]
    page2 = [{"id": i} for i in range(200, 400)]
    responses = iter(
        [
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
            httpx.Response(200, json=[]),
        ]
    )
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(side_effect=lambda _req: next(responses))
    result = await fetch_all_activities("my-token")
    assert result == page1 + page2
    assert len(respx_mock.calls) == 3


async def test_fetch_all_activities_returns_empty_on_no_activities(respx_mock):
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    result = await fetch_all_activities("my-token")
    assert result == []
    assert len(respx_mock.calls) == 1


async def test_fetch_all_activities_stops_after_single_full_page_followed_by_empty(respx_mock):
    full_page = [{"id": i} for i in range(200)]
    responses = iter(
        [
            httpx.Response(200, json=full_page),
            httpx.Response(200, json=[]),
        ]
    )
    respx_mock.get(STRAVA_ACTIVITIES_URL).mock(side_effect=lambda _req: next(responses))
    result = await fetch_all_activities("my-token")
    assert result == full_page
    assert len(respx_mock.calls) == 2


# ---------------------------------------------------------------------------
# fetch_athlete_clubs
# ---------------------------------------------------------------------------

SAMPLE_CLUBS = [{"id": 10, "name": "Running Club"}, {"id": 20, "name": "Trail Runners"}]


async def test_fetch_athlete_clubs_returns_club_list(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_CLUBS))
    result = await fetch_athlete_clubs("my-token")
    assert result == SAMPLE_CLUBS


async def test_fetch_athlete_clubs_returns_empty_list(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(return_value=httpx.Response(200, json=[]))
    result = await fetch_athlete_clubs("my-token")
    assert result == []


async def test_fetch_athlete_clubs_sends_per_page_200(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(return_value=httpx.Response(200, json=[]))
    await fetch_athlete_clubs("my-token")
    assert respx_mock.calls.last.request.url.params["per_page"] == "200"


async def test_fetch_athlete_clubs_raises_unauthorized_on_401(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(StravaUnauthorizedError):
        await fetch_athlete_clubs("bad-token")


async def test_fetch_athlete_clubs_raises_api_error_on_500(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(StravaAPIError):
        await fetch_athlete_clubs("my-token")


async def test_fetch_athlete_clubs_raises_api_error_on_network_error(respx_mock):
    respx_mock.get(STRAVA_CLUBS_URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(StravaAPIError):
        await fetch_athlete_clubs("my-token")
