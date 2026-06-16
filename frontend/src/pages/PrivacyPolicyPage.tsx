import GdprFooter from '../components/GdprFooter'

export default function PrivacyPolicyPage() {
  return (
    <div className="legal-root">
      <main className="legal-main">
        <div className="page-header">
          <div>
            <h1 className="page-title">Privacy Policy</h1>
            <p className="page-subtitle">Last updated: June 14, 2026</p>
          </div>
          <button className="legal-back" onClick={() => { window.location.href = '/' }}>
            ← Back to app
          </button>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Who We Are</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <p>
                This service is operated by <strong>Elias De Coppel</strong> as an individual
                developer. You can reach us at{' '}
                <a href="mailto:elias.decoppel@gmail.com">elias.decoppel@gmail.com</a>.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Data We Collect</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>What we store</h3>
              <ul>
                <li>Your Strava athlete ID (a numeric identifier assigned by Strava)</li>
                <li>
                  Your running activities: name, distance, and date — only running activities are
                  stored; cycling, swimming, and all other activity types are discarded and never
                  saved
                </li>
                <li>Your yearly running goal (a distance in km that you set in the app)</li>
                <li>Your Strava club memberships (club names and IDs)</li>
                <li>One session cookie used for authentication — not for tracking or advertising</li>
              </ul>
            </div>
            <div className="legal-section">
              <h3>What we never collect</h3>
              <ul>
                <li>
                  OAuth access tokens — these are encrypted at rest and never stored in readable
                  form or logged
                </li>
                <li>Heart rate, GPS routes, power data, cadence, or any health metrics</li>
                <li>Analytics or advertising cookies</li>
                <li>Any data not listed above</li>
              </ul>
            </div>
            <div className="legal-section">
              <h3>Why we collect it</h3>
              <p>
                You explicitly authorized this app to read your Strava data via Strava OAuth. That
                authorization is your consent. The sole purpose is to visualize your running goal
                progress and show club member progress within the app.
              </p>
            </div>
            <div className="legal-section">
              <h3>How long we keep it</h3>
              <p>
                We keep your data for as long as you have an account. If you delete your account via
                the Privacy page, all your data is permanently erased immediately. If you revoke
                this app's access in your Strava settings, Strava notifies us and we automatically
                erase all your data.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Your Rights</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <ul>
                <li>
                  <strong>Download your data:</strong> use the "Download My Data" button on the
                  Privacy page to receive a JSON export of everything we store about you
                </li>
                <li>
                  <strong>Delete your data:</strong> use the "Delete My Account" button on the
                  Privacy page for immediate, permanent erasure
                </li>
                <li>
                  <strong>Withdraw consent:</strong> revoke access in your Strava connected apps
                  settings — we erase your data automatically
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Security & Third Parties</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>Security</h3>
              <p>
                OAuth tokens are encrypted at rest using Fernet symmetric encryption. Session
                cookies are HttpOnly, Secure, and SameSite=Lax. No user data is transmitted to any
                third party other than as described below.
              </p>
            </div>
            <div className="legal-section">
              <h3>Third parties</h3>
              <p>
                The only third party is Strava Inc., which is the source of your activity data and
                the OAuth provider. We do not share data with advertising networks, analytics
                providers, or any other parties. We do not sell, rent, or share your data.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Contact & Changes</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <p>
                For any questions about your data, contact{' '}
                <a href="mailto:elias.decoppel@gmail.com">elias.decoppel@gmail.com</a>. If this
                policy changes, the "Last updated" date at the top of this page will be updated.
                Continued use of the app after changes constitutes acceptance.
              </p>
            </div>
          </div>
        </div>
      </main>
      <GdprFooter />
    </div>
  )
}
