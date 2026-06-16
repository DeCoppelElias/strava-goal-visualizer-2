interface BadgeIconProps {
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  color: string
  width?: number
  height?: number
}

const SHIELD = 'M 10,2 L 70,2 Q 78,2 78,10 L 78,56 Q 66,80 40,94 Q 14,80 2,56 L 2,10 Q 2,2 10,2 Z'
const SHOE   = 'M 15,68 L 15,50 Q 15,42 22,38 L 34,34 L 58,30 Q 66,28 68,36 Q 70,44 66,54 Q 60,68 50,68 Z'

export default function BadgeIcon({ tier, color, width = 80, height = 96 }: BadgeIconProps) {
  const hasLaces = tier === 'silver' || tier === 'gold' || tier === 'platinum'
  const hasTread = tier === 'gold' || tier === 'platinum'
  const hasPanel = tier === 'platinum'

  return (
    <svg viewBox="0 0 80 96" width={width} height={height} xmlns="http://www.w3.org/2000/svg">
      {/* Shield */}
      <path d={SHIELD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Running shoe — Bronze: bare outline only */}
      <path d={SHOE} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Laces — Silver+ */}
      {hasLaces && (
        <>
          <line x1="26" y1="41" x2="52" y2="36" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="26" y1="47" x2="50" y2="43" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="26" y1="53" x2="46" y2="49" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {/* Sole tread — Gold+ */}
      {hasTread && (
        <>
          {/* Heel tread */}
          <line x1="17" y1="63" x2="24" y2="63" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="17" y1="66" x2="24" y2="66" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          {/* Toe tread */}
          <line x1="52" y1="62" x2="58" y2="62" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="50" y1="65" x2="56" y2="65" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {/* Midsole/upper panel line — Platinum */}
      {hasPanel && (
        <line x1="16" y1="58" x2="62" y2="48" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      )}
    </svg>
  )
}
