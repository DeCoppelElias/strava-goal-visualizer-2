# User Nav Dropdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose `display_name` in the session endpoint, then replace the standalone "Log out" button with a user icon dropdown containing the user's name, an Account link, and Log out.

**Architecture:** Two sequential tasks. Task 1 is a pure backend + type change (no migration needed — `display_name` already exists in the DB). Task 2 is a frontend-only change: a `useRef`/`useState` dropdown inline in `HomePage.tsx`, a simplified `GdprFooter`, and new CSS in `index.css`.

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript + Vite (frontend), all CSS in `frontend/src/index.css`.

---

## File Map

| File | Change |
|---|---|
| `backend/auth/schemas.py` | Add `display_name: str` to `SessionMeResponse` |
| `backend/auth/router.py` | Pass `display_name` in `session_me` response |
| `tests/backend/auth/test_session_me.py` | Assert `display_name` in session response test |
| `frontend/src/api/client.ts` | Add `display_name: string` to `SessionUser` |
| `frontend/src/components/GdprFooter.tsx` | Remove Props, remove Data Deletion Info link, remove dead button styles in CSS |
| `frontend/src/pages/HomePage.tsx` | Add `'account'` page, user icon + dropdown, remove logout button, remove `onPrivacyClick` |
| `frontend/src/index.css` | Add `.user-menu` dropdown styles, remove `.gdpr-footer button` dead styles |

---

## Task 1 — Expose display_name in /session/me

**Files:**
- Modify: `backend/auth/schemas.py`
- Modify: `backend/auth/router.py:79-82`
- Modify: `tests/backend/auth/test_session_me.py:86-107`

- [ ] **Step 1: Update the test to assert display_name is returned**

In `tests/backend/auth/test_session_me.py`, update `test_session_me_returns_user_data_when_authenticated` to set `display_name` on the user and assert it comes back in the response:

```python
@pytest.mark.asyncio
async def test_session_me_returns_user_data_when_authenticated():
    from datetime import UTC, datetime

    from backend.auth.dependencies import get_current_user
    from backend.main import app
    from fastapi.testclient import TestClient

    created = datetime(2026, 1, 1, tzinfo=UTC)
    user = User(id=1, strava_athlete_id=12345678, display_name="Elias D.", created_at=created)

    async def _return_user():
        return user

    app.dependency_overrides[get_current_user] = _return_user
    try:
        with patch("backend.main._run_migrations"), TestClient(app) as client:
            response = client.get("/session/me")
        assert response.status_code == 200
        data = response.json()
        assert data["strava_athlete_id"] == 12345678
        assert data["display_name"] == "Elias D."
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
uv run pytest tests/backend/auth/test_session_me.py::test_session_me_returns_user_data_when_authenticated -v
```

Expected: FAIL — `display_name` key missing from response JSON.

- [ ] **Step 3: Add display_name to SessionMeResponse schema**

Replace `backend/auth/schemas.py` entirely:

```python
from datetime import datetime

from pydantic import BaseModel


class AuthorizeResponse(BaseModel):
    authorization_url: str


class SessionMeResponse(BaseModel):
    strava_athlete_id: int
    display_name: str
    created_at: datetime


class LogoutResponse(BaseModel):
    ok: bool


class RevokeResponse(BaseModel):
    ok: bool
```

- [ ] **Step 4: Pass display_name in the router response**

In `backend/auth/router.py`, update lines 79–82:

```python
    return SessionMeResponse(
        strava_athlete_id=current_user.strava_athlete_id,
        display_name=current_user.display_name,
        created_at=current_user.created_at,
    )
```

- [ ] **Step 5: Run the full auth test suite**

```bash
uv run pytest tests/backend/auth/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/auth/schemas.py backend/auth/router.py tests/backend/auth/test_session_me.py
git commit -m "feat(auth): expose display_name in /session/me response"
```

---

## Task 2 — User icon dropdown + GdprFooter simplification

**Files:**
- Modify: `frontend/src/api/client.ts:14-17`
- Modify: `frontend/src/components/GdprFooter.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/index.css`

### Step 1: Add display_name to SessionUser type

- [ ] In `frontend/src/api/client.ts`, update the `SessionUser` interface (lines 14–17):

```ts
export interface SessionUser {
  strava_athlete_id: number
  display_name: string
  created_at: string
}
```

### Step 2: Simplify GdprFooter

- [ ] Replace `frontend/src/components/GdprFooter.tsx` entirely:

```tsx
export default function GdprFooter() {
  return (
    <footer className="gdpr-footer">
      <a href="/privacy-policy">Privacy Policy</a>
      {' · '}
      <a href="/terms">Terms of Service</a>
    </footer>
  )
}
```

### Step 3: Remove dead GdprFooter button CSS

- [ ] In `frontend/src/index.css`, remove the `.gdpr-footer button` and `.gdpr-footer button:hover` blocks (lines 552–565):

Find and delete this block:

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

### Step 4: Add user-menu CSS

- [ ] In `frontend/src/index.css`, add the following block directly after the `.app-nav__actions` rule (after line 228):

```css
/* ── User menu dropdown ──────────────────────────────── */

.user-menu {
  position: relative;
}

.user-menu__panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 160px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-menu__name {
  font-size: 12px;
  color: var(--text-3);
  padding: 6px 10px;
  font-weight: 500;
}

.user-menu__item {
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-family: 'Manrope', sans-serif;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease;
}

.user-menu__item:hover {
  background: var(--surface-2);
  color: var(--text-1);
}

.user-menu__item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

### Step 5: Rewrite HomePage with the user icon dropdown

- [ ] Replace `frontend/src/pages/HomePage.tsx` entirely:

```tsx
import { useState, useRef, useEffect } from 'react'
import { postSessionLogout, type SessionUser } from '../api/client'
import GdprFooter from '../components/GdprFooter'
import DashboardPage from './DashboardPage'
import ClubsPage from './ClubsPage'
import PrivacyPage from './PrivacyPage'
import { getTheme, setTheme, type Theme } from '../theme'

type Page = 'dashboard' | 'clubs' | 'account'

interface Props {
  user: SessionUser
  onLogout: () => void
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7.5" cy="7.5" r="2.5" stroke="currentColor" strokeWidth="1.3" />
      <line x1="7.5" y1="0.5" x2="7.5" y2="2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="7.5" y1="12.5" x2="7.5" y2="14.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="0.5" y1="7.5" x2="2.5" y2="7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="12.5" y1="7.5" x2="14.5" y2="7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="2.6" y1="2.6" x2="4" y2="4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="11" y1="11" x2="12.4" y2="12.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="2.6" y1="12.4" x2="4" y2="11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="11" y1="4" x2="12.4" y2="2.6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 9.5A5.5 5.5 0 0 1 5 2.5a6 6 0 1 0 7 7z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7.5" cy="4.5" r="2.5" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M2 13.5c0-3.038 2.462-5.5 5.5-5.5s5.5 2.462 5.5 5.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function HomePage({ user, onLogout }: Props) {
  const [page, setPage] = useState<Page>('dashboard')
  const [loggingOut, setLoggingOut] = useState(false)
  const [theme, setThemeState] = useState<Theme>(getTheme)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  function toggleTheme() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await postSessionLogout()
    } finally {
      onLogout()
    }
  }

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div className="app-nav__brand">SGV</div>
        <div className="app-nav__links">
          <button
            className={`app-nav__link${page === 'dashboard' ? ' app-nav__link--active' : ''}`}
            onClick={() => setPage('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`app-nav__link${page === 'clubs' ? ' app-nav__link--active' : ''}`}
            onClick={() => setPage('clubs')}
          >
            Clubs
          </button>
        </div>
        <div className="app-nav__actions">
          <button
            className="btn btn--icon"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <div className="user-menu" ref={menuRef}>
            <button
              className="btn btn--icon"
              onClick={() => setMenuOpen(o => !o)}
              aria-label="User menu"
            >
              <UserIcon />
            </button>
            {menuOpen && (
              <div className="user-menu__panel">
                <span className="user-menu__name">
                  {user.display_name || `Athlete #${user.strava_athlete_id}`}
                </span>
                <button
                  className="user-menu__item"
                  onClick={() => { setPage('account'); setMenuOpen(false) }}
                >
                  Account
                </button>
                <button
                  className="user-menu__item"
                  onClick={() => { setMenuOpen(false); void handleLogout() }}
                  disabled={loggingOut}
                >
                  {loggingOut ? 'Logging out…' : 'Log out'}
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>
      <main className="app-main">
        {page === 'dashboard' && (
          <DashboardPage athleteId={user.strava_athlete_id} />
        )}
        {page === 'clubs' && <ClubsPage currentAthleteId={user.strava_athlete_id} />}
        {page === 'account' && <PrivacyPage onDeleteComplete={onLogout} />}
      </main>
      <GdprFooter />
    </div>
  )
}
```

### Step 6: Run the TypeScript type-check

- [ ] From `frontend/`:

```bash
npm run build
```

Expected: build succeeds with no type errors. (This catches any `SessionUser.display_name` or `GdprFooter` prop mismatches across the codebase.)

### Step 7: Commit

- [ ]
```bash
git add frontend/src/api/client.ts frontend/src/components/GdprFooter.tsx frontend/src/pages/HomePage.tsx frontend/src/index.css
git commit -m "feat(nav): replace logout button with user icon dropdown; simplify GdprFooter"
```
