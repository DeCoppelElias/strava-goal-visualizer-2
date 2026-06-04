from backend.shared.models import Activity, OAuthCredentials, OAuthStateToken, User
from sqlalchemy import inspect as sa_inspect


def _tz(model, col):
    return sa_inspect(model).columns[col].type.timezone


def test_user_created_at_is_timezone_aware():
    assert _tz(User, "created_at") is True


def test_user_updated_at_is_timezone_aware():
    assert _tz(User, "updated_at") is True


def test_oauth_credentials_created_at_is_timezone_aware():
    assert _tz(OAuthCredentials, "created_at") is True


def test_oauth_credentials_updated_at_is_timezone_aware():
    assert _tz(OAuthCredentials, "updated_at") is True


def test_oauth_credentials_token_expires_at_is_timezone_aware():
    assert _tz(OAuthCredentials, "token_expires_at") is True


def test_oauth_state_token_created_at_is_timezone_aware():
    assert _tz(OAuthStateToken, "created_at") is True


def test_oauth_state_token_expires_at_is_timezone_aware():
    assert _tz(OAuthStateToken, "expires_at") is True


def test_activity_created_at_is_timezone_aware():
    assert _tz(Activity, "created_at") is True


def test_activity_updated_at_is_timezone_aware():
    assert _tz(Activity, "updated_at") is True


def test_activity_start_date_is_timezone_aware():
    assert _tz(Activity, "start_date") is True
