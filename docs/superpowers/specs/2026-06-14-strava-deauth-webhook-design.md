# TASK-7.5: Strava Deauth Webhook Design

**Date:** 2026-06-14
**Status:** Approved

---

## Overview

Implement `POST /strava/deauth` to handle Strava's deauthorization webhook event (required by Strava's platform terms), and `GET /strava/deauth` to complete the one-time webhook subscription challenge that Strava performs when the subscription is registered.

Both routes live in `backend/privacy/router.py`.

---

## Background: How Strava Webhooks Work

Strava does not sign POST webhook events with a per-request HMAC. Instead, verification is done once during subscription setup:

1. **Registration (one-time):** You POST to Strava's subscriptions API with your `callback_url` and a `hub.verify_token` you freely choose.
2. **Challenge (GET):** Strava immediately sends `GET <callback_url>?hub.mode=subscribe&hub.challenge=<random>&hub.verify_token=<your_token>`. Your endpoint must echo `{"hub.challenge": "<random>"}` within 2 seconds. If the `hub.verify_token` doesn't match, return `403`.
3. **Events (POST):** Strava POSTs deauth events to the same URL — no signature, no additional authentication.

**Deauth event payload:**
```json
{
  "object_type": "athlete",
  "aspect_type": "update",
  "owner_id": 1234567,
  "object_id": 1234567,
  "updates": {"authorized": "false"},
  "event_time": 1516126040,
  "subscription_id": 1
}
```

Note: Strava sends other event types to the same URL (e.g. activity updates). The endpoint must silently ignore non-deauth events.

---

## Scope

### In scope
- `GET /strava/deauth` — subscription challenge handler
- `POST /strava/deauth` — deauth event processor
- New required env var: `STRAVA_WEBHOOK_VERIFY_TOKEN`
- Schemas: `WebhookChallengeResponse`, `DeauthResponse`, `StravaWebhookPayload`
- Unit tests (mock-based) covering all branches
- Integration tests (real DB) for the end-to-end deauth flow
- Post-deployment ops runbook at `docs/ops/webhook-registration.md`

### Out of scope
- Webhook subscription creation (done manually post-deployment, see ops runbook)
- Activity sync webhooks (v1 uses polling only)

---

## Environment Variable

`STRAVA_WEBHOOK_VERIFY_TOKEN` — a free-form string you choose and set once. Used to verify the `hub.verify_token` Strava sends during subscription setup. Must be added to:
- `backend/shared/config.py` — `_REQUIRED_ENV_VARS` list and `Settings` dataclass
- `.env.example` — with a descriptive comment

---

## GET /strava/deauth — Challenge Handler

**Rate limit:** 20/minute (no auth — called once by Strava during subscription setup only)

**Query parameters received from Strava:**
- `hub.mode` — always `"subscribe"` during setup
- `hub.challenge` — random string Strava generates; must be echoed back
- `hub.verify_token` — must match `settings.strava_webhook_verify_token`

**Logic:**
1. If `hub.verify_token` != `settings.strava_webhook_verify_token` → return `403`
2. Otherwise → return `{"hub.challenge": hub.challenge}` with status `200`

**Response schema:** `WebhookChallengeResponse` with field `hub_challenge: str` serialised as `"hub.challenge"` via Pydantic field alias (`model_config = ConfigDict(populate_by_name=True)`). FastAPI serializes response models `by_alias=True` by default, so the JSON key will be `"hub.challenge"` as Strava expects.

FastAPI query param names containing `.` must be declared with `Query(alias="hub.challenge")` etc. Use `Annotated[str, Query(alias="hub.challenge")]` pattern.

---

## POST /strava/deauth — Deauth Event Handler

**Rate limit:** 500/minute (no auth)

Strava allows only one webhook subscription per app and sends **all** event types (activity creates/updates/deletes, athlete profile updates, deauth) to the same callback URL. Even though v1 only acts on deauth events, the endpoint will receive the full event volume for all users. 20/minute would be hit immediately on any moderately active app. 500/minute provides meaningful abuse protection while accommodating realistic Strava traffic. The primary protection against malicious POSTs is the payload filter — only valid deauth events trigger any database work.

**Request body schema:** `StravaWebhookPayload`
```python
class StravaWebhookPayload(BaseModel):
    object_type: str
    aspect_type: str
    owner_id: int
    updates: dict[str, str] = {}
```

**Logic:**
1. **Filter:** If `object_type != "athlete"` or `updates.get("authorized") != "false"` → return `200` immediately. Strava sends profile updates and other events to the same URL; silently ignore them.
2. **User lookup:** Query `users` table by `strava_athlete_id == owner_id`. If not found → `logger.warning("Strava deauth: unknown athlete %s", owner_id)` → return `200` (Strava requires 200 on all responses).
3. **Delete:** Call `privacy_service.delete_user_data(db, user_id=user.id, reason=DeletionReason.STRAVA_DEAUTH)`.
4. **Session invalidation:** Handled naturally. Sessions are cookie-based with no server-side store; `get_current_user` queries the DB on every request. Once the user row is deleted, any subsequent request with the old cookie returns `401`.
5. **Error handling:** Wrap steps 2–3 in `try/except Exception`. On failure: `logger.error("Strava deauth failed for athlete %s: %s", owner_id, exc)` → return `200`. Strava retries on non-200; we return 200 to stop retries and rely on operator manual resolution from logs.

**Response schema:** `DeauthResponse(status: str = "ok")`

---

## Schemas (`backend/privacy/schemas.py` additions)

```python
class WebhookChallengeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    hub_challenge: str = Field(alias="hub.challenge")

class StravaWebhookPayload(BaseModel):
    object_type: str
    aspect_type: str
    owner_id: int
    updates: dict[str, str] = {}

class DeauthResponse(BaseModel):
    status: str = "ok"
```

---

## Testing

### Unit tests (`tests/backend/privacy/test_privacy_router.py`)

Mock-based tests using FastAPI's `TestClient` and `app.dependency_overrides`:

| Test | Expected |
|------|----------|
| `GET` with correct `hub.verify_token` | `200`, body `{"hub.challenge": "<value>"}` |
| `GET` with wrong `hub.verify_token` | `403` |
| `POST` valid deauth payload, known user | `200`, service called with `strava_deauth` reason |
| `POST` valid deauth payload, unknown athlete | `200`, service not called |
| `POST` non-deauth event (e.g. `aspect_type != "update"` or `authorized != "false"`) | `200`, service not called |
| `POST` service raises exception | `200`, error logged |
| `POST` rate limit exceeded (21st request) | `429` |

### Integration tests (`tests/backend/privacy/test_deauth_integration.py`)

Real-DB tests using the `db` fixture from `tests/conftest.py`:

| Test | Assertion |
|------|-----------|
| Valid deauth for existing user | User row deleted; `deletion_events` has 1 row with `reason = "strava_deauth"` |
| Valid deauth for unknown athlete ID | `200` returned; no `deletion_events` row added |
| After deauth, `GET /session/me` (or equivalent auth check) | Returns `401` (user gone from DB) |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/shared/config.py` | Add `STRAVA_WEBHOOK_VERIFY_TOKEN` to `_REQUIRED_ENV_VARS` and `Settings` |
| `.env.example` | Add `STRAVA_WEBHOOK_VERIFY_TOKEN=` with comment |
| `backend/privacy/schemas.py` | Add `WebhookChallengeResponse`, `StravaWebhookPayload`, `DeauthResponse` |
| `backend/privacy/router.py` | Add `GET /strava/deauth` and `POST /strava/deauth` |
| `tests/backend/privacy/test_privacy_router.py` | Add unit tests for both new routes |
| `tests/backend/privacy/test_deauth_integration.py` | New file: integration tests |
| `docs/ops/webhook-registration.md` | New file: post-deployment runbook |

---

## Post-Deployment Ops

See `docs/ops/webhook-registration.md` for the exact steps to register the webhook subscription with Strava after deployment.
