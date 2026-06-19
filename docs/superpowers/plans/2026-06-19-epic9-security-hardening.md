# EPIC-9 Security & Privacy Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close four pre-launch security/privacy audit findings — one HIGH (Secure cookie) and three LOW — each shipped as its own commit.

**Architecture:** Four independent tasks touching config, a middleware flag, a Dockerfile, a webhook handler (with tests), and the privacy policy page. No migrations, no new routes, no new dependencies.

**Tech Stack:** FastAPI · Starlette SessionMiddleware · Python dataclasses (config) · pytest · React/TSX

---

## File Map

| File | What changes |
|------|-------------|
| `backend/shared/config.py` | Add `session_cookie_secure` (TASK-9.1) and `strava_webhook_subscription_id` (TASK-9.2) fields |
| `backend/main.py` | Pass `https_only=settings.session_cookie_secure` to `SessionMiddleware` |
| `.env.example` | Document `SESSION_COOKIE_SECURE` and `STRAVA_WEBHOOK_SUBSCRIPTION_ID` |
| `backend/privacy/schemas.py` | Add `subscription_id: int \| None = None` to `StravaWebhookPayload` |
| `backend/privacy/router.py` | Add subscription_id filter before any deletion logic |
| `docs/ops/webhook-registration.md` | Add step: copy returned `id` into `STRAVA_WEBHOOK_SUBSCRIPTION_ID` |
| `docs/design.md` | Fix wrong "verified by Strava signature" claim; add residual-risk note |
| `backend/Dockerfile` | Add `--proxy-headers --forwarded-allow-ips="*"` to CMD |
| `frontend/src/pages/PrivacyPolicyPage.tsx` | Disclose minimal deletion record in "How long we keep it" |
| `tests/backend/shared/test_config.py` | New — Settings field defaults |
| `tests/backend/privacy/test_privacy_router.py` | Add 4 subscription_id filter tests |
| `tests/backend/privacy/test_deauth_integration.py` | Add filter-active integration test |

---

## Task 1: TASK-9.1 — Session cookie `Secure` flag

**Files:**
- Modify: `backend/shared/config.py`
- Modify: `backend/main.py`
- Modify: `.env.example`
- Create: `tests/backend/shared/test_config.py`

- [ ] **Step 1.1: Write failing tests**

Create `tests/backend/shared/test_config.py`:

```python
from backend.shared.config import Settings, settings


def _base_settings(**kwargs) -> Settings:
    defaults = dict(
        frontend_origin="http://localhost:5173",
        database_url="postgresql+asyncpg://x:x@localhost/x",
        token_encryption_key="key",
        strava_client_id="id",
        strava_client_secret="secret",
        strava_redirect_uri="http://localhost:8000/oauth/callback",
        session_secret_key="key",
        strava_webhook_verify_token="token",
    )
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
```

- [ ] **Step 1.2: Run tests to verify they fail**

```
uv run pytest tests/backend/shared/test_config.py -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'session_cookie_secure'`

- [ ] **Step 1.3: Add `session_cookie_secure` to `config.py`**

In `backend/shared/config.py`, add the field to the `Settings` dataclass (after `sync_cooldown_seconds` for grouping optional fields together):

```python
@dataclass(frozen=True)
class Settings:
    frontend_origin: str
    database_url: str
    token_encryption_key: str
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str
    session_secret_key: str
    strava_webhook_verify_token: str
    sync_cooldown_seconds: int = 600
    session_cookie_secure: bool = True
```

And add the parse expression to the `settings` singleton (after `sync_cooldown_seconds`):

```python
settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=os.environ["DATABASE_URL"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
    session_secret_key=os.environ["SESSION_SECRET_KEY"],
    strava_webhook_verify_token=os.environ["STRAVA_WEBHOOK_VERIFY_TOKEN"],
    sync_cooldown_seconds=int(os.environ.get("SYNC_COOLDOWN_SECONDS", "600")),
    session_cookie_secure=os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    not in ("false", "0"),
)
```

- [ ] **Step 1.4: Wire into `main.py`**

In `backend/main.py`, change the `SessionMiddleware` call at line 57–62:

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=settings.session_cookie_secure,
    same_site="lax",
)
```

- [ ] **Step 1.5: Document in `.env.example`**

Add after the `# ---- Session ----` block (after `SESSION_SECRET_KEY=`):

```
# Set to false ONLY for local HTTP development. Production default is true (Secure cookie).
# SESSION_COOKIE_SECURE=false
```

- [ ] **Step 1.6: Run all tests**

```
uv run pytest tests/backend/shared/test_config.py tests/backend/ -v
```

Expected: all pass. If any auth tests involving session cookies fail, check that `https_only=True` is not causing Starlette to reject HTTP test requests — Starlette only adds the `Secure` attribute to the cookie header; it does not block HTTP requests.

- [ ] **Step 1.7: Commit**

```bash
git add backend/shared/config.py backend/main.py .env.example tests/backend/shared/test_config.py
git commit -m "feat(security): set Secure flag on session cookie via SESSION_COOKIE_SECURE env var"
```

---

## Task 2: TASK-9.2 — Deauth webhook `subscription_id` filter

**Files:**
- Modify: `backend/privacy/schemas.py`
- Modify: `backend/shared/config.py`
- Modify: `backend/privacy/router.py`
- Modify: `.env.example`
- Modify: `docs/ops/webhook-registration.md`
- Modify: `docs/design.md`
- Modify: `tests/backend/privacy/test_privacy_router.py`
- Modify: `tests/backend/privacy/test_deauth_integration.py`

- [ ] **Step 2.1: Write failing unit tests**

Append to `tests/backend/privacy/test_privacy_router.py`:

```python
# ---- subscription_id filter tests ----


def _active_settings(subscription_id: int):
    """Return a mock settings object with the filter enabled."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.strava_webhook_subscription_id = subscription_id
    return mock


def test_deauth_filter_active_matching_id_deletes_user():
    from unittest.mock import patch

    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            patch("backend.privacy.router.settings", _active_settings(99)),
            TestClient(app) as client,
        ):
            response = client.post(
                "/strava/deauth",
                json={**_DEAUTH_PAYLOAD, "subscription_id": 99},
            )
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_filter_active_mismatched_id_no_deletion(caplog):
    import logging
    from unittest.mock import patch

    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            patch("backend.privacy.router.settings", _active_settings(99)),
            caplog.at_level(logging.WARNING),
            TestClient(app) as client,
        ):
            response = client.post(
                "/strava/deauth",
                json={**_DEAUTH_PAYLOAD, "subscription_id": 999},  # wrong id
            )
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_not_called()
        assert "mismatch" in caplog.text.lower()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_filter_active_missing_id_no_deletion(caplog):
    import logging
    from unittest.mock import patch

    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    payload_no_sub_id = {
        "object_type": "athlete",
        "aspect_type": "update",
        "owner_id": 12345,
        "object_id": 12345,
        "updates": {"authorized": "false"},
        "event_time": 1516126040,
        # subscription_id intentionally absent
    }

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            patch("backend.privacy.router.settings", _active_settings(99)),
            caplog.at_level(logging.WARNING),
            TestClient(app) as client,
        ):
            response = client.post("/strava/deauth", json=payload_no_sub_id)
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_not_called()
        assert "mismatch" in caplog.text.lower()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)


def test_deauth_filter_unset_deletes_regardless_of_payload_id():
    """When STRAVA_WEBHOOK_SUBSCRIPTION_ID is unset, filter is skipped entirely."""
    from unittest.mock import patch

    from backend.main import app

    known_user = User(id=7, strava_athlete_id=12345)
    mock_svc = MagicMock()
    mock_svc.delete_user_data = AsyncMock()

    app.dependency_overrides[get_db] = _make_mock_db(user=known_user)
    app.dependency_overrides[get_privacy_service] = lambda: mock_svc
    try:
        with (
            patch("backend.main._run_migrations"),
            TestClient(app) as client,
        ):
            # No settings patch — filter is inactive (default)
            response = client.post(
                "/strava/deauth",
                json={**_DEAUTH_PAYLOAD, "subscription_id": 9999},
            )
        assert response.status_code == 200
        mock_svc.delete_user_data.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_privacy_service, None)
```

- [ ] **Step 2.2: Write failing integration test**

Append to `tests/backend/privacy/test_deauth_integration.py`:

```python
async def test_deauth_filter_active_matching_id_deletes(db: AsyncSession) -> None:
    """Filter active + matching subscription_id → user deleted, event logged."""
    from unittest.mock import patch, MagicMock

    from backend.main import app
    from backend.shared.db import get_db

    user = await _seed_user(db, strava_athlete_id=77003)
    strava_id = user.strava_athlete_id

    mock_settings = MagicMock()
    mock_settings.strava_webhook_subscription_id = 42

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch("backend.main._run_migrations"),
            patch("backend.privacy.router.settings", mock_settings),
        ):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": strava_id,
                        "object_id": strava_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 42,
                    },
                )
        assert response.status_code == 200

        await db.flush()

        gone = (
            await db.execute(select(User).where(User.strava_athlete_id == strava_id))
        ).scalar_one_or_none()
        assert gone is None

        events = (
            (await db.execute(select(DeletionEvent).where(DeletionEvent.user_id == strava_id)))
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].reason == "strava_deauth"
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 2.3: Run tests to verify they fail**

```
uv run pytest tests/backend/privacy/ -v -k "filter"
```

Expected: failures because `StravaWebhookPayload` has no `subscription_id` field and `settings` has no `strava_webhook_subscription_id`.

- [ ] **Step 2.4: Add `subscription_id` to `StravaWebhookPayload`**

In `backend/privacy/schemas.py`, update `StravaWebhookPayload`:

```python
class StravaWebhookPayload(BaseModel):
    object_type: str
    aspect_type: str
    owner_id: int
    updates: dict[str, str] = {}
    subscription_id: int | None = None
```

- [ ] **Step 2.5: Add `strava_webhook_subscription_id` to `config.py`**

In `backend/shared/config.py`, add the field to `Settings` (after `session_cookie_secure`):

```python
@dataclass(frozen=True)
class Settings:
    frontend_origin: str
    database_url: str
    token_encryption_key: str
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str
    session_secret_key: str
    strava_webhook_verify_token: str
    sync_cooldown_seconds: int = 600
    session_cookie_secure: bool = True
    strava_webhook_subscription_id: int | None = None
```

Add the parse expression to the `settings` singleton (after `session_cookie_secure`):

```python
settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=os.environ["DATABASE_URL"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
    session_secret_key=os.environ["SESSION_SECRET_KEY"],
    strava_webhook_verify_token=os.environ["STRAVA_WEBHOOK_VERIFY_TOKEN"],
    sync_cooldown_seconds=int(os.environ.get("SYNC_COOLDOWN_SECONDS", "600")),
    session_cookie_secure=os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    not in ("false", "0"),
    strava_webhook_subscription_id=int(os.environ["STRAVA_WEBHOOK_SUBSCRIPTION_ID"])
    if os.environ.get("STRAVA_WEBHOOK_SUBSCRIPTION_ID")
    else None,
)
```

- [ ] **Step 2.6: Add the filter to the deauth handler**

In `backend/privacy/router.py`, replace the `strava_deauth_webhook` function body. The filter check goes at the very top, before the `object_type`/`authorized` guards:

```python
@router.post("/strava/deauth", response_model=DeauthResponse)
@limiter.limit("500/minute")
async def strava_deauth_webhook(
    request: Request,
    payload: StravaWebhookPayload,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: PrivacyService = Depends(get_privacy_service),  # noqa: B008
) -> DeauthResponse:
    configured_id = settings.strava_webhook_subscription_id
    if configured_id is not None and payload.subscription_id != configured_id:
        logger.warning(
            "Deauth webhook rejected: subscription_id mismatch (got %s, expected %s)",
            payload.subscription_id,
            configured_id,
        )
        return DeauthResponse()

    if payload.object_type != "athlete" or payload.updates.get("authorized") != "false":
        return DeauthResponse()

    logger.info("Strava deauth webhook received for athlete %s", payload.owner_id)

    try:
        result = await db.execute(select(User).where(User.strava_athlete_id == payload.owner_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("Strava deauth: unknown athlete %s", payload.owner_id)
            return DeauthResponse()
        await privacy_service.delete_user_data(
            db, user_id=user.id, reason=DeletionReason.STRAVA_DEAUTH
        )
    except Exception as exc:
        logger.error("Strava deauth failed for athlete %s: %s", payload.owner_id, exc)

    return DeauthResponse()
```

- [ ] **Step 2.7: Run the filter tests**

```
uv run pytest tests/backend/privacy/ -v -k "filter"
```

Expected: all 5 new tests pass.

- [ ] **Step 2.8: Run the full privacy test suite to confirm no regressions**

```
uv run pytest tests/backend/privacy/ -v
```

Expected: all pass. Existing tests use `_DEAUTH_PAYLOAD` which has `subscription_id: 1`; since `STRAVA_WEBHOOK_SUBSCRIPTION_ID` is not set in the test environment, the filter is inactive and all existing tests continue to pass unmodified.

- [ ] **Step 2.9: Document `STRAVA_WEBHOOK_SUBSCRIPTION_ID` in `.env.example`**

Add after the `# ---- Strava webhook ----` block (after `STRAVA_WEBHOOK_VERIFY_TOKEN=`):

```
# Subscription ID returned by Strava when the webhook is registered (see docs/ops/webhook-registration.md).
# Only known after registration; leave unset to disable the subscription_id filter entirely.
# STRAVA_WEBHOOK_SUBSCRIPTION_ID=
```

- [ ] **Step 2.10: Update `docs/ops/webhook-registration.md`**

After the "### Successful response" block in Step 1 (after the `{"id": 12345}` json block), replace:

```markdown
Save this subscription ID — you will need it to view or delete the subscription later.
```

with:

```markdown
Copy the returned `id` into your production environment:

```bash
# In your Fly.io secrets (or equivalent):
STRAVA_WEBHOOK_SUBSCRIPTION_ID=12345
```

This activates the `subscription_id` filter on `POST /strava/deauth`: events whose `subscription_id` does not match are rejected with `200 OK` and no deletion occurs. If the ID is ever lost, recover it via the GET in Step 2.
```

- [ ] **Step 2.11: Update `docs/design.md`**

In section **9.3 Strava Deauthorization Callback**, replace the existing content:

```markdown
### 9.3 Strava Deauthorization Callback

- Strava sends a deauthorization event when a user revokes app access from within Strava.
- On receipt, the backend attempts to revoke stored tokens, erase all user data, and invalidate the active session.
- **Failure handling:** If the callback fails, the error is logged for operator manual resolution.
- This satisfies Strava's platform requirement and GDPR right to erasure.
- **Webhook authenticity:** Strava does not sign webhook events — there is no HMAC or per-event secret. A `subscription_id` filter provides a cheap speed bump: every genuine Strava event carries the `subscription_id` of the registered push subscription; events with a mismatched or absent `subscription_id` are logged and rejected with `200 OK` (no deletion). This is **not** a real authentication boundary — `subscription_id` is a guessable incrementing integer. **Residual risk:** a determined attacker who knows the victim's athlete ID and the subscription ID could trigger erasure; data is re-syncable on next login and no data exfiltration occurs. The alternative (verifying the deauth by calling Strava with the stored token before deleting) was rejected: a transient Strava failure during a genuine deauth would skip a required erasure, a worse GDPR outcome.
```

Also fix the authorization matrix entry in section **10** (currently incorrect — Strava does not verify with a signature):

Find:
```markdown
| `POST /strava/deauth` | Strava server (verified by Strava signature) | — |
```

Replace with:
```markdown
| `POST /strava/deauth` | Strava server (no signature; filtered by `subscription_id` when configured) | — |
```

- [ ] **Step 2.12: Commit**

```bash
git add backend/privacy/schemas.py backend/shared/config.py backend/privacy/router.py \
        .env.example docs/ops/webhook-registration.md docs/design.md \
        tests/backend/privacy/test_privacy_router.py tests/backend/privacy/test_deauth_integration.py
git commit -m "feat(security): add subscription_id filter on deauth webhook"
```

---

## Task 3: TASK-9.3 — Trust Fly.io proxy headers

**Files:**
- Modify: `backend/Dockerfile`

No application tests are needed — the change is a uvicorn flag that affects IP extraction at the HTTP layer.

- [ ] **Step 3.1: Update `backend/Dockerfile`**

Replace the last line:

```dockerfile
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

with:

```dockerfile
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
```

- [ ] **Step 3.2: Verify the full test suite still passes**

```
uv run pytest tests/ -v
```

Expected: all pass (Dockerfile changes don't affect Python tests).

- [ ] **Step 3.3: Commit**

```bash
git add backend/Dockerfile
git commit -m "fix(ops): trust Fly.io proxy headers for correct client IP in rate limiting and logs"
```

---

## Task 4: TASK-9.4 — Reconcile deletion audit log with privacy policy

**Files:**
- Modify: `frontend/src/pages/PrivacyPolicyPage.tsx`

Option A: update the policy wording to disclose the minimal retained deletion record.

- [ ] **Step 4.1: Update the "How long we keep it" section**

In `frontend/src/pages/PrivacyPolicyPage.tsx`, find the paragraph (around line 74):

```tsx
              <p>
                We keep your data for as long as you have an account. If you delete your account via
                the Privacy page, all your data is permanently erased immediately. If you revoke
                this app's access in your Strava settings, Strava notifies us and we automatically
                erase all your data.
              </p>
```

Replace with:

```tsx
              <p>
                We keep your data for as long as you have an account. If you delete your account via
                the Privacy page, all your data is permanently erased immediately — a minimal
                deletion record (a pseudonymous identifier, timestamp, and reason) is retained
                solely as legal evidence that the erasure occurred. If you revoke this app&apos;s
                access in your Strava settings, Strava notifies us and we automatically erase all
                your data.
              </p>
```

- [ ] **Step 4.2: Verify no TS errors**

```
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 4.3: Commit**

```bash
git add frontend/src/pages/PrivacyPolicyPage.tsx
git commit -m "docs(privacy): disclose minimal deletion record retained as legal evidence"
```

---

## Self-Review

**Spec coverage:**
- TASK-9.1 Secure cookie → Task 1 ✓ (config field, middleware wiring, .env.example, tests)
- TASK-9.2 Webhook filter → Task 2 ✓ (schema, config, router, .env.example, webhook-registration.md, design.md, unit + integration tests)
- TASK-9.3 Proxy headers → Task 3 ✓ (Dockerfile CMD)
- TASK-9.4 Privacy policy Option A → Task 4 ✓ (PrivacyPolicyPage.tsx)

**Placeholder scan:** None found. All code steps show complete implementations.

**Type consistency:**
- `session_cookie_secure: bool` defined in Task 1 Step 1.3, used in Task 1 Step 1.4 ✓
- `strava_webhook_subscription_id: int | None` defined in Task 2 Step 2.5, used in Task 2 Step 2.6 ✓
- `subscription_id: int | None = None` added to `StravaWebhookPayload` in Task 2 Step 2.4; referenced as `payload.subscription_id` in Task 2 Step 2.6 ✓
- `_active_settings(subscription_id)` helper defined in Task 2 Step 2.1 and used in all filter tests in the same step ✓

**Existing test back-compat:** The existing `_DEAUTH_PAYLOAD` in `test_privacy_router.py` has `subscription_id: 1`. Since `STRAVA_WEBHOOK_SUBSCRIPTION_ID` is not set in the test env, `settings.strava_webhook_subscription_id` is `None` → filter inactive → all existing tests pass without modification ✓
