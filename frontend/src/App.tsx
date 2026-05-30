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
