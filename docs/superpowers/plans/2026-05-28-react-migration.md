# React Migration Plan (Streamlit → React + Vite)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit Python frontend with a React + Vite + TypeScript SPA, implementing TASK-2.8 (login/auth UI) as the first page, and updating all infrastructure and documentation to reflect the new stack.

**Architecture:** The React app runs in the browser and calls FastAPI directly via `fetch(..., { credentials: 'include' })`. The browser handles the session cookie natively — no cookie extraction hacks required. FastAPI's existing CORS config (`allow_credentials=True`, origin allowlist) already supports this. No backend code changes needed.

**Tech Stack:** React 18, TypeScript 5, Vite 5, Node 20, existing FastAPI backend (unchanged)

---

## File Map

### Deleted
- `frontend/app.py` — Streamlit app script
- `frontend/config.py` — Streamlit Python config
- `frontend/__init__.py` — Python package marker
- `frontend/Dockerfile` — Python/Streamlit Dockerfile (replaced)

### Created
- `frontend/Dockerfile` — Node dev server image
- `frontend/package.json` — Node project manifest
- `frontend/tsconfig.json` — TypeScript config
- `frontend/vite.config.ts` — Vite dev server config
- `frontend/index.html` — HTML entry point
- `frontend/src/vite-env.d.ts` — Vite env type declarations
- `frontend/src/main.tsx` — React root mount
- `frontend/src/App.tsx` — Auth state manager, top-level routing
- `frontend/src/api/client.ts` — Typed fetch wrapper (credentials: include)
- `frontend/src/pages/LoginPage.tsx` — Unauthenticated page
- `frontend/src/pages/HomePage.tsx` — Authenticated home (athlete ID + logout)
- `frontend/src/components/GdprFooter.tsx` — GDPR links rendered on every page

### Modified
- `pyproject.toml` — remove frontend Python dependency group + wheel package + mypy override
- `docker-compose.yml` — replace Streamlit service with Vite/Node service
- `.env.example` — add `VITE_API_BASE_URL`, update `FRONTEND_ORIGIN` port
- `.gitignore` — remove Streamlit entry, add `frontend/.env.local`
- `CLAUDE.md` — update stack description
- `docs/design.md` — update frontend stack references
- `docs/epics/backlog.md` — rewrite Output sections of TASK-2.8, 3.5, 5.4, 6.5, 7.6

---

## Task 1: Delete Streamlit Python files

**Files:** Delete `frontend/app.py`, `frontend/config.py`, `frontend/__init__.py`

- [ ] **Step 1: Delete the three Python files**

```bash
git rm frontend/app.py frontend/config.py frontend/__init__.py
```

Expected output:
```
rm 'frontend/app.py'
rm 'frontend/config.py'
rm 'frontend/__init__.py'
```

- [ ] **Step 2: Confirm deletion**

```bash
git status
```
Expected: the three files listed under "Changes to be committed: deleted"

---

## Task 2: Update `pyproject.toml`

**Files:** Modify `pyproject.toml`

- [ ] **Step 1: Remove the `frontend` dependency group, wheel package, and mypy override**

In `pyproject.toml`, apply these three changes:

**Remove** from `[tool.hatch.build.targets.wheel]`:
```toml
# Before
packages = ["backend", "frontend"]

# After
packages = ["backend"]
```

**Remove** the entire `frontend` dependency group:
```toml
# Remove this entire block:
frontend = [
    "streamlit>=1.36",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]
```

**Remove** the `streamlit.*` mypy override:
```toml
# Remove this entire block:
[[tool.mypy.overrides]]
module = ["streamlit.*"]
ignore_missing_imports = true
```

- [ ] **Step 2: Verify backend tests still pass (no accidental breakage)**

```bash
pytest -q
```
Expected: `33 passed`

---

## Task 3: Scaffold React + Vite + TypeScript

**Files:** Create `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/vite-env.d.ts`, `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "strava-goal-visualizer",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "typescript": "^5.6.3",
    "vite": "^5.4.10"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src", "vite.config.ts"]
}
```

- [ ] **Step 3: Create `frontend/vite.config.ts`**

The `host: true` option makes Vite listen on all interfaces, which is required for the Docker dev server to be reachable from outside the container.

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
})
```

- [ ] **Step 4: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Strava Goal Visualizer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/src/vite-env.d.ts`**

Declares the custom env var so TypeScript knows its type.

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

- [ ] **Step 6: Create `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

---

## Task 4: Install dependencies

**Files:** Generates `frontend/package-lock.json`

- [ ] **Step 1: Install Node dependencies from `frontend/`**

```bash
cd frontend && npm install
```

Expected: `node_modules/` created, `package-lock.json` generated. Output ends with something like `added 123 packages`.

- [ ] **Step 2: Verify TypeScript compiles (no src yet — just config check)**

```bash
npx tsc --noEmit
```

Expected: exits with code 0 (no errors; `src/` is empty so nothing to check yet).

---

## Task 5: Implement the API client

**Files:** Create `frontend/src/api/client.ts`

- [ ] **Step 1: Create `frontend/src/api/client.ts`**

This module is the single place that knows the base URL and always sends `credentials: 'include'`. All API calls go through here.

```ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
}

export interface SessionUser {
  strava_athlete_id: number
  created_at: string
}

export async function getSessionMe(): Promise<SessionUser | null> {
  const res = await apiFetch('/session/me')
  if (res.status === 401) return null
  if (!res.ok) throw new Error(`/session/me returned ${res.status}`)
  return res.json() as Promise<SessionUser>
}

export async function postOAuthAuthorize(): Promise<string> {
  const res = await apiFetch('/oauth/authorize', { method: 'POST' })
  if (!res.ok) throw new Error(`/oauth/authorize returned ${res.status}`)
  const data = await res.json() as { authorization_url: string }
  return data.authorization_url
}

export async function postSessionLogout(): Promise<void> {
  await apiFetch('/session/logout', { method: 'POST' })
}
```

---

## Task 6: Implement auth pages

**Files:** Create `frontend/src/components/GdprFooter.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/HomePage.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/components/GdprFooter.tsx`**

```tsx
export default function GdprFooter() {
  return (
    <footer style={{ marginTop: '2rem', fontSize: '0.8rem' }}>
      <a href="#">Privacy Policy</a>
      {' · '}
      <a href="#">Terms of Service</a>
      {' · '}
      <a href="#">Data Deletion Info</a>
    </footer>
  )
}
```

- [ ] **Step 2: Create `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useState } from 'react'
import { postOAuthAuthorize } from '../api/client'
import GdprFooter from '../components/GdprFooter'

interface Props {
  oauthError: string | null
}

export default function LoginPage({ oauthError }: Props) {
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  async function handleConnect() {
    setLoading(true)
    setApiError(null)
    try {
      const url = await postOAuthAuthorize()
      window.location.href = url
    } catch {
      setApiError('Backend unavailable — please try again.')
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Strava Goal Visualizer</h1>
      {oauthError === 'auth_failed' && (
        <p role="alert" style={{ color: 'red' }}>Authentication failed — please try again.</p>
      )}
      {oauthError === 'strava_error' && (
        <p role="alert" style={{ color: 'red' }}>Strava returned an error — please try again.</p>
      )}
      {apiError && <p role="alert" style={{ color: 'red' }}>{apiError}</p>}
      <p>Connect your Strava account to visualize your yearly running goal.</p>
      <button onClick={handleConnect} disabled={loading}>
        {loading ? 'Redirecting…' : 'Connect with Strava'}
      </button>
      <GdprFooter />
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/pages/HomePage.tsx`**

```tsx
import { useState } from 'react'
import { postSessionLogout, type SessionUser } from '../api/client'
import GdprFooter from '../components/GdprFooter'

interface Props {
  user: SessionUser
  onLogout: () => void
}

export default function HomePage({ user, onLogout }: Props) {
  const [loading, setLoading] = useState(false)

  async function handleLogout() {
    setLoading(true)
    try {
      await postSessionLogout()
    } finally {
      onLogout()
    }
  }

  return (
    <div>
      <h1>Strava Goal Visualizer</h1>
      <p>Connected as Strava athlete #{user.strava_athlete_id}</p>
      <button onClick={handleLogout} disabled={loading}>
        {loading ? 'Logging out…' : 'Logout'}
      </button>
      <GdprFooter />
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/App.tsx`**

Reads and clears `?error=` query params from OAuth failure redirects, checks auth state on mount, and renders the appropriate page.

```tsx
import { useEffect, useState } from 'react'
import { getSessionMe, type SessionUser } from './api/client'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'

type AuthState = 'loading' | 'unauthenticated' | 'authenticated'

function readAndClearOAuthError(): string | null {
  const params = new URLSearchParams(window.location.search)
  const error = params.get('error')
  if (error) {
    params.delete('error')
    const newSearch = params.toString()
    window.history.replaceState(
      {},
      '',
      newSearch ? `?${newSearch}` : window.location.pathname,
    )
  }
  return error
}

const oauthError = readAndClearOAuthError()

export default function App() {
  const [authState, setAuthState] = useState<AuthState>('loading')
  const [user, setUser] = useState<SessionUser | null>(null)

  useEffect(() => {
    getSessionMe()
      .then((u) => {
        if (u) {
          setUser(u)
          setAuthState('authenticated')
        } else {
          setAuthState('unauthenticated')
        }
      })
      .catch(() => setAuthState('unauthenticated'))
  }, [])

  if (authState === 'loading') return <p>Loading…</p>

  if (authState === 'authenticated' && user) {
    return (
      <HomePage
        user={user}
        onLogout={() => {
          setUser(null)
          setAuthState('unauthenticated')
        }}
      />
    )
  }

  return <LoginPage oauthError={oauthError} />
}
```

---

## Task 7: Verify frontend works standalone

**Files:** None — verification only

- [ ] **Step 1: Create `frontend/.env.local` with the local dev API URL**

```
VITE_API_BASE_URL=http://localhost:8000
```

This file is gitignored. Every developer and every Docker container needs it (or the Docker equivalent).

- [ ] **Step 2: Run the Vite dev server**

```bash
cd frontend && npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in Xms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://0.0.0.0:5173/
```

- [ ] **Step 3: Verify TypeScript compiles cleanly**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exits 0, no errors.

- [ ] **Step 4: Verify build succeeds**

```bash
cd frontend && npm run build
```

Expected: `dist/` directory created, no errors.

- [ ] **Step 5: Manual browser check (backend must be running)**

With FastAPI running on `localhost:8000`, visit `http://localhost:5173`.

✓ Page shows "Connect with Strava" button and GDPR links
✓ No console errors
✓ Network tab shows `GET /session/me` returning 401 (not logged in yet)

---

## Task 8: Update Docker infrastructure

**Files:** Replace `frontend/Dockerfile`, modify `docker-compose.yml`

- [ ] **Step 1: Replace `frontend/Dockerfile`**

The dev Dockerfile installs dependencies and runs the Vite dev server. Source files are mounted via docker-compose volumes for hot reload.

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 2: Update `docker-compose.yml` frontend service**

Replace the entire `frontend:` service block:

```yaml
  frontend:
    build:
      context: ./frontend
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/index.html:/app/index.html
      - ./frontend/vite.config.ts:/app/vite.config.ts
      - ./frontend/.env.local:/app/.env.local:ro
    ports:
      - "5173:5173"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:5173 > /dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
```

Note: `VITE_API_BASE_URL` must be `http://localhost:8000` — the URL **the browser** uses to reach the backend. Since the backend port is exposed on the host, `localhost:8000` is correct for both Docker and non-Docker dev.

The `.env.local` mount assumes the developer has already created `frontend/.env.local` (done in Task 7 Step 1).

Also remove the old `API_BASE_URL: http://backend:8000` override (it was Streamlit server-side; React doesn't need it).

---

## Task 9: Update `.env.example` and `.gitignore`

**Files:** Modify `.env.example`, `.gitignore`

- [ ] **Step 1: Update `.env.example`**

Replace the `# ---- Frontend ----` section:

```
# ---- Frontend ----
# URL of the FastAPI backend reachable from the USER'S BROWSER (not server-to-server)
VITE_API_BASE_URL=http://localhost:8000
# Origin of the React frontend (used by backend for CORS)
FRONTEND_ORIGIN=http://localhost:5173
```

The old `API_BASE_URL` line is removed. `FRONTEND_ORIGIN` port changes from `8501` to `5173`.

- [ ] **Step 2: Update `.gitignore`**

Remove the Streamlit entry and add React build artifacts:

```gitignore
# Remove this block:
# Streamlit
.streamlit/secrets.toml

# Add this block:
# React / Node frontend
frontend/.env.local
frontend/dist/
```

Note: `node_modules/` is already ignored by the existing `node_modules/` rule.

---

## Task 10: Update documentation

**Files:** Modify `CLAUDE.md`, `docs/design.md`, `docs/epics/backlog.md`

- [ ] **Step 1: Update `CLAUDE.md` — stack description header**

Replace:
```markdown
- **Frontend:** `frontend/` — Streamlit
```
With:
```markdown
- **Frontend:** `frontend/` — React + Vite (TypeScript)
```

- [ ] **Step 2: Update `CLAUDE.md` — domain structure comment**

Remove the sentence referencing Streamlit in the overview paragraph if present. The backend domain structure section remains unchanged.

- [ ] **Step 3: Update `docs/design.md` — §1 Overview**

Replace:
```
A Strava-integrated application with a Streamlit frontend and FastAPI backend, written in Python
```
With:
```
A Strava-integrated application with a React + Vite frontend and FastAPI backend
```

- [ ] **Step 4: Update `docs/design.md` — §5 Deployment Topology**

Replace:
```
- **Topology:** Separate deployments for Streamlit frontend, FastAPI backend, and PostgreSQL.
```
With:
```
- **Topology:** Separate deployments for React frontend (static SPA / Vite dev server), FastAPI backend, and PostgreSQL.
```

- [ ] **Step 5: Update `docs/epics/backlog.md` — TASK-2.8 Output section**

Replace the current Output bullet list with:

```markdown
**Output:**
- `frontend/src/api/client.ts` — `fetch` wrapper with `credentials: 'include'` on every call; typed functions: `getSessionMe()`, `postOAuthAuthorize()`, `postSessionLogout()`
- `frontend/src/App.tsx` — reads and clears `?error=` query param; calls `getSessionMe()` on mount; renders `LoginPage` or `HomePage` based on auth state
- `frontend/src/pages/LoginPage.tsx` — displays OAuth error messages; "Connect with Strava" button calls `postOAuthAuthorize()` then sets `window.location.href`
- `frontend/src/pages/HomePage.tsx` — shows athlete ID; "Logout" button calls `postSessionLogout()` then resets auth state in `App`
- `frontend/src/components/GdprFooter.tsx` — GDPR placeholder links rendered on all pages
```

- [ ] **Step 6: Update `docs/epics/backlog.md` — TASK-3.5 Output section**

Replace Streamlit-specific output with:

```markdown
**Output:**
- `frontend/src/api/client.ts` extended with `postSync()` returning `{ synced_activities: number, last_sync_completed_at: string }`
- `frontend/src/pages/SyncPage.tsx` — "Sync Activities" button calls `POST /sync`; shows activity table (name, date, distance, moving time, sport type); shows last sync timestamp; shows cooldown error ("Sync unavailable — try again in X minutes") on 429 response
```

- [ ] **Step 7: Update `docs/epics/backlog.md` — TASK-5.4 Output section**

Replace Streamlit-specific output with:

```markdown
**Output:**
- `frontend/src/api/client.ts` extended with `getPersonalDashboard()` and `putGoal(km: number)`
- `frontend/src/pages/DashboardPage.tsx` — progress bar (distance to date vs goal); pace line chart using Recharts; key stats (total km, % complete, on-pace indicator); goal edit: number input + save button; last sync timestamp; empty state: "No running activities yet — sync your data to get started"; GDPR links visible
```

- [ ] **Step 8: Update `docs/epics/backlog.md` — TASK-6.5 Output section**

Replace Streamlit-specific output with:

```markdown
**Output:**
- `frontend/src/api/client.ts` extended with `getClubs()` and `getClubProgress(clubId: number)`
- `frontend/src/pages/ClubsPage.tsx` — club select dropdown from `GET /clubs`; per-member progress bar list for selected club; persistent disclaimer: "This club view shows members who have connected this app. It is a progress visualization, not a competition leaderboard."; empty state: "No other members of this club have connected the app yet."; GDPR links visible
```

- [ ] **Step 9: Update `docs/epics/backlog.md` — TASK-7.6 Output section**

Replace Streamlit-specific output with:

```markdown
**Output:**
- `frontend/src/pages/PrivacyPage.tsx` — "Download My Data" button calls `POST /privacy/export` and triggers a file download; "Delete My Account" button opens a confirmation step ("This will permanently delete all your data. This cannot be undone.") then calls `POST /privacy/delete` and redirects to the login page; GDPR document links visible
```

---

## Task 11: Commit

- [ ] **Step 1: Stage all changes**

```bash
git add frontend/ pyproject.toml docker-compose.yml .env.example .gitignore CLAUDE.md docs/design.md docs/epics/backlog.md
```

Note: `frontend/.env.local` is gitignored — it will not be staged. `frontend/node_modules/` is also gitignored. `frontend/package-lock.json` should be staged.

- [ ] **Step 2: Verify nothing sensitive is staged**

```bash
git diff --cached --stat
```

Confirm `frontend/.env.local` does NOT appear in the diff.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(frontend): replace Streamlit with React + Vite (TASK-2.8)"
```

---

## Task 12: Full system verification

- [ ] **Step 1: Start the full stack**

```bash
docker compose up --build
```

Expected: all three services (`db`, `backend`, `frontend`) reach healthy state.

- [ ] **Step 2: Run backend tests**

```bash
pytest -q
```

Expected: `33 passed`

- [ ] **Step 3: Full browser e2e — login flow**

Visit `http://localhost:5173`
✓ Page shows "Connect with Strava" button and GDPR links
✓ Click "Connect with Strava" → browser redirects to Strava OAuth consent
✓ Approve in Strava → browser redirected back to `http://localhost:5173`
✓ Page shows "Connected as Strava athlete #\<id\>" and "Logout" button

- [ ] **Step 4: Full browser e2e — session persistence**

Hard-refresh (`Ctrl+Shift+R`) `http://localhost:5173`
✓ Page still shows authenticated state (session cookie survives reload)

- [ ] **Step 5: Full browser e2e — logout flow**

Click "Logout"
✓ Page shows login state
✓ Hard-refresh still shows login state (cookie cleared)

- [ ] **Step 6: Full browser e2e — OAuth error handling**

Visit `http://localhost:5173?error=strava_error`
✓ Red error message shown on login page
✓ URL bar cleaned up (no `?error=...` after render)

---

## Dev workflow notes

**Running locally without Docker (recommended for frontend development):**

```bash
# Terminal 1: Docker Compose for DB + backend only
docker compose up db backend

# Terminal 2: Vite dev server
cd frontend && npm run dev
```

Visit `http://localhost:5173`. The browser calls FastAPI at `http://localhost:8000` (from `VITE_API_BASE_URL` in `.env.local`).

**Running everything in Docker:**

```bash
docker compose up --build
```

Requires `frontend/.env.local` to exist on the host (it is mounted into the container as read-only). The `VITE_API_BASE_URL` should still be `http://localhost:8000` because the browser (running on the host) reaches the backend through the exposed Docker port.
