from backend.shared.models import OAuthCredentials, OAuthStateToken
from sqlalchemy import inspect as sa_inspect


def test_oauth_credentials_token_expires_at_is_timezone_aware():
    col = sa_inspect(OAuthCredentials).columns["token_expires_at"]
    assert col.type.timezone is True


def test_oauth_state_token_expires_at_is_timezone_aware():
    col = sa_inspect(OAuthStateToken).columns["expires_at"]
    assert col.type.timezone is True
