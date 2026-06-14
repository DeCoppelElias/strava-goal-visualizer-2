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

export interface DailyDistancePoint {
  date: string        // YYYY-MM-DD
  cumulative_km: number
}

export interface PersonalDashboard {
  goal_km: number
  distance_to_date_km: number
  progress_pct: number
  on_pace: boolean
  expected_pct: number
  last_sync_completed_at: string
  daily_series: DailyDistancePoint[]
}

export interface GoalResponse {
  yearly_running_goal_km: number
}

export async function getPersonalDashboard(): Promise<PersonalDashboard | null> {
  const res = await apiFetch('/dashboard/personal')
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`/dashboard/personal returned ${res.status}`)
  return res.json() as Promise<PersonalDashboard>
}

export async function putGoal(km: number): Promise<GoalResponse> {
  const res = await apiFetch('/goals', {
    method: 'PUT',
    body: JSON.stringify({ yearly_running_goal_km: km }),
  })
  if (!res.ok) throw new Error(`/goals returned ${res.status}`)
  return res.json() as Promise<GoalResponse>
}

export interface Club {
  id: number
  name: string
}

export interface MemberProgress {
  strava_athlete_id: number
  display_name: string
  distance_to_date_km: number
  goal_km: number
  progress_pct: number
  daily_series: DailyDistancePoint[]
}

export interface ClubDashboard {
  club_id: number
  club_name: string
  members: MemberProgress[]
}

export async function getClubs(): Promise<Club[]> {
  const res = await apiFetch('/clubs')
  if (!res.ok) throw new Error(`/clubs returned ${res.status}`)
  return res.json() as Promise<Club[]>
}

export async function getClubDashboard(clubId: number): Promise<ClubDashboard> {
  const res = await apiFetch(`/dashboard/club/${clubId}`)
  if (!res.ok) throw new Error(`/dashboard/club/${clubId} returned ${res.status}`)
  return res.json() as Promise<ClubDashboard>
}

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
