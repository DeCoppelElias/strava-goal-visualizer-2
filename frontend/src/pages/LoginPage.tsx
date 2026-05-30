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
    <div>
      <h1>Strava Goal Visualizer</h1>
      {oauthError === 'auth_failed' && (
        <p role="alert" style={{ color: 'red' }}>Authentication failed — please try again.</p>
      )}
      {oauthError === 'strava_error' && (
        <p role="alert" style={{ color: 'red' }}>Strava returned an error — please try again.</p>
      )}
      {apiError && <p role="alert" style={{ color: 'red' }}>{apiError}</p>}
      <p>Connect your Strava account to visualize your yearly running goal.</p>
      <button onClick={handleConnect} disabled={loading}>
        {loading ? 'Redirecting…' : 'Connect with Strava'}
      </button>
      <GdprFooter />
    </div>
  )
}
