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
