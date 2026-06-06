import { useEffect, useState } from 'react'
import {
  postSync,
  SyncCooldownError,
  getPersonalDashboard,
  putGoal,
  type PersonalDashboard,
} from '../api/client'

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

type DashState =
  | { status: 'loading' }
  | { status: 'not_synced' }
  | { status: 'error' }
  | { status: 'loaded'; data: PersonalDashboard }

export default function DashboardPage({ athleteId }: Props) {
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

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Athlete #{athleteId}</p>
      </div>

      {/* Sync card */}
      <div className="card">
        <div className="card__header">
          <span className="card__label">Sync Activities</span>
        </div>
        <div className="card__body">
          <button
            className="btn btn--primary"
            onClick={() => void handleSync()}
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

          {syncCount !== null && lastSyncAt !== null && (
            <div className="sync-result">
              <p className="sync-count">
                {syncCount} {syncCount === 1 ? 'run' : 'runs'} synced
              </p>
              <p className="sync-timestamp">Last synced {formatSyncTime(lastSyncAt)}</p>
            </div>
          )}

          {syncError?.type === 'cooldown' && (
            <p className="status-msg status-msg--warning" role="alert">
              Sync unavailable — try again in {Math.ceil(syncError.retryAfterSeconds / 60)} min
            </p>
          )}

          {syncError?.type === 'api' && (
            <p className="status-msg status-msg--danger" role="alert">
              Sync failed — please try again.
            </p>
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
          {/* Stats row */}
          <div className="stats-row">
            <div className="stat-tile">
              <span className="stat-tile__value">
                {dashState.data.distance_to_date_km.toFixed(1)}
              </span>
              <span className="stat-tile__label">Total km</span>
            </div>
            <div className="stat-tile">
              <span className="stat-tile__value">
                {dashState.data.progress_pct.toFixed(1)}%
              </span>
              <span className="stat-tile__label">Complete</span>
            </div>
            <div className="stat-tile">
              <span
                className={`pace-badge ${
                  dashState.data.on_pace ? 'pace-badge--on' : 'pace-badge--behind'
                }`}
              >
                {dashState.data.on_pace ? 'On pace' : 'Behind pace'}
              </span>
              <span className="stat-tile__label">Pace</span>
            </div>
          </div>

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
                      <span className="sync-btn__spinner" aria-hidden="true" />
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
