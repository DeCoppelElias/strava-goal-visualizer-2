# Production Deployment Guide

This guide takes you from a fresh environment to a live, correctly-configured instance on Fly.io. Follow the steps in order.

**Prerequisites:**
- [`flyctl`](https://fly.io/docs/hands-on/install-flyctl/) installed and authenticated (`fly auth login`)
- Docker running locally (needed for `fly deploy` to build the image)
- A [Strava API application](https://www.strava.com/settings/api) created — you need the Client ID and Client Secret

---

## Architecture

One Fly.io app runs both the FastAPI backend and the built React frontend (served as static files by FastAPI). The database is a separate Fly Postgres instance attached to the app. This single-app design avoids cross-origin session cookie restrictions that arise when frontend and backend are on different `*.fly.dev` domains.

```
Browser → https://<app-name>.fly.dev
             └─ Fly.io app (FastAPI)
                  ├─ /oauth, /sync, /dashboard, ...  → FastAPI API handlers
                  ├─ /assets/*                        → built React JS/CSS bundles
                  └─ everything else                  → index.html (React SPA)
                       ↓
               Fly Postgres (DATABASE_URL secret)
```

---

## Step 1: Create the Fly.io app and database

```bash
# From the repo root — answer the interactive prompts:
#   App name: choose a unique name (e.g. strava-goal-visualizer)
#   Region:   pick the closest to your users
#   Deploy now? No
fly launch --no-deploy

# Create a Fly Postgres cluster and attach it (sets DATABASE_URL secret automatically)
fly postgres create --name <db-app-name>
fly postgres attach <db-app-name>
```

After `fly postgres attach`, run `fly secrets list` — you should see `DATABASE_URL` already set.

Update `fly.toml` with your chosen app name (replace both `<app-name>` placeholders).

---

## Step 2: Update the Strava redirect URI

Before your first deploy, go to [strava.com/settings/api](https://www.strava.com/settings/api) and add:

```
https://<app-name>.fly.dev/oauth/callback
```

to the **Authorization Callback Domain** field. The OAuth login flow will fail until this is set.

---

## Step 3: Set production secrets

Generate the required keys first:

```bash
# SESSION_SECRET_KEY — 32-byte hex string
python -c "import secrets; print(secrets.token_hex(32))"

# TOKEN_ENCRYPTION_KEY — Fernet key (44 chars)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# STRAVA_WEBHOOK_VERIFY_TOKEN — any random string
python -c "import secrets; print(secrets.token_hex(16))"
```

Then set all secrets in one command:

```bash
fly secrets set \
  STRAVA_CLIENT_ID=<your-strava-client-id> \
  STRAVA_CLIENT_SECRET=<your-strava-client-secret> \
  STRAVA_REDIRECT_URI=https://<app-name>.fly.dev/oauth/callback \
  SESSION_SECRET_KEY=<generated-above> \
  TOKEN_ENCRYPTION_KEY=<generated-above> \
  STRAVA_WEBHOOK_VERIFY_TOKEN=<generated-above>
```

`FRONTEND_ORIGIN` and `SESSION_COOKIE_SECURE` are already set in `fly.toml` `[env]` — do not add them here.
`DATABASE_URL` was set automatically by `fly postgres attach` — do not override it.

### Production env var reference

| Variable | Where set | Production value |
|---|---|---|
| `DATABASE_URL` | Auto (postgres attach) | `postgresql+asyncpg://...` (Fly internal) |
| `STRAVA_CLIENT_ID` | `fly secrets set` | Your Strava app client ID |
| `STRAVA_CLIENT_SECRET` | `fly secrets set` | Your Strava app client secret |
| `STRAVA_REDIRECT_URI` | `fly secrets set` | `https://<app-name>.fly.dev/oauth/callback` |
| `SESSION_SECRET_KEY` | `fly secrets set` | 32-byte hex string |
| `SESSION_COOKIE_SECURE` | `fly.toml [env]` | `true` (do not change) |
| `TOKEN_ENCRYPTION_KEY` | `fly secrets set` | Fernet key (44 chars) |
| `FRONTEND_ORIGIN` | `fly.toml [env]` | `https://<app-name>.fly.dev` |
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | `fly secrets set` | Random string (you choose) |
| `STRAVA_WEBHOOK_SUBSCRIPTION_ID` | `fly secrets set` (after Step 5) | Returned by Strava at webhook registration |
| `SYNC_COOLDOWN_SECONDS` | Omit | Defaults to 600 s (10 min) |
| `VITE_API_BASE_URL` | Baked in at build | `""` (set in Dockerfile — do not override) |

---

## Step 4: Deploy

```bash
fly deploy
```

Fly.io builds the multi-stage Dockerfile (Node 22 builds the React app, Python stage runs the backend), pushes the image, and starts the machine. Database migrations run automatically on startup.

**First deploy takes 3–5 minutes** (Node and Python dependency installs are cached on subsequent deploys).

Watch startup logs:

```bash
fly logs
```

Look for:

```
Running database migrations...
Database migrations complete.
Application startup complete.
```

---

## Step 5: Register the Strava webhook

Strava requires a one-time webhook subscription before it sends deauthorization events. Without this, users who revoke app access in Strava will **not** have their data deleted automatically.

### Register the subscription

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET> \
  -F callback_url=https://<app-name>.fly.dev/strava/deauth \
  -F verify_token=<STRAVA_WEBHOOK_VERIFY_TOKEN>
```

Strava immediately sends a GET challenge to your `callback_url`. The `GET /strava/deauth` endpoint handles this automatically (verifies the token, echoes the challenge back within 2 seconds).

**Successful response:**

```json
{"id": 12345}
```

Copy the returned `id` and set it as a secret:

```bash
fly secrets set STRAVA_WEBHOOK_SUBSCRIPTION_ID=12345
```

This activates the `subscription_id` filter: events with a non-matching ID are rejected with `200 OK` and no deletion occurs.

### Common errors

| Error | Cause | Fix |
|---|---|---|
| `callback_url_not_reachable` | GET challenge timed out | Verify the app is live; check `fly logs` |
| `verify_token_mismatch` | Token mismatch | Ensure `STRAVA_WEBHOOK_VERIFY_TOKEN` in prod matches the `-F verify_token=` value |
| `already_subscribed` | Subscription exists | See below to view or delete it |

### Verify the subscription is active

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=<STRAVA_CLIENT_ID> \
  -d client_secret=<STRAVA_CLIENT_SECRET>
```

Expected:

```json
[{"id": 12345, "callback_url": "https://<app-name>.fly.dev/strava/deauth", ...}]
```

### Delete the subscription (if needed)

To rotate (e.g. after a domain change or secret rotation):

```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/<SUBSCRIPTION_ID>" \
  -F client_id=<STRAVA_CLIENT_ID> \
  -F client_secret=<STRAVA_CLIENT_SECRET>
```

Then re-run Step 5 with the new URL / token.

### Test the deauth flow

1. Create or use a test Strava account and authorize the app via the normal OAuth flow.
2. In Strava → Settings → My Apps → revoke access to this app.
3. Wait up to 60 seconds.
4. Check `fly logs` for a `strava_deauth` log entry.
5. Verify via `fly postgres connect`: the user row and all associated data are gone; `deletion_events` has a row with `reason = 'strava_deauth'`.

---

## Step 6: Post-deploy verification

```bash
curl https://<app-name>.fly.dev/health
# → {"status":"ok"}

curl https://<app-name>.fly.dev/health/db
# → {"db":"ok"}
```

Then manually in a browser:

1. Open `https://<app-name>.fly.dev` — the React login page should load.
2. Click **Connect with Strava** — OAuth flow should complete and redirect back to the dashboard.
3. Click **Sync** — activities should load and the pace chart should render.

---

## Ongoing operations

```bash
# Tail live logs
fly logs

# SSH into a running machine
fly ssh console

# Manually run migrations (normally runs on startup automatically)
fly ssh console -C "alembic upgrade head"

# View usage statistics (see docs/ops/db-statistics.md for queries)
fly postgres connect -a <db-app-name>

# Redeploy after a code change
fly deploy

# Scale machine memory if needed
fly scale memory 512
```
