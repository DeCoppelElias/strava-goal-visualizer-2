interface Props {
  onPrivacyClick?: () => void
}

export default function GdprFooter({ onPrivacyClick }: Props) {
  return (
    <footer className="gdpr-footer">
      <a href="/privacy-policy">Privacy Policy</a>
      {' · '}
      <a href="/terms">Terms of Service</a>
      {' · '}
      {onPrivacyClick ? (
        <button onClick={onPrivacyClick}>Data Deletion Info</button>
      ) : (
        <a href="#">Data Deletion Info</a>
      )}
    </footer>
  )
}
