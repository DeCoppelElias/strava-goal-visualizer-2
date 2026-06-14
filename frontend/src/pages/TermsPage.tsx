import GdprFooter from '../components/GdprFooter'

export default function TermsPage() {
  return (
    <div className="legal-root">
      <main className="legal-main">
        <div className="page-header">
          <div>
            <h1 className="page-title">Terms of Service</h1>
            <p className="page-subtitle">Last updated: June 14, 2026</p>
          </div>
          <button className="legal-back" onClick={() => window.history.back()}>
            ← Back to app
          </button>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">About This Service</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>What it is</h3>
              <p>
                Strava Goal Visualizer is a personal running goal tracker that reads your authorized
                Strava data to help you visualize your yearly running progress. It is operated by{' '}
                <strong>Elias De Coppel</strong> as an individual developer, not as a business.
              </p>
            </div>
            <div className="legal-section">
              <h3>Not affiliated with Strava</h3>
              <p>
                This app is not affiliated with, endorsed by, or a product of Strava Inc. "Strava"
                is a registered trademark of Strava Inc.
              </p>
            </div>
            <div className="legal-section">
              <h3>Eligibility</h3>
              <p>
                You must have a Strava account to use this service and be old enough to consent to
                data processing in your country of residence.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Using the Service</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>What you authorize</h3>
              <p>
                By connecting with Strava, you authorize this app to read your Strava activities and
                profile. You can revoke this authorization at any time in your Strava connected apps
                settings, which triggers automatic deletion of all your data.
              </p>
            </div>
            <div className="legal-section">
              <h3>Acceptable use</h3>
              <ul>
                <li>This service is for personal use only</li>
                <li>Do not attempt to access other users' data</li>
                <li>Do not attempt to circumvent rate limits or reverse-engineer the service</li>
                <li>Do not use the service for any unlawful purpose</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Service Limitations</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>No warranty</h3>
              <p>
                This service is provided "as-is" with no guarantee of uptime, accuracy, or fitness
                for any particular purpose. Running progress figures are computed from the data
                Strava provides and may differ from Strava's own metrics.{' '}
                <strong>The service may be discontinued at any time without notice.</strong>
              </p>
            </div>
            <div className="legal-section">
              <h3>Limitation of liability</h3>
              <p>
                The developer is not liable for any direct, indirect, or consequential damages
                arising from the use of, or inability to use, this service. As this is a free
                service, the maximum liability is €0.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Termination</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <ul>
                <li>
                  You can delete your account and all associated data at any time via the Privacy
                  page
                </li>
                <li>We reserve the right to revoke your access if you violate these terms</li>
                <li>
                  <strong>
                    We reserve the right to shut down the service permanently at any time.
                  </strong>{' '}
                  In that event, all stored user data will be deleted.
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <span className="card__label">Governing Law & Contact</span>
          </div>
          <div className="card__body">
            <div className="legal-section">
              <h3>Governing law</h3>
              <p>These terms are governed by the laws of Belgium.</p>
            </div>
            <div className="legal-section">
              <h3>Contact and changes</h3>
              <p>
                For any questions, contact{' '}
                <a href="mailto:elias.decoppel@gmail.com">elias.decoppel@gmail.com</a>. We may
                update these terms at any time. The "Last updated" date at the top of this page will
                reflect the most recent change. Continued use after changes constitutes acceptance.
              </p>
            </div>
          </div>
        </div>
      </main>
      <GdprFooter />
    </div>
  )
}
