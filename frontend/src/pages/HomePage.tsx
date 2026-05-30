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
