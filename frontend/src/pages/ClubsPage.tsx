import { useEffect, useState } from 'react'
import {
  getClubs,
  getClubDashboard,
  type Club,
  type ClubDashboard,
} from '../api/client'
import ClubPaceChart from '../components/ClubPaceChart'

interface Props {
  currentAthleteId: number
}

type ClubsStatus = 'loading' | 'error' | 'loaded'
type DashStatus = 'idle' | 'loading' | 'error' | 'loaded'

export default function ClubsPage({ currentAthleteId }: Props) {
  const [clubs, setClubs] = useState<Club[]>([])
  const [clubsStatus, setClubsStatus] = useState<ClubsStatus>('loading')
  const [selectedClubId, setSelectedClubId] = useState<number | null>(null)
  const [clubDashboard, setClubDashboard] = useState<ClubDashboard | null>(null)
  const [dashStatus, setDashStatus] = useState<DashStatus>('idle')

  async function fetchClubs() {
    setClubsStatus('loading')
    try {
      const data = await getClubs()
      setClubs(data)
      setClubsStatus('loaded')
      if (data.length > 0) setSelectedClubId(data[0].id)
    } catch {
      setClubsStatus('error')
    }
  }

  async function fetchDashboard(clubId: number) {
    setDashStatus('loading')
    setClubDashboard(null)
    try {
      const data = await getClubDashboard(clubId)
      setClubDashboard(data)
      setDashStatus('loaded')
    } catch {
      setDashStatus('error')
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void fetchClubs() }, [])

  useEffect(() => {
    if (selectedClubId !== null) void fetchDashboard(selectedClubId)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClubId])

  const selectedClub = clubs.find((c) => c.id === selectedClubId) ?? null

  return (
    <div className="clubs-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Clubs</h1>
          <p className="page-subtitle">{selectedClub?.name ?? ''}</p>
        </div>
      </div>

      {/* Club selector card */}
      <div className="card">
        <div className="card__header">
          <span className="card__label">Your Clubs</span>
        </div>
        <div className="card__body">
          {clubsStatus === 'loading' && (
            <p className="dash-loading">Loading…</p>
          )}
          {clubsStatus === 'error' && (
            <>
              <p className="status-msg status-msg--danger" role="alert">
                Failed to load clubs — please try again.
              </p>
              <button
                className="btn btn--ghost"
                onClick={() => void fetchClubs()}
                style={{ marginTop: 12 }}
              >
                Retry
              </button>
            </>
          )}
          {clubsStatus === 'loaded' && clubs.length === 0 && (
            <p className="dash-empty">No clubs found — sync your data first.</p>
          )}
          {clubsStatus === 'loaded' && clubs.length > 0 && (
            <select
              className="club-select"
              value={selectedClubId ?? ''}
              onChange={(e) => setSelectedClubId(Number(e.target.value))}
            >
              {clubs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>


      {/* Members card */}
      {selectedClubId !== null && clubs.length > 0 && (
        <div className="card">
          <div className="card__header">
            <span className="card__label">Members</span>
          </div>
          <div className="card__body">
            {dashStatus === 'loading' && (
              <p className="dash-loading">Loading…</p>
            )}
            {dashStatus === 'error' && (
              <>
                <p className="status-msg status-msg--danger" role="alert">
                  Failed to load club data — please try again.
                </p>
                <button
                  className="btn btn--ghost"
                  onClick={() => void fetchDashboard(selectedClubId)}
                  style={{ marginTop: 12 }}
                >
                  Retry
                </button>
              </>
            )}
            {dashStatus === 'loaded' &&
              clubDashboard !== null &&
              clubDashboard.members.length === 0 && (
                <p className="dash-empty">
                  No other members of this club have connected the app yet.
                </p>
              )}
            {dashStatus === 'loaded' &&
              clubDashboard !== null &&
              clubDashboard.members.length > 0 && (
                <>
                  <ClubPaceChart
                    members={clubDashboard.members}
                    currentAthleteId={currentAthleteId}
                  />
                  <div className="member-list" style={{ marginTop: 24 }}>
                    {clubDashboard.members.map((member) => (
                      <div key={member.strava_athlete_id} className="member-row">
                        <span className="member-row__name">
                          {member.display_name}
                        </span>
                        <div className="member-row__bar-track">
                          <div
                            className="member-row__bar-fill"
                            style={{
                              width: `${Math.min(member.progress_pct, 100)}%`,
                            }}
                          />
                        </div>
                        <span className="member-row__stats">
                          {member.progress_pct.toFixed(1)}%
                          {' · '}
                          {member.distance_to_date_km.toFixed(1)}
                          {' / '}
                          {member.goal_km.toFixed(0)} km
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
          </div>
        </div>
      )}
    </div>
  )
}
