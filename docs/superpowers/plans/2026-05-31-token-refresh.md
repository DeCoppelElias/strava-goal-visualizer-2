# TASK-3.3 — Token Refresh Utility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ensure_fresh_token` to `StravaOAuthService` so callers always get a valid Strava access token, refreshing silently when the stored token is near expiry.

**Architecture:** `ensure_fresh_token` lives as a method on the existing `StravaOAuthService` (which already holds `crypto`, `STRAVA_TOKEN_URL`, and the httpx call pattern). `TokenRefreshError` is added to `backend/auth/exceptions.py`. No new files, no new DI factory.

**Tech Stack:** Python 3.12, httpx 0.28, respx for HTTP mocking in tests, pytest-asyncio (auto mode)

---

### Task 1: Add TokenRefreshError and failing tests

**Files:**
- Modify: `backend/auth/exceptions.py`
- Modify: `tests/backend/auth/test_strava_oauth_service.py`

- [ ] Add `TokenRefreshError` to `backend/auth/exceptions.py`. The full updated file:

```python
class OAuthStateError(Exception):
    pass


class InsufficientScopeError(Exception):
    pass


class StravaAPIError(Exception):
    pass


class TokenRefreshError(Exception):
    pass
```

- [ ] Append the following to the end of `tests/backend/auth/test_strava_oauth_service.py` (after all existing tests). This adds helpers and 5 new test functions:

```python
# ---------------------------------------------------------------------------
# ensure_fresh_token
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta


def _make_creds(*, expires_in_seconds: float) -> MagicMock:
    """Returns a mock OAuthCredentials with configurable expiry."""
    creds = MagicMock()
    creds.access_token_encrypted = "enc_access_abc"
    creds.refresh_token_encrypted = "enc_refresh_xyz"
    creds.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
    return creds


def _make_creds_db(creds: MagicMock | None) -> AsyncMock:
    """Returns a mocked AsyncSession whose single execute() returns the given creds."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = creds
    db.execute.return_value = result
    return db


def _patch_httpx_refresh(
    status_code: int = 200,
    response_json: dict | None = None,
) -> MagicMock:
    """Patches httpx.AsyncClient for the Strava token refresh POST call."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = response_json or {}
    if status_code not in (200, 401):
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("backend.auth.strava_oauth_service.httpx.AsyncClient", mock_cls)


@pytest.mark.asyncio
async def test_ensure_fresh_token_returns_token_without_refresh_when_not_expired(
    mock_settings, mock_crypto
):
    creds = _make_creds(expires_in_seconds=3600)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)
    token = await service.ensure_fresh_token(db, user_id=1)

    assert token == "access_abc"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_fresh_token_calls_strava_and_updates_db_when_expired(
    mock_settings, mock_crypto
):
    creds = _make_creds(expires_in_seconds=60)  # within 5-min buffer
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")
    mock_crypto.encrypt.side_effect = lambda s: f"enc_{s}"

    refresh_response = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_at": 9999999999,
    }
    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=200, response_json=refresh_response):
        token = await service.ensure_fresh_token(db, user_id=1)

    assert token == "new_access"
    assert creds.access_token_encrypted == "enc_new_access"
    assert creds.refresh_token_encrypted == "enc_new_refresh"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_when_no_credentials(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    db = _make_creds_db(None)
    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=99)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_on_strava_401(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=401), pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=1)


@pytest.mark.asyncio
async def test_ensure_fresh_token_raises_on_strava_server_error(mock_settings, mock_crypto):
    from backend.auth.exceptions import TokenRefreshError

    creds = _make_creds(expires_in_seconds=60)
    db = _make_creds_db(creds)
    mock_crypto.decrypt.side_effect = lambda s: s.removeprefix("enc_")

    service = StravaOAuthService(AsyncMock(), mock_crypto)

    with _patch_httpx_refresh(status_code=500), pytest.raises(TokenRefreshError):
        await service.ensure_fresh_token(db, user_id=1)
```

- [ ] Run to verify the 5 new tests fail:

```
uv run pytest tests/backend/auth/test_strava_oauth_service.py -v -k "ensure_fresh"
```

Expected: 5 errors with `AttributeError: 'StravaOAuthService' object has no attribute 'ensure_fresh_token'`.

---

### Task 2: Implement ensure_fresh_token

**Files:**
- Modify: `backend/auth/strava_oauth_service.py`

- [ ] In `backend/auth/strava_oauth_service.py`, update the `datetime` import line to include `timedelta`:

```python
from datetime import UTC, datetime, timedelta
```

- [ ] In the same file, update the exceptions import to include `TokenRefreshError`:

```python
from backend.auth.exceptions import InsufficientScopeError, OAuthStateError, StravaAPIError, TokenRefreshError
```

- [ ] Add `ensure_fresh_token` as a method on `StravaOAuthService`, after the `revoke_tokens` method:

```python
    async def ensure_fresh_token(self, db: AsyncSession, user_id: int) -> str:
        result = await db.execute(
            select(OAuthCredentials).where(OAuthCredentials.user_id == user_id)
        )
        creds = result.scalar_one_or_none()

        if creds is None:
            raise TokenRefreshError(f"No OAuth credentials for user {user_id}")

        if creds.token_expires_at - datetime.now(UTC) > timedelta(minutes=5):
            return self.crypto.decrypt(creds.access_token_encrypted)

        refresh_token = self.crypto.decrypt(creds.refresh_token_encrypted)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            if response.status_code == 401:
                raise TokenRefreshError("Strava refresh rejected — credentials revoked")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TokenRefreshError(f"Strava refresh failed: {exc}") from exc
            token_data: dict[str, Any] = response.json()

        creds.access_token_encrypted = self.crypto.encrypt(token_data["access_token"])
        creds.refresh_token_encrypted = self.crypto.encrypt(token_data["refresh_token"])
        creds.token_expires_at = datetime.fromtimestamp(token_data["expires_at"], tz=UTC)
        await db.commit()

        return token_data["access_token"]  # type: ignore[no-any-return]
```

- [ ] Run the 5 new tests to verify they pass:

```
uv run pytest tests/backend/auth/test_strava_oauth_service.py -v -k "ensure_fresh"
```

Expected: 5 passed.

- [ ] Run the full test suite to check for regressions:

```
uv run pytest -v
```

Expected: 54 passed (49 existing + 5 new).

- [ ] Commit:

```
git add backend/auth/exceptions.py backend/auth/strava_oauth_service.py tests/backend/auth/test_strava_oauth_service.py
git commit -m "feat(auth): implement ensure_fresh_token on StravaOAuthService (TASK-3.3)"
```
