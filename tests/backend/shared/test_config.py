from backend.shared.config import Settings, settings


def _base_settings(**kwargs) -> Settings:
    defaults = {
        "frontend_origin": "http://localhost:5173",
        "database_url": "postgresql+asyncpg://x:x@localhost/x",
        "token_encryption_key": "key",
        "strava_client_id": "id",
        "strava_client_secret": "secret",
        "strava_redirect_uri": "http://localhost:8000/oauth/callback",
        "session_secret_key": "key",
        "strava_webhook_verify_token": "token",
    }
    return Settings(**{**defaults, **kwargs})


def test_session_cookie_secure_defaults_to_true():
    s = _base_settings()
    assert s.session_cookie_secure is True


def test_session_cookie_secure_can_be_set_false():
    s = _base_settings(session_cookie_secure=False)
    assert s.session_cookie_secure is False


def test_live_settings_session_cookie_secure_is_true():
    # conftest does not set SESSION_COOKIE_SECURE, so the default (True) is used
    assert settings.session_cookie_secure is True
