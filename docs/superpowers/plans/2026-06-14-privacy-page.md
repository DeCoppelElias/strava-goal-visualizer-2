# Privacy Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-service privacy page accessible from the GDPR footer, providing data export and account deletion.

**Architecture:** `GdprFooter` gains an optional click callback; `HomePage` adds `'privacy'` to the `Page` union and wires both the footer and a new `PrivacyPage` component. The two backend endpoints (`POST /privacy/export`, `POST /privacy/delete`) already exist — this is entirely frontend work.

**Tech Stack:** React 18, TypeScript, Vite, existing CSS design tokens in `index.css`

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `frontend/src/index.css` | Add `.btn--danger`, `.gdpr-footer button`, `.privacy-page` styles |
| Modify | `frontend/src/api/client.ts` | Add `postPrivacyExport()` and `postPrivacyDelete()` |
| Modify | `frontend/src/components/GdprFooter.tsx` | Add `onPrivacyClick?` prop; convert "Data Deletion Info" to button |
| Create | `frontend/src/pages/PrivacyPage.tsx` | Export card + inline-confirm delete card |
| Modify | `frontend/src/pages/HomePage.tsx` | Add `'privacy'` to `Page`, render `PrivacyPage`, wire footer |

---

## Task 1: Add CSS

**Files:**
- Modify: `frontend/src/index.css`

No test framework for frontend — verify visually after wiring in Task 5.

- [ ] **Step 1: Add `.btn--danger` after the existing `.btn--ghost` block (around line 130)**

Open `frontend/src/index.css`. After the `.btn--ghost:hover:not(:disabled)` block, add:

```css
.btn--danger {
  background: var(--danger-dim);
  color: var(--danger);
  border-color: var(--danger-dim);
}

.btn--danger:hover:not(:disabled) {
  background: var(--danger);
  color: #fff;
  border-color: var(--danger);
}
```

- [ ] **Step 2: Add `.gdpr-footer button` styles after `.gdpr-footer a:hover` block (around line 536)**

The footer currently only styles `<a>` tags. "Data Deletion Info" will become a `<button>` — it must look identical to the anchor links:

```css
.gdpr-footer button {
  font-size: 12px;
  color: var(--text-3);
  background: none;
  border: none;
  padding: 0;
  margin: 0 6px;
  cursor: pointer;
  font-family: inherit;
  transition: color 180ms ease;
}

.gdpr-footer button:hover {
  color: var(--text-2);
}
```

- [ ] **Step 3: Add `.privacy-page` layout and component styles at the end of the file**

```css
/* ── Privacy Page ────────────────────────────────────── */

.privacy-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.privacy-description {
  font-size: 14px;
  color: var(--text-2);
}

.privacy-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.privacy-feedback {
  font-size: 13px;
  color: var(--text-2);
}

.privacy-feedback--error {
  color: var(--danger);
}

.privacy-confirm {
  background: var(--danger-dim);
  border: 1px solid rgba(224, 82, 82, 0.2);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.privacy-confirm__warning {
  font-size: 14px;
  color: var(--danger);
}

.privacy-confirm__actions {
  display: flex;
  gap: 8px;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(privacy): add danger button and privacy page CSS"
```

---

## Task 2: Add API functions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `PrivacyExportRateLimitedError` class and `postPrivacyExport` at the end of `client.ts`**

```ts
export class PrivacyExportRateLimitedError extends Error {
  constructor() {
    super('Privacy export rate limited')
    this.name = 'PrivacyExportRateLimitedError'
  }
}

export async function postPrivacyExport(): Promise<void> {
  const res = await apiFetch('/privacy/export', { method: 'POST' })
  if (res.status === 429) throw new PrivacyExportRateLimitedError()
  if (!res.ok) throw new Error(`/privacy/export returned ${res.status}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'strava-export.json'
  a.click()
  URL.revokeObjectURL(url)
}

export async function postPrivacyDelete(): Promise<{ deleted: boolean }> {
  const res = await apiFetch('/privacy/delete', { method: 'POST' })
  if (!res.ok) throw new Error(`/privacy/delete returned ${res.status}`)
  return res.json() as Promise<{ deleted: boolean }>
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(privacy): add postPrivacyExport and postPrivacyDelete API functions"
```

---

## Task 3: Update `GdprFooter`

**Files:**
- Modify: `frontend/src/components/GdprFooter.tsx`

- [ ] **Step 1: Replace the entire file content**

```tsx
interface Props {
  onPrivacyClick?: () => void
}

export default function GdprFooter({ onPrivacyClick }: Props) {
  return (
    <footer className="gdpr-footer">
      <a href="#">Privacy Policy</a>
      {' · '}
      <a href="#">Terms of Service</a>
      {' · '}
      {onPrivacyClick ? (
        <button onClick={onPrivacyClick}>Data Deletion Info</button>
      ) : (
        <a href="#">Data Deletion Info</a>
      )}
    </footer>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GdprFooter.tsx
git commit -m "feat(privacy): add onPrivacyClick prop to GdprFooter"
```

---

## Task 4: Create `PrivacyPage`

**Files:**
- Create: `frontend/src/pages/PrivacyPage.tsx`

- [ ] **Step 1: Create the file with the full implementation**

```tsx
import { useState } from 'react'
import {
  postPrivacyExport,
  postPrivacyDelete,
  PrivacyExportRateLimitedError,
} from '../api/client'

type ExportStatus = 'idle' | 'loading' | 'success' | 'error' | 'rate_limited'
type DeleteStatus = 'idle' | 'confirming' | 'loading' | 'error'

interface Props {
  onDeleteComplete: () => void
}

export default function PrivacyPage({ onDeleteComplete }: Props) {
  const [exportStatus, setExportStatus] = useState<ExportStatus>('idle')
  const [deleteStatus, setDeleteStatus] = useState<DeleteStatus>('idle')

  async function handleExport() {
    setExportStatus('loading')
    try {
      await postPrivacyExport()
      setExportStatus('success')
    } catch (err) {
      if (err instanceof PrivacyExportRateLimitedError) {
        setExportStatus('rate_limited')
      } else {
        setExportStatus('error')
      }
    }
  }

  async function handleDelete() {
    setDeleteStatus('loading')
    try {
      await postPrivacyDelete()
      onDeleteComplete()
    } catch {
      setDeleteStatus('error')
    }
  }

  const showConfirm =
    deleteStatus === 'confirming' ||
    deleteStatus === 'loading' ||
    deleteStatus === 'error'

  return (
    <div className="privacy-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Privacy</h1>
          <p className="page-subtitle">Manage your data and account</p>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <span className="card__label">Your Data</span>
        </div>
        <div className="card__body">
          <p className="privacy-description">
            Download a copy of all your stored data as JSON.
          </p>
          <div className="privacy-actions">
            <button
              className="btn btn--primary"
              onClick={handleExport}
              disabled={exportStatus === 'loading'}
            >
              {exportStatus === 'loading' ? (
                <>
                  <span className="btn__spinner" aria-hidden="true" />
                  Downloading…
                </>
              ) : (
                'Download My Data'
              )}
            </button>
            {exportStatus === 'success' && (
              <span className="privacy-feedback">Download started.</span>
            )}
            {exportStatus === 'error' && (
              <span className="privacy-feedback privacy-feedback--error">
                Export failed. Please try again.
              </span>
            )}
            {exportStatus === 'rate_limited' && (
              <span className="privacy-feedback privacy-feedback--error">
                You can download at most 5 times per hour.
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <span className="card__label">Delete Account</span>
        </div>
        <div className="card__body">
          <p className="privacy-description">
            Permanently remove your account and all associated data from this app.
          </p>
          {!showConfirm && (
            <button
              className="btn btn--danger"
              onClick={() => setDeleteStatus('confirming')}
            >
              Delete My Account
            </button>
          )}
          {showConfirm && (
            <div className="privacy-confirm">
              <p className="privacy-confirm__warning">
                This cannot be undone. All your activities, goals, and club
                memberships will be permanently deleted.
              </p>
              {deleteStatus === 'error' && (
                <p className="privacy-feedback privacy-feedback--error">
                  Deletion failed. Please try again.
                </p>
              )}
              <div className="privacy-confirm__actions">
                <button
                  className="btn btn--danger"
                  onClick={handleDelete}
                  disabled={deleteStatus === 'loading'}
                >
                  {deleteStatus === 'loading' ? (
                    <>
                      <span className="btn__spinner" aria-hidden="true" />
                      Deleting…
                    </>
                  ) : (
                    'Confirm Delete'
                  )}
                </button>
                <button
                  className="btn btn--ghost"
                  onClick={() => setDeleteStatus('idle')}
                  disabled={deleteStatus === 'loading'}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/PrivacyPage.tsx
git commit -m "feat(privacy): add PrivacyPage with export and delete flows"
```

---

## Task 5: Wire `HomePage`

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Add `'privacy'` to the `Page` union type (line 8)**

Change:
```ts
type Page = 'dashboard' | 'clubs'
```
To:
```ts
type Page = 'dashboard' | 'clubs' | 'privacy'
```

- [ ] **Step 2: Add `PrivacyPage` to the imports at the top of the file**

After the existing page imports, add:
```tsx
import PrivacyPage from './PrivacyPage'
```

- [ ] **Step 3: Pass `onPrivacyClick` to `GdprFooter`**

Change:
```tsx
<GdprFooter />
```
To:
```tsx
<GdprFooter onPrivacyClick={() => setPage('privacy')} />
```

- [ ] **Step 4: Render `PrivacyPage` in the `<main>` block**

After the existing `{page === 'clubs' && <ClubsPage ... />}` line, add:
```tsx
{page === 'privacy' && <PrivacyPage onDeleteComplete={onLogout} />}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat(privacy): wire PrivacyPage into HomePage via GdprFooter"
```

---

## Task 6: End-to-End Verification

**No files to change.** Start the dev server and verify the complete flow in a browser.

- [ ] **Step 1: Start the dev server**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173`. Log in if not already authenticated (requires the backend and Postgres running: `docker compose up db -d && uv run uvicorn backend.main:app --reload --port 8000`).

- [ ] **Step 2: Verify footer navigation**

In the GDPR footer at the bottom, click "Data Deletion Info".

Expected: the page switches to the Privacy view showing a "Privacy" title, a "YOUR DATA" card, and a "DELETE ACCOUNT" card. The Dashboard and Clubs nav tabs are still active and clickable.

- [ ] **Step 3: Verify nav tabs still work from privacy page**

While on the Privacy page, click "Dashboard" in the nav.

Expected: switches back to the Dashboard page. Click "Data Deletion Info" in the footer again — returns to Privacy.

- [ ] **Step 4: Verify export flow**

Click "Download My Data".

Expected: button shows spinner + "Downloading…" while the request is in flight, then "Download started." appears inline. A file named `strava-export.json` is saved by the browser. Open the file — it should contain your activities, goal, and profile data but no tokens.

- [ ] **Step 5: Verify export rate limit message**

Click "Download My Data" 6 times in quick succession (the limit is 5/hour).

Expected: after the 6th click, the inline message reads "You can download at most 5 times per hour." instead of the generic error.

- [ ] **Step 6: Verify delete confirmation expand**

Click "Delete My Account".

Expected: the button disappears and a danger-tinted panel appears with the warning text, a "Confirm Delete" button, and a "Cancel" button.

- [ ] **Step 7: Verify cancel collapses the confirmation**

Click "Cancel".

Expected: the confirmation panel disappears and "Delete My Account" button reappears.

- [ ] **Step 8: Verify the full delete flow**

Click "Delete My Account" → "Confirm Delete".

Expected: "Confirm Delete" shows spinner + "Deleting…", all buttons disabled. On success, the page redirects to the login screen. Attempting to log in with the same Strava account creates a fresh user with no activities or goal.

- [ ] **Step 9: Verify danger button styling in both themes**

Toggle between dark and light mode using the theme button in the nav.

Expected: "Delete My Account" and "Confirm Delete" buttons are danger-tinted in both themes (red background-dim, red text). Hovering fills the button solid red.
