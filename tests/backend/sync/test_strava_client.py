from backend.sync.exceptions import StravaAPIError, StravaUnauthorizedError


def test_strava_unauthorized_error_is_exception():
    assert issubclass(StravaUnauthorizedError, Exception)


def test_strava_api_error_is_exception():
    assert issubclass(StravaAPIError, Exception)
