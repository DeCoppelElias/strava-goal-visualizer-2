import { useState } from 'react'
import { postOAuthAuthorize } from '../api/client'
import GdprFooter from '../components/GdprFooter'
import { APP_NAME } from '../config/site'

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
    <div className="login-root">
      <div className="login-center">
        <div className="login-mark" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="13,1 25,13 13,25 1,13" fill="var(--accent)" />
          </svg>
        </div>
        <h1 className="login-title">{APP_NAME}</h1>
        <p className="login-subtitle">Track your yearly running goal.</p>
        {(oauthError === 'auth_failed' || oauthError === 'strava_error') && (
          <p className="login-error" role="alert">
            {oauthError === 'auth_failed'
              ? 'Authentication failed — please try again.'
              : 'Strava returned an error — please try again.'}
          </p>
        )}
        {apiError && <p className="login-error" role="alert">{apiError}</p>}
        <button className="btn btn--primary" onClick={handleConnect} disabled={loading}>
          {loading ? 'Redirecting…' : 'Connect with Strava'}
        </button>
      </div>
      <GdprFooter />
    </div>
  )
}
