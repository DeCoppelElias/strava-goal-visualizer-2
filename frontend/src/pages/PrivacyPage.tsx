import { useState } from 'react'
import {
  postPrivacyExport,
  postPrivacyDelete,
  PrivacyExportRateLimitedError,
} from '../api/client'

type ExportStatus = 'idle' | 'loading' | 'success' | 'error' | 'rate_limited'
type DeleteStatus = 'idle' | 'confirming' | 'loading' | 'error'

interface Props {
  onDeleteComplete: () => void
}

export default function PrivacyPage({ onDeleteComplete }: Props) {
  const [exportStatus, setExportStatus] = useState<ExportStatus>('idle')
  const [deleteStatus, setDeleteStatus] = useState<DeleteStatus>('idle')

  async function handleExport() {
    setExportStatus('loading')
    try {
      await postPrivacyExport()
      setExportStatus('success')
    } catch (err) {
      if (err instanceof PrivacyExportRateLimitedError) {
        setExportStatus('rate_limited')
      } else {
        setExportStatus('error')
      }
    }
  }

  async function handleDelete() {
    setDeleteStatus('loading')
    try {
      await postPrivacyDelete()
      onDeleteComplete()
    } catch {
      setDeleteStatus('error')
    }
  }

  const showConfirm =
    deleteStatus === 'confirming' ||
    deleteStatus === 'loading' ||
    deleteStatus === 'error'

  return (
    <div className="privacy-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Privacy</h1>
          <p className="page-subtitle">Manage your data and account</p>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <span className="card__label">Your Data</span>
        </div>
        <div className="card__body">
          <p className="privacy-description">
            Download a copy of all your stored data as JSON.
          </p>
          <div className="privacy-actions">
            <button
              className="btn btn--primary"
              onClick={handleExport}
              disabled={exportStatus === 'loading'}
            >
              {exportStatus === 'loading' ? (
                <>
                  <span className="btn__spinner" aria-hidden="true" />
                  Downloading…
                </>
              ) : (
                'Download My Data'
              )}
            </button>
            {exportStatus === 'success' && (
              <span className="privacy-feedback">Download started.</span>
            )}
            {exportStatus === 'error' && (
              <span className="privacy-feedback privacy-feedback--error">
                Export failed. Please try again.
              </span>
            )}
            {exportStatus === 'rate_limited' && (
              <span className="privacy-feedback privacy-feedback--error">
                You can download at most 5 times per hour.
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <span className="card__label">Delete Account</span>
        </div>
        <div className="card__body">
          <p className="privacy-description">
            Permanently remove your account and all associated data from this app.
          </p>
          {!showConfirm && (
            <button
              className="btn btn--danger"
              onClick={() => setDeleteStatus('confirming')}
            >
              Delete My Account
            </button>
          )}
          {showConfirm && (
            <div className="privacy-confirm">
              <p className="privacy-confirm__warning">
                This cannot be undone. All your activities, goals, and club
                memberships will be permanently deleted.
              </p>
              {deleteStatus === 'error' && (
                <p className="privacy-feedback privacy-feedback--error">
                  Deletion failed. Please try again.
                </p>
              )}
              <div className="privacy-confirm__actions">
                <button
                  className="btn btn--danger"
                  onClick={handleDelete}
                  disabled={deleteStatus === 'loading'}
                >
                  {deleteStatus === 'loading' ? (
                    <>
                      <span className="btn__spinner" aria-hidden="true" />
                      Deleting…
                    </>
                  ) : (
                    'Confirm Delete'
                  )}
                </button>
                <button
                  className="btn btn--ghost"
                  onClick={() => setDeleteStatus('idle')}
                  disabled={deleteStatus === 'loading'}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
