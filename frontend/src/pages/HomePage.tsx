import { useState } from 'react'
import { postSessionLogout, type SessionUser } from '../api/client'
import GdprFooter from '../components/GdprFooter'
import DashboardPage from './DashboardPage'

type Page = 'dashboard'

interface Props {
  user: SessionUser
  onLogout: () => void
}

export default function HomePage({ user, onLogout }: Props) {
  const [page] = useState<Page>('dashboard')
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await postSessionLogout()
    } finally {
      onLogout()
    }
  }

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div className="app-nav__brand">SGV</div>
        <div className="app-nav__links">
          <button className={`app-nav__link${page === 'dashboard' ? ' app-nav__link--active' : ''}`}>
            Dashboard
          </button>
        </div>
        <button
          className="app-nav__logout"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? '…' : 'Logout →'}
        </button>
      </nav>
      <main className="app-main">
        <DashboardPage athleteId={user.strava_athlete_id} />
      </main>
      <GdprFooter />
    </div>
  )
}
