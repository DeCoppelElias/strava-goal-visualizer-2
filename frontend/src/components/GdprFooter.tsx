interface Props {
  onPrivacyClick?: () => void
}

export default function GdprFooter({ onPrivacyClick }: Props) {
  return (
    <footer className="gdpr-footer">
      <a href="#">Privacy Policy</a>
      {' · '}
      <a href="#">Terms of Service</a>
      {' · '}
      {onPrivacyClick ? (
        <button onClick={onPrivacyClick}>Data Deletion Info</button>
      ) : (
        <a href="#">Data Deletion Info</a>
      )}
    </footer>
  )
}
