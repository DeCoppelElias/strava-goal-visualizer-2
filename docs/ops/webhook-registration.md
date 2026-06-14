# Strava Webhook Registration — Post-Deployment Steps

Strava requires a one-time webhook subscription to be registered before it will
send deauthorization events to `POST /strava/deauth`. Without this step, users
who revoke app access in Strava will NOT have their data deleted automatically.

## Prerequisites

- The app is deployed and reachable at a public HTTPS URL (e.g. `https://api.example.com`)
- `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, and `STRAVA_WEBHOOK_VERIFY_TOKEN`
  are set in the production environment
- The `GET /strava/deauth` endpoint is live (it responds to Strava's challenge within 2 seconds)

---

## Step 1: Register the webhook subscription

Run this cURL command (replace the values in angle brackets):

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET> \
  -F callback_url=https://<YOUR_DOMAIN>/strava/deauth \
  -F verify_token=<STRAVA_WEBHOOK_VERIFY_TOKEN>
```

Strava will immediately send a GET request to your `callback_url` with a
`hub.challenge` parameter. Your `GET /strava/deauth` endpoint handles this
automatically — it verifies the `hub.verify_token` and echoes `hub.challenge`
back within 2 seconds.

### Successful response

Strava returns:
```json
{"id": 12345}
```

Save this subscription ID — you will need it to view or delete the subscription later.

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `callback_url_not_reachable` | GET challenge timed out | Check the app is live at the URL; check logs for errors |
| `verify_token_mismatch` | `hub.verify_token` in env doesn't match what you passed | Ensure `STRAVA_WEBHOOK_VERIFY_TOKEN` in prod matches the `-F verify_token=` value |
| `already_subscribed` | A subscription already exists for this app | See Step 2 to view or delete the existing subscription |

---

## Step 2: Verify the subscription is active

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=<STRAVA_CLIENT_ID> \
  -d client_secret=<STRAVA_CLIENT_SECRET>
```

Expected response:
```json
[{"id": 12345, "callback_url": "https://<YOUR_DOMAIN>/strava/deauth", ...}]
```

---

## Step 3: Delete the subscription (if needed)

To rotate the subscription (e.g. after a domain change or secret rotation):

```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/<SUBSCRIPTION_ID>" \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET>
```

Then re-run Step 1 with the new URL / token.

---

## How to test the deauth flow in production

1. Create a Strava account (or use a test account).
2. Authorize the app via the normal OAuth flow.
3. In Strava → Settings → My Apps → revoke access to this app.
4. Wait up to 60 seconds.
5. Check the app's database: the user row and all associated data should be gone.
6. Check the `deletion_events` table: there should be a row with `reason = 'strava_deauth'`.
