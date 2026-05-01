# Strava App — Greenfield Design Document

_Last updated: May 1, 2026_

---

## 1. Overview

A Strava-integrated application with a Streamlit frontend and FastAPI backend, written in Python, deployed as a shared SaaS product. The app enables athletes to visualize personal running progress toward a yearly goal and view club progress for authorized members of their Strava clubs.

---

## 2. Product Goals

- Provide clear annual running-goal visualization per athlete.
- Provide club progress visualization for all app-authorized members of a user's Strava clubs.
- Ensure privacy-forward self-service data export and deletion.
- Keep operations simple for a single operator while supporting up to 500 active users.

---

## 3. Non-Goals (v1)

- Club-admin permission system.
- Non-Strava data sources.
- Cross-club aggregate rankings.
- Webhook-based real-time data ingestion.
- Reconciliation of deleted or private Strava activities.
- Enterprise-grade SLO commitments.

---

## 4. Target Users and Roles

| Role | Capabilities |
|---|---|
| Athlete | Connect Strava, view personal dashboard, set goal, sync own data, export own data, delete own account |
| Operator | Deploy and operate the service, receive alert notifications |

---

## 5. Deployment and Tenancy

- **Model:** Shared SaaS, single shared product instance.
- **Hosting:** Fly.io.
- **Topology:** Separate deployments for Streamlit frontend, FastAPI backend, and PostgreSQL.
- **Sync model:** Lazy sync only (manual trigger + auto-trigger on dashboard open when stale).
- **Scale target:** Up to 500 active users.

---

## 6. Architecture

### 6.1 Frontend (Streamlit)

**Responsibilities:**
- OAuth initiation and callback-handoff UX.
- Personal progress view (current year only, goal progress, charts).
- Club progress view (per-club switcher).
- Privacy actions: data export initiation, account deletion initiation, status feedback.
- Sync status display: shows last-sync timestamp and sync-in-progress indicator.
- Persistent links to GDPR documents (privacy policy, terms of service, data deletion info) visible on all pages.
- Empty-state handling: clear messaging when a club has no other authorized members, when no activities are found, or when sync is pending.
- Trigger direct browser calls to FastAPI endpoints for auth, sync, goals, clubs, and privacy actions.

**Caching strategy:**
- `st.cache_data` is used for expensive read operations (club progress queries, aggregated metrics).
- Cache TTL is set to 30–120 seconds; the database is always the authoritative source.
- No explicit cache invalidation logic; TTL-based expiry is sufficient for v1.

### 6.2 Backend (FastAPI)

**Responsibilities:**
- OAuth and token lifecycle management.
- Incremental activity sync orchestration with per-user lock enforcement.
- Per-user lock remains required to prevent concurrent sync runs from multi-tab usage, rapid repeat clicks, and overlapping manual/auto-on-open triggers.
- Goal read/update.
- Club progress view computation.
- DSAR export and deletion execution.
- Strava deauthorization callback handling.
- Enforcement of all authorization, rate limiting, and CSRF policies.

### 6.3 Data Layer (PostgreSQL)

**Persistent entities:**
- Users (Strava athlete ID as primary identity).
- OAuth credentials and metadata (tokens stored encrypted at rest).
- Activities (incremental, keyed by Strava activity ID).
- Clubs and app-authorized memberships.
- User goal preferences.
- Sync state per user (last sync cursor, sync status, last sync timestamp).

**Data freshness model:**
- v1 uses polling-only sync; no Strava webhooks.
- The UI displays the exact last-sync timestamp so users understand data freshness without false guarantees.
- Club membership changes (user leaves a Strava club) are reflected at the user's next successful sync.
- Deleted and private activities are retained as a historical snapshot in v1 until user-initiated deletion or deauthorization.

---

## 7. Authentication and Session Model

- **OAuth provider:** Strava.
- **Identity linkage:** Strict Strava athlete ID only. No name-based or fuzzy matching.
- **Frontend ↔ Backend auth:** Browser calls FastAPI directly with secure HTTP-only session cookies.
- **Cookie attributes:** `Secure`, `HttpOnly`, `SameSite=Lax`. Session cookie is rotated on login and on token refresh.
- **Session timeout:** 30 minutes of inactivity (rolling window).
- **Session invalidation:** Forced on deauthorization callback, token refresh failure, and explicit user logout.
- **Token behavior:** Silent Strava access-token refresh by default. Re-authentication required only if the refresh token itself is invalid or expired.
- **CSRF protection:** Handled via `SameSite=Lax` + strict CORS origin allowlist for the Streamlit frontend origin. Explicit CSRF tokens are not required for v1.

---

## 8. Core Domain Behavior

### 8.1 Goals

- Goal is a per-athlete visualization parameter stored in the database.
- Users can edit their own goal at any time; updates are reflected immediately in personal and club views.
- Club progress percentages use **each member's own goal**, not a shared club goal.
- Default goal: 365 km/year. Maximum: 100,000 km/year.

### 8.2 Personal Sync

- A user can request sync for their own account via the Streamlit UI or API endpoint.
- The dashboard can auto-trigger sync on open when data is stale (24h+).
- The backend checks the per-user lock; if a sync is already running, the request is rejected with a `409 Sync already running` response.
- Lazy triggers use the same lock mechanism; the backend enforces mutual exclusion via the per-user lock.
- Sync is incremental: the backend fetches only activities created or updated since the last sync cursor.
- **v1 limitation:** Changes to activities older than the cursor window may be missed (for example: late Strava edits on old activities, retroactive privacy changes, or backdated activity corrections). This can cause temporary metric inaccuracies until a future broader reconciliation strategy is added.
- v1 retains deleted and private Strava activities as a historical snapshot.

### 8.3 Sync State Machine

Each user's sync has the following states:

| State | Meaning |
|---|---|
| `idle` | No sync in progress; data may or may not be stale |
| `running` | Sync job is active for this user |
| `completed` | Last sync finished successfully |
| `failed` | Last sync encountered a terminal error |

**Idempotency:** Sync uses best-effort idempotency with upsert semantics. Activities are upserted by Strava activity ID; re-running over the same window produces no duplicate activities. Partial failures preserve the sync cursor, so the next attempt re-fetches from the last safe point.

**Concurrency lock:** A hard per-user lock prevents concurrent syncs. If a manual trigger and an auto-on-open trigger happen simultaneously for the same user, the second request receives an immediate `409 Sync already running` response and is dropped. No queuing.

**Sync cursor:** Updated only after a fully successful sync. A partial failure leaves the cursor unchanged so the next run re-fetches from the last safe point.

### 8.4 Club Sync

- No user-triggered club-wide sync feature.
- Club progress view freshness relies on each member's individual lazy sync.

### 8.5 Club Views

- Club switcher shows all Strava clubs the authenticated user belongs to.
- Each club has an independent progress view.
- Club progress view includes only app-authorized users who are members of that club.
- A persistent disclaimer is displayed on every club progress view: "This club view shows members who have connected this app. It is a progress visualization, not a competition leaderboard."
- Empty-state message is shown if the user is the only authorized member of a club.

---

## 9. Privacy and Compliance

### 9.1 DSAR (Data Subject Access Request)

- Export and deletion are self-service in the app UI.
- Target completion: seconds to minutes (synchronous execution).
- No dedicated DSAR event log in v1.

### 9.2 User-Initiated Deletion

- Full erasure: user record, OAuth tokens, activities, and club memberships are deleted.
- A minimal deletion event is logged (timestamp, user ID, reason) without enrichment or PII.
- Active session is immediately invalidated.
- No audit trail survives deletion in v1.

### 9.3 Strava Deauthorization Callback

- Strava sends a deauthorization event when a user revokes app access from within Strava.
- On receipt, the backend attempts to: revoke stored tokens, erase all user data, invalidate active session.
- **Failure handling:** If the callback fails, the backend logs the error and raises an operator alert for manual resolution.
- This satisfies Strava's platform requirement and GDPR right to erasure.

### 9.4 Retention

- No automated retention cleanup in v1.
- Activities are retained indefinitely until user-initiated deletion or deauthorization.

---

## 10. Authorization Matrix

Every endpoint enforces the following rules. "Own" means the resource belongs to the authenticated session user.

| Endpoint | Who can call | Resource constraint |
|---|---|---|
| `POST /oauth/authorize` | Unauthenticated | Initiates new OAuth flow |
| `GET /oauth/callback` | Unauthenticated | Must present valid state token (TTL: 10 min) |
| `POST /oauth/revoke` | Authenticated athlete | Own tokens only |
| `GET /session/me` | Authenticated athlete | Own profile only |
| `POST /session/logout` | Authenticated athlete | Own session only |
| `GET /goals` | Authenticated athlete | Own goal only |
| `PUT /goals` | Authenticated athlete | Own goal only |
| `POST /sync` | Authenticated athlete | Own athlete ID only; any other ID is rejected |
| `GET /sync/status` | Authenticated athlete | Own sync status only |
| `GET /clubs` | Authenticated athlete | Own Strava clubs only |
| `GET /clubs/{id}/leaderboard` | Authenticated athlete | Must be a member of club `{id}` |
| `POST /privacy/export` | Authenticated athlete | Own data only |
| `POST /privacy/delete` | Authenticated athlete | Own data only |
| `POST /strava/deauth` | Strava server (verified by Strava signature) | — |
| `GET /internal/health` | Operator (token-authenticated or localhost) | Service status |

No endpoint permits an authenticated user to read, write, or sync another user's data.

---

## 11. External Failure Handling

### 11.1 Strava API Failures

| Condition | Behavior |
|---|---|
| HTTP 5xx / timeout | Retry up to 3 times with exponential backoff; mark sync failed after 3rd failure |
| HTTP 429 rate limit | Pause sync; resume at next rate-limit window; do not fail the job |
| HTTP 401 invalid token | Attempt silent refresh; if refresh fails, mark sync failed and prompt user re-auth |
| Strava unreachable | Mark sync failed; preserve cursor; retry on the next lazy trigger |

### 11.2 Deauthorization Callback Failure

- Execute revoke + erase atomically.
- On failure: one automatic retry.
- On second failure: log error, raise operator alert for manual resolution.

### 11.3 Strava App Suspension

- All syncs fail with 401/403. Backend logs the condition and stops retrying after the standard backoff cycle.
- Operator must resolve Strava app status and notify users to retry sync.

---

## 12. Backend Security

### 12.1 Abuse Protection

- Per-IP rate limits applied at middleware layer on all auth, sync, and privacy endpoints.
- No per-session rate limiting in v1; per-IP limits are sufficient for the threat model.

### 12.2 CSRF Protection

- CSRF is mitigated via `SameSite=Lax` cookie attribute and strict CORS origin allowlist.
- Explicit CSRF tokens are not implemented in v1.

### 12.3 Token Storage

- Strava OAuth tokens are encrypted at rest using a mandatory `TOKEN_ENCRYPTION_KEY` environment variable.
- Tokens are never included in API responses or logs.

### 12.4 Transport

- HTTPS enforced at the infrastructure layer (Fly.io proxy). Backend does not serve plain HTTP in production.

---

## 13. Observability and Operations

### 13.1 Minimum Metrics at Launch

| Metric | Purpose |
|---|---|
| Sync success/failure count (per day) | Detect sync pipeline degradation |
| Strava API error rate (4xx, 5xx) | Detect Strava API instability |
| Last sync age (max across all users) | Detect users silently falling behind |

### 13.2 Log Redaction Rules

- OAuth tokens (access, refresh): never logged by discipline.
- Email addresses: masked in logs (e.g., `e***@example.com`).
- Athlete IDs: raw values allowed in logs.
- DSAR payloads: never logged.
- Plain text logs are acceptable in v1.

### 13.3 Operational Controls

- `GET /internal/health` returns service status (reachability, basic DB connectivity check).
- No scheduled jobs or CLI maintenance tools in v1.

---

## 14. OAuth Flow and Failure Modes

### 14.1 Happy Path

1. User clicks "Connect Strava".
2. Backend generates a signed state token (TTL: 10 minutes) and stores it server-side.
3. User is redirected to Strava OAuth consent screen.
4. On consent, Strava redirects to callback with `code` and `state`.
5. Backend validates state token (must match stored value, must not be expired).
6. Backend exchanges code for tokens, stores encrypted tokens, creates or updates user record.
7. Session cookie is issued; state token is deleted.

### 14.2 Failure Modes

| Condition | Behavior |
|---|---|
| State token expired (> 10 min) | Reject callback; show "Authorization timed out, please try again" |
| State token mismatch | Reject callback; log as potential CSRF attempt |
| Required scopes not granted | Hard fail; redirect to re-consent with explanation of required permissions |
| Strava returns error on callback | Show error message; invite user to retry |
| Token exchange fails | Show error message; no partial user record created |

Required Strava scopes: `activity:read_all`, `profile:read_all`. Both must be granted; partial consent results in hard failure with a re-consent prompt.

---

## 15. Lazy Sync Concurrency Policy

- Sync is triggered only by user manual request or auto-on-dashboard-open when stale.
- The per-user sync lock (§8.3) prevents overlap between lazy triggers for the same user.
- **No job queue in v1.** Sync tasks are executed in-process. Lost tasks on process crash are acceptable; a subsequent lazy trigger retries.

---

## 16. Streamlit Architecture Notes

- Streamlit runs as a separate process on Fly.io; no direct database connection.
- **Auth boundary:** Browser calls FastAPI endpoints directly. Streamlit does not proxy API requests.
- Deployment is split across separate Fly apps: frontend app (Streamlit), backend app (FastAPI), and managed PostgreSQL.
- Fly.io supports this topology directly.
- Frontend calls backend over HTTPS using a fixed API base URL; backend CORS allowlist includes only the frontend origin.
- Session cookies are set and validated by FastAPI only.
- `st.cache_data` keyed by user ID is used for club progress and metrics queries with a 30–120s TTL. The database is the authoritative source.
- `st.cache_data` keyed by user ID is used for club progress and metrics queries with a 30–120s TTL. The database is the authoritative source.
- Sync status is polled from FastAPI and shown in the UI; long-running sync does not block the UI thread.
- `st.session_state` holds current view parameters and lightweight UI state only. No sensitive data stored in session state.
- Page routing uses Streamlit's multi-page app feature.

---

## 17. API Surface (High-Level)

- **OAuth:** `POST /oauth/authorize`, `GET /oauth/callback`, `POST /oauth/revoke`
- **Session:** `GET /session/me`, `POST /session/logout`
- **Goals:** `GET /goals`, `PUT /goals`
- **Sync:** `POST /sync`, `GET /sync/status`
- **Clubs:** `GET /clubs`, `GET /clubs/{club_id}/leaderboard` (endpoint name retained for compatibility; response is used as a non-competitive club progress view)
- **Privacy:** `POST /privacy/export`, `POST /privacy/delete`
- **Strava events:** `POST /strava/deauth`
- **Internal (operator):** `GET /internal/health` only.

---

## 18. Acceptance Criteria

- A user can authorize with Strava and view personal yearly progress without operator intervention.
- A user can update their own goal and see progress recalculated immediately.
- No endpoint permits a user to sync or read another user's data.
- Club progress view shows only app-authorized users who are members of that club, with a persistent non-competitive disclaimer displayed.
- Expired access tokens refresh silently; re-auth is prompted only if refresh fails.
- User deletion is self-service and complete in seconds, producing full erasure with minimal audit logging.
- Strava deauthorization callback triggers erasure and session invalidation; operator-manual resolution on failure.
- Sync is lazy-only (manual + auto-on-open when stale); per-user lock prevents double-processing.
- Activity cleanup is not automated in v1.
- Sync uses best-effort idempotency with upsert semantics; re-running the same window produces no duplicate activities.
- OAuth state tokens expire after 10 minutes; expired tokens are rejected with a clear user-facing message.
- Partial Strava scope consent results in hard failure with a re-consent prompt.

---

## 19. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Strava quota exhaustion during peak usage | Incremental sync, stale-only targeting, pause-at-limit behavior |
| Deleted/private activities not reflected in v1 | Explicit non-goal documented; users informed via last-sync timestamp |
| Older activity edits can be missed by cursor-only sync | Explicitly document limitation in v1, display last-sync timestamp, and keep manual sync available; broader historical reconciliation is out of scope for v1 |
| User confusion around 30-minute session timeout | Clear expiry messaging and frictionless re-auth flow |
| Deauthorization callback partially fails | One automatic retry; operator alert on second failure; manual resolution path documented |
| Strava platform suspension | Backoff halts retries; operator alert; syncs degrade gracefully without data loss |
| Session cookie theft | `Secure` + `HttpOnly` + `SameSite=Lax`; session rotation on login and token refresh |

---

## 20. Operational Decision

- Incident-response alerting channel uses the existing support email from the current codebase.