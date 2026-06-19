# EPIC-9 Security & Privacy Hardening — Design Spec

**Date:** 2026-06-19
**Status:** Approved
**Scope:** Close audit findings before public launch. Four small, independent tasks ordered by severity.

---

## Background

The app is launch-ready in all other respects. The audit found one HIGH finding (cookie missing `Secure`) and three LOW findings. All four are fixed here; no enterprise-grade controls are in scope for a personal project of this size.

---

## TASK-9.1 — Session cookie `Secure` flag (HIGH)

**Problem:** `SessionMiddleware(https_only=False)` means the auth cookie is sent over plain HTTP, contradicting the privacy policy.

**Design:**
- Add `session_cookie_secure: bool` to `Settings`, defaulting to `True`.
- Read from optional env var `SESSION_COOKIE_SECURE`; parse `"false"` / `"0"` as `False`.
- Pass `https_only=settings.session_cookie_secure` to `SessionMiddleware`.
- Document in `.env.example`: set `false` only for local HTTP dev; production default is `true`.

**Local dev impact:** None — set `SESSION_COOKIE_SECURE=false` in `.env`.

---

## TASK-9.2 — Deauth webhook `subscription_id` filter (LOW)

**Problem:** `POST /strava/deauth` deletes user data based solely on an unauthenticated `owner_id`. Strava doesn't sign events, so a forged request from anyone who knows a victim's athlete ID could wipe their data (recoverable on next login, but still bad UX).

**Design:**
- Add `subscription_id: int | None = None` to `StravaWebhookPayload`.
- Add optional `strava_webhook_subscription_id: int | None` to `Settings` (not required; skips filter when unset).
- In the deauth handler: if the setting is set and `payload.subscription_id` doesn't match → log warning, return `200` (no deletion).
- When the setting is unset, skip the check entirely (preserves current behaviour at first boot).
- Document the residual risk: `subscription_id` is a guessable incrementing integer, not a real auth boundary.
- Update `.env.example` and `docs/ops/webhook-registration.md`.
- Add a short note to `docs/design.md` recording the residual risk and why the token-verification alternative was rejected.

---

## TASK-9.3 — Trust Fly.io proxy headers (LOW)

**Problem:** Uvicorn runs without `--proxy-headers`, so `request.client.host` is always the Fly proxy IP. Per-user rate limits collapse into a shared global bucket; logged IPs are wrong.

**Design:**
- Add `--proxy-headers --forwarded-allow-ips="*"` to the uvicorn `CMD` in `backend/Dockerfile`.
- One-line change; no application code touched.

---

## TASK-9.4 — Reconcile deletion audit log with privacy policy (LOW)

**Problem:** `DeletionEvent` stores a raw `strava_athlete_id` after deletion, but the privacy policy says "all your data is permanently erased."

**Decision:** Option A — update privacy policy wording to acknowledge the minimal, non-content deletion record (pseudonymous identifier + timestamp + reason) retained as legal evidence. No model or migration change.

**Design:**
- Update `PrivacyPolicyPage.tsx` to note that a minimal deletion record is kept solely to evidence the deletion occurred.

---

## Order of implementation

| # | Task | Files touched |
|---|------|--------------|
| 1 | 9.1 Secure cookie | `config.py`, `main.py`, `.env.example` |
| 2 | 9.2 Webhook filter | `schemas.py`, `config.py`, `router.py`, `.env.example`, `webhook-registration.md`, `design.md` + tests |
| 3 | 9.3 Proxy headers | `backend/Dockerfile` |
| 4 | 9.4 Privacy policy | `PrivacyPolicyPage.tsx` |

Each task ships as its own commit.

---

## Out of scope (tracked separately)

Production deployment guide (`docs/ops/deployment.md`) is tracked as **TASK-10.1**. It depends on TASK-9.1 and TASK-9.2 landing first so that `SESSION_COOKIE_SECURE` and `STRAVA_WEBHOOK_SUBSCRIPTION_ID` are already in `.env.example` before the guide is written.
