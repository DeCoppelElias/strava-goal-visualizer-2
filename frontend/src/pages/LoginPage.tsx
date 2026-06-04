import { useState } from 'react'
import { postOAuthAuthorize } from '../api/client'
import GdprFooter from '../components/GdprFooter'

interface Props {
  oauthError: string | null
}

export default function LoginPage({ oauthError }: Props) {
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  async function handleConnect() {
    setLoading(true)
    setApiError(null)
    try {
      const url = await postOAuthAuthorize()
      window.location.href = url
    } catch {
      setApiError('Backend unavailable — please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <h1 className="login-brand">
        Strava<br />
        <span>Goal</span><br />
        Visualizer
      </h1>
      <p className="login-sub">Track your yearly running goal.</p>
      {(oauthError === 'auth_failed' || oauthError === 'strava_error') && (
        <p className="login-error" role="alert">
          {oauthError === 'auth_failed'
            ? 'Authentication failed — please try again.'
            : 'Strava returned an error — please try again.'}
        </p>
      )}
      {apiError && <p className="login-error" role="alert">{apiError}</p>}
      <button className="login-btn" onClick={handleConnect} disabled={loading}>
        {loading ? 'Redirecting…' : 'Connect with Strava'}
      </button>
      <GdprFooter />
    </div>
  )
}
