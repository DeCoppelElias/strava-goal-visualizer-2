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
