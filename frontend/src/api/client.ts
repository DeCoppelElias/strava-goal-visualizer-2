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

export interface SyncResponse {
  synced_activities: number
  last_sync_completed_at: string
}

export class SyncCooldownError extends Error {
  constructor(public readonly retryAfterSeconds: number) {
    super(`Sync on cooldown. Retry after ${retryAfterSeconds}s`)
    this.name = 'SyncCooldownError'
  }
}

export async function postSync(): Promise<SyncResponse> {
  const res = await apiFetch('/sync', { method: 'POST' })
  if (res.status === 429) {
    const retryAfter = res.headers.get('Retry-After')
    throw new SyncCooldownError(retryAfter ? parseInt(retryAfter, 10) : 600)
  }
  if (!res.ok) throw new Error(`/sync returned ${res.status}`)
  return res.json() as Promise<SyncResponse>
}
