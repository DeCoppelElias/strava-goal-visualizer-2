# TASK-3.3 — Token Refresh Utility Design

## Goal

Add `ensure_fresh_token` to `StravaOAuthService` so callers can obtain a valid access token without caring whether a refresh was needed.

## Architecture

No new file. The method lives on `StravaOAuthService` in `backend/auth/strava_oauth_service.py` because the class already owns `crypto`, `STRAVA_TOKEN_URL`, and the httpx call pattern.

`TokenRefreshError` is added to `backend/auth/exceptions.py` alongside the existing OAuth exceptions.

## Method Signature

```python
async def ensure_fresh_token(self, db: AsyncSession, user_id: int) -> str
```

Returns a decrypted, valid Strava access token. Never logs the token value.

## Logic

1. Load `OAuthCredentials` for `user_id` via `select`. If no row exists, raise `TokenRefreshError`.
2. If `token_expires_at - now(UTC) > 5 minutes`: decrypt `access_token_encrypted` and return it. No network call.
3. Otherwise, POST to `STRAVA_TOKEN_URL` with:
   - `grant_type=refresh_token`
   - `client_id`, `client_secret` from `settings`
   - `refresh_token` decrypted from `creds.refresh_token_encrypted`
4. On HTTP 401: raise `TokenRefreshError("Strava refresh rejected — credentials revoked")`.
5. On any other HTTP error: raise `TokenRefreshError` wrapping the original exception.
6. On success: update `creds.access_token_encrypted`, `creds.refresh_token_encrypted`, `creds.token_expires_at`; call `await db.commit()`; return new decrypted access token.

## Error Handling

- Missing credentials row → `TokenRefreshError`
- Strava 401 → `TokenRefreshError` (caller must invalidate the session)
- Any other Strava HTTP error → `TokenRefreshError`
- Tokens are never written to logs at any level

## Files Changed

| File | Change |
|------|--------|
| `backend/auth/exceptions.py` | Add `TokenRefreshError` |
| `backend/auth/strava_oauth_service.py` | Add `ensure_fresh_token` method |
| `tests/backend/auth/test_strava_oauth_service.py` | Add test cases (TDD) |

## Test Cases

| Scenario | Expected |
|----------|----------|
| Token expires more than 5 min from now | Returns decrypted token; no HTTP call |
| Token expires within 5 min (or already expired) | Calls Strava refresh; updates DB; returns new token |
| No `OAuthCredentials` row for user | Raises `TokenRefreshError` |
| Strava refresh returns 401 | Raises `TokenRefreshError` |
| Strava refresh returns 500 | Raises `TokenRefreshError` |

## Dependencies

- TASK-2.2 (`Crypto` utility) — already injected into `StravaOAuthService`
- TASK-2.1 (`OAuthCredentials` model) — already in `shared/models.py`
