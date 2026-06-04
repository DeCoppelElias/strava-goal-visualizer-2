# TASK-3.5 Dashboard Sync Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authenticated app shell (nav bar) and a minimal DashboardPage with a sync button, run count confirmation, and error handling — no activity list.

**Architecture:** `HomePage.tsx` becomes a sticky-nav shell that renders the active page. `DashboardPage.tsx` is the only active page for now; it calls `POST /sync` and shows the result count + timestamp. Backend `ActivitySummary` additions are reverted — `SyncResponse` stays as count + timestamp only.

**Tech Stack:** React 18, TypeScript, Vite, FastAPI (backend revert only), pytest (backend tests only — no frontend test suite exists)

---

## File Map

| Action | Path |
|---|---|
| Revert | `backend/sync/schemas.py` |
| Revert | `backend/sync/sync_service.py` |
| Modify | `frontend/src/api/client.ts` — remove `ActivitySummary` + `activities` field |
| Modify | `frontend/src/index.css` — add `.sync-result` and `.sync-count` classes |
| Modify | `frontend/src/pages/HomePage.tsx` — nav shell pointing to DashboardPage |
| Create | `frontend/src/pages/DashboardPage.tsx` |
| Delete | `frontend/src/pages/SyncPage.tsx` |

These files are already correct and need no changes:
- `frontend/index.html` (Google Fonts)
- `frontend/src/index.css` (design system — we only add to it)
- `frontend/src/main.tsx` (CSS import)
- `frontend/src/App.tsx` (loading class)
- `frontend/src/components/GdprFooter.tsx` (CSS class)
- `frontend/src/pages/LoginPage.tsx` (redesigned)

---

### Task 1: Revert backend schema and service

The backend was incorrectly extended with `ActivitySummary`. Revert it so existing tests pass unchanged.

**Files:**
- Modify: `backend/sync/schemas.py`
- Modify: `backend/sync/sync_service.py`
- Test: `tests/backend/sync/test_sync_service.py` (run only — no changes)
- Test: `tests/backend/sync/test_sync_router.py` (run only — no changes)

- [ ] **Step 1: Restore `backend/sync/schemas.py` to its original state**

Replace the entire file with:

```python
from datetime import datetime

from pydantic import BaseModel


class SyncResponse(BaseModel):
    synced_activities: int
    last_sync_completed_at: datetime
```

- [ ] **Step 2: Restore `backend/sync/sync_service.py` — remove ActivitySummary import and activities mapping**

The import line to change (near top of file):
```python
# Before
from backend.sync.schemas import ActivitySummary, SyncResponse

# After
from backend.sync.schemas import SyncResponse
```

The `run_sync` method body to restore:
```python
async def run_sync(self, db: AsyncSession, user_id: int) -> SyncResponse:
    await self._check_cooldown(db, user_id)
    access_token = await self.oauth_service.ensure_fresh_token(db, user_id)
    raw = await fetch_all_activities(access_token, after=_jan1_unix_timestamp())
    runs = [a for a in raw if a.get("sport_type") == "Run"]
    if runs:
        await self._upsert_activities(db, user_id, runs)
    now = datetime.now(UTC)
    await self._upsert_sync_state(db, user_id, now)
    return SyncResponse(synced_activities=len(runs), last_sync_completed_at=now)
```

- [ ] **Step 3: Run backend sync tests — all 30 must pass**

```
uv run pytest tests\backend\sync\ -v
```

Expected: `30 passed`

---

### Task 2: Clean up frontend draft artifacts

Remove the `ActivitySummary` type and the `activities` field that were added to `client.ts` during the draft implementation, and delete `SyncPage.tsx`.

**Files:**
- Modify: `frontend/src/api/client.ts`
- Delete: `frontend/src/pages/SyncPage.tsx`

- [ ] **Step 1: Remove `ActivitySummary` interface and `activities` field from `client.ts`**

The current file has this block to remove:

```typescript
export interface ActivitySummary {
  name: string
  start_date: string
  distance_meters: number
  moving_time_seconds: number
}
```

And `SyncResponse` currently has an extra field — replace it with:

```typescript
export interface SyncResponse {
  synced_activities: number
  last_sync_completed_at: string
}
```

The rest of `client.ts` (`SyncCooldownError`, `postSync`) is correct and stays unchanged.

- [ ] **Step 2: Delete `SyncPage.tsx`**

```bash
rm frontend/src/pages/SyncPage.tsx
```

- [ ] **Step 3: Verify TypeScript still compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no type errors. (It will fail to resolve the `SyncPage` import in `HomePage.tsx` — that is expected and will be fixed in Task 4.)

> If you want a clean build first, temporarily revert `HomePage.tsx` to importing nothing, verify, then proceed to Task 4.

---

### Task 3: Add sync-result CSS classes to index.css

Two new CSS classes are needed by `DashboardPage` to display the post-sync confirmation.

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add `.sync-result` and `.sync-count` after the existing `.sync-timestamp` block**

Find the `.sync-timestamp` block in `frontend/src/index.css`:

```css
.sync-timestamp {
  font-family: 'Fira Mono', monospace;
  font-size: 12px;
  color: var(--text-2);
  letter-spacing: 0.04em;
}
```

Add immediately after it:

```css
.sync-result {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sync-count {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--accent);
}
```

---

### Task 4: Update HomePage.tsx to nav shell

`HomePage.tsx` is already structured as a nav shell from the draft. It just needs its reference to `SyncPage` swapped to `DashboardPage`, and the nav label updated from "Sync" to "Dashboard".

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Replace the full contents of `HomePage.tsx`**

```tsx
import { useState } from 'react'
import { postSessionLogout, type SessionUser } from '../api/client'
import GdprFooter from '../components/GdprFooter'
import DashboardPage from './DashboardPage'

type Page = 'dashboard'

interface Props {
  user: SessionUser
  onLogout: () => void
}

export default function HomePage({ user, onLogout }: Props) {
  const [page] = useState<Page>('dashboard')
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await postSessionLogout()
    } finally {
      onLogout()
    }
  }

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div className="app-nav__brand">SGV</div>
        <div className="app-nav__links">
          <button className={`app-nav__link${page === 'dashboard' ? ' app-nav__link--active' : ''}`}>
            Dashboard
          </button>
        </div>
        <button
          className="app-nav__logout"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? '…' : 'Logout →'}
        </button>
      </nav>
      <main className="app-main">
        <DashboardPage athleteId={user.strava_athlete_id} />
      </main>
      <GdprFooter />
    </div>
  )
}
```

---

### Task 5: Create DashboardPage.tsx

The core new component. Handles sync trigger, success state, and both error states. Uses only CSS classes already defined in `index.css` plus the two added in Task 3.

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Create the file with the following content**

```tsx
import { useState } from 'react'
import { postSync, SyncCooldownError } from '../api/client'

interface Props {
  athleteId: number
}

function formatSyncTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type SyncError =
  | { type: 'cooldown'; retryAfterSeconds: number }
  | { type: 'api' }

export default function DashboardPage({ athleteId }: Props) {
  const [syncing, setSyncing] = useState(false)
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null)
  const [syncCount, setSyncCount] = useState<number | null>(null)
  const [error, setError] = useState<SyncError | null>(null)

  async function handleSync() {
    setSyncing(true)
    setError(null)
    try {
      const result = await postSync()
      setSyncCount(result.synced_activities)
      setLastSyncAt(result.last_sync_completed_at)
    } catch (e) {
      if (e instanceof SyncCooldownError) {
        setError({ type: 'cooldown', retryAfterSeconds: e.retryAfterSeconds })
      } else {
        setError({ type: 'api' })
      }
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="sync-page">
      <div className="sync-hero">
        <h1 className="sync-title">Dashboard</h1>
        <p className="sync-athlete">Athlete #{athleteId}</p>
      </div>

      <div className="sync-action">
        <button
          className={`sync-btn${syncing ? ' sync-btn--loading' : ''}`}
          onClick={handleSync}
          disabled={syncing}
        >
          {syncing ? (
            <>
              <span className="sync-btn__spinner" aria-hidden="true" />
              Syncing…
            </>
          ) : (
            'Sync Activities'
          )}
        </button>
      </div>

      {syncCount !== null && lastSyncAt !== null && (
        <div className="sync-result">
          <p className="sync-count">
            {syncCount} {syncCount === 1 ? 'run' : 'runs'} synced
          </p>
          <p className="sync-timestamp">Last synced: {formatSyncTime(lastSyncAt)}</p>
        </div>
      )}

      {error?.type === 'cooldown' && (
        <p className="sync-cooldown-error" role="alert">
          <span aria-hidden="true">⚠</span>
          {' '}Sync unavailable — try again in {Math.ceil(error.retryAfterSeconds / 60)} minutes
        </p>
      )}

      {error?.type === 'api' && (
        <p className="sync-error" role="alert">
          Sync failed — please try again.
        </p>
      )}
    </div>
  )
}
```

---

### Task 6: Verify and commit

**Files:** all modified files

- [ ] **Step 1: Run full backend test suite**

```
uv run pytest tests\backend\ -v
```

Expected: all tests pass (minimum 30 from sync suite).

- [ ] **Step 2: Run TypeScript + Vite build**

```bash
cd frontend && npm run build
```

Expected: `✓ built in X.XXs` with no type errors.

- [ ] **Step 3: Commit all TASK-3.5 changes as a single commit**

Stage only the files changed in this task:

```bash
git add backend/sync/schemas.py backend/sync/sync_service.py
git add frontend/index.html frontend/src/index.css frontend/src/main.tsx
git add frontend/src/api/client.ts frontend/src/App.tsx
git add frontend/src/components/GdprFooter.tsx
git add frontend/src/pages/LoginPage.tsx frontend/src/pages/HomePage.tsx
git add frontend/src/pages/DashboardPage.tsx
git rm frontend/src/pages/SyncPage.tsx
git commit -m "feat(frontend): add app shell and dashboard sync page (TASK-3.5)

Authenticated app shell with sticky nav. DashboardPage with sync
button, run count confirmation, cooldown and error handling.
Design system (Barlow/Fira Mono, CSS variables) applied globally.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- ✅ `postSync()` in client.ts — exists from draft, `ActivitySummary` removed in Task 2
- ✅ Nav shell (`HomePage.tsx`) — Task 4
- ✅ `DashboardPage.tsx` — Task 5
- ✅ Sync button with spinner — Task 5
- ✅ Run count ("N runs synced") — Task 5
- ✅ Last sync timestamp — Task 5
- ✅ Cooldown error with minutes — Task 5
- ✅ Generic API error — Task 5
- ✅ Backend revert — Task 1
- ✅ Delete SyncPage.tsx — Task 2

**Placeholder scan:** None found. All steps contain exact file contents or diffs.

**Type consistency:**
- `SyncCooldownError.retryAfterSeconds` — defined in `client.ts`, consumed in Task 5 ✅
- `SyncResponse.synced_activities` / `.last_sync_completed_at` — defined in `client.ts`, consumed in Task 5 ✅
- `DashboardPage` default export referenced in `HomePage.tsx` Task 4 — created in Task 5 ✅ (implement Task 5 before running build in Task 6)
- CSS classes `.sync-result`, `.sync-count` — added in Task 3, used in Task 5 ✅
