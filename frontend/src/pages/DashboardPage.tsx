import { useEffect, useState } from 'react'
import {
  postSync,
  SyncCooldownError,
  getPersonalDashboard,
  putGoal,
  type PersonalDashboard,
} from '../api/client'
import PaceChart from '../components/PaceChart'
import BadgeRow from '../components/BadgeRow'

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

function computeDashStats(data: PersonalDashboard) {
  const today = new Date()
  const year = today.getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365
  const dayOfYear =
    Math.floor((today.getTime() - new Date(year, 0, 1).getTime()) / 86400000) + 1
  const remainingKm = data.goal_km - data.distance_to_date_km
  const remainingWeeks = (daysInYear - dayOfYear) / 7
  const neededWeeklyPace = remainingKm <= 0 ? null : remainingKm / remainingWeeks
  const idealToDate = (dayOfYear / daysInYear) * data.goal_km
  const vsIdeal = data.distance_to_date_km - idealToDate
  return { neededWeeklyPace, vsIdeal }
}

type SyncError =
  | { type: 'cooldown'; retryAfterSeconds: number }
  | { type: 'api' }

type DashState =
  | { status: 'loading' }
  | { status: 'not_synced' }
  | { status: 'error' }
  | { status: 'loaded'; data: PersonalDashboard }

export default function DashboardPage({ athleteId: _athleteId }: Props) {
  const [syncing, setSyncing] = useState(false)
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null)
  const [syncCount, setSyncCount] = useState<number | null>(null)
  const [syncError, setSyncError] = useState<SyncError | null>(null)

  const [dashState, setDashState] = useState<DashState>({ status: 'loading' })
  const [goalInput, setGoalInput] = useState('')
  const [goalSaving, setGoalSaving] = useState(false)
  const [goalError, setGoalError] = useState<string | null>(null)

  async function fetchDashboard() {
    setDashState({ status: 'loading' })
    try {
      const data = await getPersonalDashboard()
      if (data === null) {
        setDashState({ status: 'not_synced' })
      } else {
        setDashState({ status: 'loaded', data })
        setGoalInput(String(Math.round(data.goal_km)))
      }
    } catch {
      setDashState({ status: 'error' })
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void fetchDashboard() }, [])

  async function handleSync() {
    setSyncing(true)
    setSyncError(null)
    try {
      const result = await postSync()
      setSyncCount(result.synced_activities)
      setLastSyncAt(result.last_sync_completed_at)
      await fetchDashboard()
    } catch (e) {
      if (e instanceof SyncCooldownError) {
        setSyncError({ type: 'cooldown', retryAfterSeconds: e.retryAfterSeconds })
      } else {
        setSyncError({ type: 'api' })
      }
    } finally {
      setSyncing(false)
    }
  }

  async function handleSaveGoal() {
    const km = parseFloat(goalInput)
    if (isNaN(km) || km < 1 || km > 100_000) {
      setGoalError('Goal must be between 1 and 100,000 km')
      return
    }
    setGoalSaving(true)
    setGoalError(null)
    try {
      await putGoal(km)
      await fetchDashboard()
    } catch {
      setGoalError('Failed to save goal — please try again')
    } finally {
      setGoalSaving(false)
    }
  }

  const dashStats = dashState.status === 'loaded' ? computeDashStats(dashState.data) : null

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{new Date().getFullYear()} · Running Goal</p>
        </div>
        {dashState.status === 'loaded' && (
          <BadgeRow distanceKm={dashState.data.distance_to_date_km} />
        )}
        <div className="sync-inline">
          <button
            className="btn btn--ghost"
            onClick={() => void handleSync()}
            disabled={syncing}
          >
            {syncing ? (
              <>
                <span className="btn__spinner" aria-hidden="true" />
                Syncing…
              </>
            ) : (
              'Sync'
            )}
          </button>
          {syncCount !== null && lastSyncAt !== null && (
            <span className="sync-feedback">
              {syncCount} {syncCount === 1 ? 'run' : 'runs'} synced · Last synced {formatSyncTime(lastSyncAt)}
            </span>
          )}
          {syncError?.type === 'cooldown' && (
            <span className="sync-feedback sync-feedback--warning" role="alert">
              Try again in {Math.ceil(syncError.retryAfterSeconds / 60)} min
            </span>
          )}
          {syncError?.type === 'api' && (
            <span className="sync-feedback sync-feedback--danger" role="alert">
              Sync failed — please try again
            </span>
          )}
        </div>
      </div>

      {/* Dashboard content */}
      {dashState.status === 'loading' && (
        <p className="dash-loading">Loading…</p>
      )}

      {dashState.status === 'error' && (
        <div className="card">
          <div className="card__body">
            <p className="status-msg status-msg--danger" role="alert">
              Failed to load dashboard data.
            </p>
            <button className="btn btn--ghost" onClick={() => void fetchDashboard()}>
              Retry
            </button>
          </div>
        </div>
      )}

      {dashState.status === 'not_synced' && (
        <div className="card">
          <div className="card__body">
            <p className="dash-empty">
              No running activities yet — sync your data to get started.
            </p>
          </div>
        </div>
      )}

      {dashState.status === 'loaded' && (
        <>
          {/* Pace chart card */}
          <div className="card">
            <div className="card__header">
              <span className="card__label">Progress vs Pace</span>
            </div>
            <div className="card__body card__body--chart">
              {dashState.data.daily_series.length === 0 ? (
                <p className="chart-empty">No runs recorded this year yet.</p>
              ) : (
                <>
                  <PaceChart
                    dailySeries={dashState.data.daily_series}
                    goalKm={dashState.data.goal_km}
                  />
                  <div className="member-row" style={{ marginTop: 16 }}>
                    <div className="member-row__bar-track">
                      <div
                        className="member-row__bar-fill"
                        style={{
                          width: `${Math.min(dashState.data.progress_pct, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="member-row__stats">
                      {dashState.data.progress_pct.toFixed(1)}%
                      {' · '}
                      {dashState.data.distance_to_date_km.toFixed(1)}
                      {' / '}
                      {dashState.data.goal_km.toFixed(0)} km
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Stats card */}
          {dashStats && (
            <div className="card">
              <div className="card__header">
                <span className="card__label">Stats</span>
              </div>
              <div className="card__body">
                <div className="stats-table">
                  <div className="stats-table__row">
                    <span className="stats-table__label">Total distance</span>
                    <span className="stats-table__value">
                      {dashState.data.distance_to_date_km.toFixed(1)} km
                    </span>
                  </div>
                  <div className="stats-table__row">
                    <span className="stats-table__label">Progress</span>
                    <span className="stats-table__value">
                      {dashState.data.progress_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="stats-table__row">
                    <span className="stats-table__label">Needed weekly pace</span>
                    <span
                      className={`stats-table__value${
                        dashStats.neededWeeklyPace === null ? ' stats-table__value--success' : ''
                      }`}
                    >
                      {dashStats.neededWeeklyPace === null
                        ? 'Goal achieved'
                        : `${dashStats.neededWeeklyPace.toFixed(1)} km/week`}
                    </span>
                  </div>
                  <div className="stats-table__row">
                    <span className="stats-table__label">vs. Ideal</span>
                    <span
                      className={`stats-table__value ${
                        dashStats.vsIdeal >= 0
                          ? 'stats-table__value--success'
                          : 'stats-table__value--danger'
                      }`}
                    >
                      {dashStats.vsIdeal >= 0 ? '+' : ''}
                      {dashStats.vsIdeal.toFixed(1)} km
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Goal edit card */}
          <div className="card">
            <div className="card__header">
              <span className="card__label">Yearly Goal</span>
            </div>
            <div className="card__body">
              <div className="goal-edit">
                <input
                  className="goal-input"
                  type="number"
                  min="1"
                  max="100000"
                  step="1"
                  value={goalInput}
                  onChange={(e) => setGoalInput(e.target.value)}
                  aria-label="Yearly running goal in km"
                />
                <span className="goal-input__unit">km</span>
                <button
                  className="btn btn--primary"
                  onClick={() => void handleSaveGoal()}
                  disabled={goalSaving}
                >
                  {goalSaving ? (
                    <>
                      <span className="btn__spinner" aria-hidden="true" />
                      Saving…
                    </>
                  ) : (
                    'Save'
                  )}
                </button>
              </div>
              {goalError && (
                <p className="status-msg status-msg--danger" role="alert">
                  {goalError}
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
