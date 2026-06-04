# TASK-3.5 — Dashboard Sync Page Design

_Date: 2026-06-04_

## What We're Building

A minimal `DashboardPage` component that lets the authenticated user trigger an activity sync and see a confirmation result. This page grows in TASK-5.4 when goal progress content is added. The sync button lives here — not on a separate sync page — because it is contextually tied to the data it populates.

## Changes: Keep vs Revert

### Keep (from earlier draft implementation)
- `frontend/index.html` — Google Fonts (Barlow Condensed, Barlow, Fira Mono)
- `frontend/src/index.css` — design system: CSS variables, nav shell, button, error, footer styles
- `frontend/src/main.tsx` — CSS import
- `frontend/src/api/client.ts` — `SyncCooldownError` class, `SyncResponse` interface, `postSync()` function. `ActivitySummary` removed.
- `frontend/src/App.tsx` — loading state uses `.app-loading` CSS class
- `frontend/src/components/GdprFooter.tsx` — uses `.gdpr-footer` CSS class
- `frontend/src/pages/LoginPage.tsx` — redesigned with design system classes

### Revert (backend changes no longer needed)
- `backend/sync/schemas.py` — remove `ActivitySummary`, restore original `SyncResponse` (count + timestamp only)
- `backend/sync/sync_service.py` — remove activities mapping, restore original `run_sync` return

### Delete
- `frontend/src/pages/SyncPage.tsx` — replaced by `DashboardPage.tsx`

### Create / Update
- `frontend/src/pages/DashboardPage.tsx` — new minimal dashboard shell (see below)
- `frontend/src/pages/HomePage.tsx` — updated to nav shell (see below)

## Architecture

### Auth flow (unchanged)
`App.tsx` is the auth gate. Authenticated state renders `HomePage`. No changes to `App.tsx` beyond the loading class already applied.

### App shell — `HomePage.tsx`
Transforms into the authenticated navigation shell:
- Sticky top nav bar: `SGV` brand (left) · nav links (centre) · `Logout →` (right)
- `page` state (`'dashboard'` only for now; expands as future tasks add pages) lives in `HomePage`
- Renders the active page component in a `<main>` content area
- `GdprFooter` at the bottom
- No placeholder/disabled nav links for pages not yet built

### Dashboard page — `DashboardPage.tsx`
Props: `athleteId: number`

Elements (top to bottom):
1. Heading — "Dashboard" in large condensed font
2. Athlete ID — small monospace label (`Athlete #12345`)
3. Sync button — lime, full label "Sync Activities"; shows spinner + "Syncing…" during request
4. **Success state** (shown after sync): run count (`"5 runs synced"` / `"1 run synced"`) + last synced timestamp in monospace
5. **Cooldown error**: amber warning — `"Sync unavailable — try again in N minutes"` (seconds from `Retry-After` header, rounded up)
6. **Generic API error**: red — `"Sync failed — please try again."`

State is in-memory only. Refreshing resets to the initial state (no count, no timestamp). Persistent data display is deferred to TASK-5.4.

## API

`postSync()` already added to `client.ts`:
```ts
interface SyncResponse {
  synced_activities: number
  last_sync_completed_at: string
}

class SyncCooldownError extends Error {
  retryAfterSeconds: number
}

async function postSync(): Promise<SyncResponse>
```

## Error Handling

| Scenario | Response |
|---|---|
| 429 with `Retry-After` header | `SyncCooldownError` thrown; UI shows minutes remaining |
| Any other non-ok response | Generic `Error` thrown; UI shows "Sync failed" |
| Network failure | Same as above |

## Backlog Impact

- TASK-3.5 now creates `DashboardPage.tsx` (minimal shell, sync only)
- TASK-5.4 extends `DashboardPage.tsx` rather than creating it from scratch — backlog note to be updated

## Out of Scope

- Activity list display (removed — dashboard is the data view, TASK-5.4)
- Persistent sync state across page refresh (deferred to dashboard content tasks)
- `GET /activities` backend endpoint (not needed for this task)
- Placeholder nav links for future pages
