# Strava App — MVP Design Document

_Last updated: May 2, 2026_

---

## 1. Overview

A Strava-integrated application with a Streamlit frontend and FastAPI backend, written in Python, deployed as a shared SaaS product. The app enables athletes to visualize personal running progress toward a yearly goal and view club progress for authorized members of their Strava clubs.

---

## 2. Product Goals

- Provide clear annual running-goal visualization per athlete.
- Provide club progress visualization for all app-authorized members of a user's Strava clubs.
- Ensure privacy-forward self-service data export and deletion.
- Keep operations simple for a single operator.

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
| Operator | Deploy and operate the service |

---

## 5. Deployment and Tenancy

- **Model:** Shared SaaS, single shared product instance.
- **Hosting:** Fly.io.
- **Topology:** Separate deployments for Streamlit frontend, FastAPI backend, and PostgreSQL.
- **Sync model:** Single synchronous endpoint, manual trigger only with per-user cooldown.

---

## 6. Architecture Patterns

### 6.0 Backend Code Organisation

The backend follows a **domain-driven structure**. Each business domain owns its routes, business logic, and schemas. Cross-cutting infrastructure lives in `shared/`.

```
backend/
  auth/          # OAuth flow, sessions, users, credentials
  sync/          # Activity fetch, upsert, cooldown
  goals/         # Goal CRUD, progress computation
  clubs/         # Club fetch, membership, progress view
  privacy/       # Export, deletion, deauth webhook
  shared/        # config, crypto, db, models, rate_limit
  db/            # Alembic migrations only
  dependencies.py
  main.py        # Assembly: middleware, router inclusion, health endpoints
```

Each domain contains a `router.py` (FastAPI `APIRouter`), a `schemas.py` (Pydantic models), and one or more service files containing business logic.

**`shared/` rule:** A module belongs in `shared/` only if it is imported by two or more domains. Single-domain utilities live inside that domain.

### 6.0.1 Dependency Injection

All service construction goes through factory functions in `backend/dependencies.py`. Singletons (e.g., the `Crypto` instance, the `Limiter`) are module-level constants — never recreated per request. Endpoints always use `Depends(factory_fn)`; they never instantiate services directly.

### 6.0.2 Pydantic Schemas

Every endpoint declares a named `response_model` using a Pydantic `BaseModel`. Request body parameters also use named schema classes. Schemas live in `<domain>/schemas.py`. Endpoints return the schema instance, not a raw dict. This ensures OpenAPI documentation is always accurate and responses are validated.

### 6.0.3 Rate Limiting

A single `Limiter` instance from `backend/shared/rate_limit.py` is registered on `app.state.limiter` and reused across all domain routers. Decorating an endpoint with `@limiter.limit("N/minute")` uses this shared instance and its shared storage backend.

---

## 6. Architecture

### 6.1 Frontend (Streamlit)

**Responsibilities:**
- OAuth initiation and callback-handoff UX.
- Personal progress view (current year only, goal progress, charts).
- Club progress view (per-club switcher).
- Privacy actions: data export initiation, account deletion initiation, status feedback.
- Sync status display: shows last-sync timestamp.
- Persistent links to GDPR documents (privacy policy, terms of service, data deletion info) visible on all pages.
- Empty-state handling: clear messaging when a club has no other authorized members, when no activities are found, or when sync is pending.
- Trigger direct browser calls to FastAPI endpoints for auth, sync, goals, clubs, and privacy actions.

### 6.2 Backend (FastAPI)

**Responsibilities:**
- OAuth and token lifecycle management.
- Activity sync (full fetch, cooldown-enforced).
- Goal read/update.
- Club progress view computation.
- DSAR export and deletion execution.
- Strava deauthorization callback handling.
- Enforcement of all authorization, rate limiting, and CSRF policies.

### 6.3 Data Layer (PostgreSQL)

**Persistent entities:**
- Users (Strava athlete ID as primary identity).
- OAuth credentials and metadata (tokens stored encrypted at rest).
- Activities (keyed by Strava activity ID).
- User club memberships.
- User goal preferences.
- Sync state per user (`last_sync_completed_at` timestamp only).

**Data freshness model:**
- v1 uses polling-only sync; no Strava webhooks.
- The UI displays the exact last-sync timestamp so users understand data freshness.
- Club membership changes (user leaves a Strava club) are reflected at the user's next successful sync.
- Deleted and private activities are retained as a historical snapshot in v1 until user-initiated deletion or deauthorization.

---

## 7. Authentication and Session Model

- **OAuth provider:** Strava.
- **Identity linkage:** Strict Strava athlete ID only. No name-based or fuzzy matching.
- **Frontend ↔ Backend auth:** Browser calls FastAPI directly with secure HTTP-only session cookies.
- **Cookie attributes:** `Secure`, `HttpOnly`, `SameSite=Lax`. Session cookie is rotated on login.
- **Session timeout:** Fixed session until explicit logout.
- **Session invalidation:** Forced on deauthorization callback, token refresh failure, and explicit user logout.
- **Token behavior:** Silent Strava access-token refresh by default. If the refresh token is invalid or expired, the session is immediately invalidated and the user is required to re-authenticate on their next action.
- **CSRF protection:** Handled via `SameSite=Lax` + strict CORS origin allowlist for the Streamlit frontend origin.

---

## 8. Core Domain Behavior

### 8.1 Goals

- Goal is a per-athlete visualization parameter stored in the database.
- Users can edit their own goal at any time; updates are reflected immediately in personal and club views.
- Club progress percentages use **each member's own goal**, not a shared club goal.
- All distance and progress calculations are based on running activities only (see §8.5).
- Default goal: 365 km/year. Maximum: 100,000 km/year.

### 8.2 Personal Sync

- A user can request sync for their own account via the Streamlit UI or the `POST /sync` endpoint.
- Sync is synchronous and stateless except for a cooldown timestamp (`last_sync_completed_at`).
- On each sync, the backend fetches all Strava activities in full (no incremental or cursor-based logic) and upserts them into the database by `strava_activity_id`.
- All activity types are stored. Only activities with `sport_type = 'Run'` are used in any business logic or computation (see §8.5).
- On success, `last_sync_completed_at` is set to the current time.
- The backend enforces a 10-minute per-user cooldown: if a sync completed in the last 10 minutes, the request is rejected with `429 Too Many Requests` and a `Retry-After` header indicating when the next sync is allowed.
- There is no auto-trigger on dashboard open.
- There is no retry logic; if the Strava API call fails, the error is surfaced directly to the user.
- v1 retains deleted and private Strava activities as a historical snapshot.
- Sync uses best-effort idempotency with upsert semantics; re-running produces no duplicate activities.

### 8.3 Club Sync


- No user-triggered club-wide sync feature.
- Club progress view freshness relies on each member's individual lazy sync.

### 8.4 Club Views

- Club switcher shows all Strava clubs the authenticated user belongs to.
- Each club has an independent progress view.
- Club progress view includes only app-authorized users who are members of that club. Users that are part of the user database and have that club inside of the club membership database.
- A persistent disclaimer is displayed on every club progress view: "This club view shows members who have connected this app. It is a progress visualization, not a competition leaderboard."
- Empty-state message is shown if the user is the only authorized member of a club.

---

### 8.5 Activity Scope Rule

**The application only considers Strava activities where `sport_type = "Run"`.**

This is the single, non-negotiable filter that governs all business logic in the system.

**What this means:**
- All metrics (total distance, goal progress, pace calculations, progress percentages) are computed exclusively from running activities.
- Non-running activities (cycling, swimming, hiking, etc.) are never included in any computation.
- The rule applies uniformly across: personal dashboard, club progress view, all backend computation endpoints.

**Storage rule:**
- All activity types received from the Strava API may be stored in the database as-is.
- Every query that feeds business logic **must** include a `WHERE sport_type = 'Run'` filter (or equivalent ORM condition).
- No additional filtering pipeline or tagging system is introduced; the filter is applied directly at query time.

**Definition:** A running activity is any Strava activity whose `sport_type` field equals the string `"Run"` exactly. No other sport types are treated as equivalent.

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

### 9.3 Strava Deauthorization Callback

- Strava sends a deauthorization event when a user revokes app access from within Strava.
- On receipt, the backend attempts to revoke stored tokens, erase all user data, and invalidate the active session.
- **Failure handling:** If the callback fails, the error is logged for operator manual resolution.
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
| `GET /clubs` | Authenticated athlete | Own Strava clubs only |
| `GET /clubs/{id}/progress` | Authenticated athlete | Must be a member of club `{id}` |
| `POST /privacy/export` | Authenticated athlete | Own data only |
| `POST /privacy/delete` | Authenticated athlete | Own data only |
| `POST /strava/deauth` | Strava server (verified by Strava signature) | — |

No endpoint permits an authenticated user to read, write, or sync another user's data.

---

## 11. Strava API Integration

### 11.1 Strava API Failures

| Condition | Behavior |
|---|---|
| HTTP 401 invalid token | Attempt silent refresh; if refresh fails, invalidate session and require re-auth |
| Any other failure (5xx, timeout, 429) | Surface error directly to user; no retry |

### 11.2 Non-Strava Failures

- Any non-Strava operation that fails (database writes, export generation, etc.) logs the error and surfaces a user-facing error message. No automatic retry.

---

## 12. Backend Security

### 12.1 Abuse Protection

- Per-IP rate limits applied at middleware layer on all auth, sync, and privacy endpoints.

### 12.2 CSRF Protection

- CSRF is mitigated via `SameSite=Lax` cookie attribute and strict CORS origin allowlist.

### 12.3 Token Storage

- Strava OAuth tokens are encrypted at rest using a mandatory `TOKEN_ENCRYPTION_KEY` environment variable.
- Tokens are never included in API responses or logs.

### 12.4 Transport

- HTTPS enforced at the infrastructure layer (Fly.io proxy). Backend does not serve plain HTTP in production.

---

## 13. Logging

- Plain text structured logs throughout.
- OAuth tokens (access, refresh): never logged.
- Athlete IDs: raw values allowed in logs.
- DSAR payloads: never logged.
- Deletion events are logged with timestamp, user ID, and reason only (no PII enrichment).

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

## 15. API Surface (High-Level)

- **OAuth:** `POST /oauth/authorize`, `GET /oauth/callback`, `POST /oauth/revoke`
- **Session:** `GET /session/me`, `POST /session/logout`
- **Goals:** `GET /goals`, `PUT /goals`
- **Sync:** `POST /sync`
- **Clubs:** `GET /clubs`, `GET /clubs/{club_id}/progress`
- **Privacy:** `POST /privacy/export`, `POST /privacy/delete`
- **Strava events:** `POST /strava/deauth`

---

## 16. Acceptance Criteria

- A user can authorize with Strava and view personal yearly running progress without operator intervention.
- A user can update their own goal and see progress recalculated immediately.
- All distance metrics, goal progress, and club progress percentages are computed exclusively from activities where `sport_type = 'Run'`; non-running activities are never included in any computation.
- No endpoint permits a user to sync or read another user's data.
- Club progress view shows only app-authorized users who are members of that club, with a persistent non-competitive disclaimer displayed.
- Expired access tokens refresh silently; if refresh fails, the session is immediately invalidated and the user is required to re-authenticate.
- User deletion is self-service and complete in seconds, producing full erasure with minimal audit logging.
- Strava deauthorization callback triggers erasure and session invalidation; errors are logged for manual operator resolution.
- Sync is manual-only; a 10-minute per-user cooldown prevents rapid repeat syncs.
- Sync within the cooldown window returns `429 Too Many Requests` with a `Retry-After` header.
- Activity cleanup is not automated in v1.
- Sync uses best-effort idempotency with upsert semantics; re-running produces no duplicate activities.
- OAuth state tokens expire after 10 minutes; expired tokens are rejected with a clear user-facing message.
- Partial Strava scope consent results in hard failure with a re-consent prompt.

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Strava quota exhaustion during peak usage | 10-minute per-user cooldown limits sync frequency |
| Deleted/private activities not reflected in v1 | Explicit non-goal documented; users informed via last-sync timestamp |
| Deauthorization callback partially fails | Error logged; operator resolves manually |
| Session cookie theft | `Secure` + `HttpOnly` + `SameSite=Lax`; session rotation on login |
| Strava token expiry during fixed session | Silent refresh on access token expiry; immediate logout and re-auth prompt on refresh token failure |
