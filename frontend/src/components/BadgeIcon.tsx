interface BadgeIconProps {
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  color: string
  width?: number
  height?: number
}

const SHIELD = 'M 10,2 L 70,2 Q 78,2 78,10 L 78,56 Q 66,80 40,94 Q 14,80 2,56 L 2,10 Q 2,2 10,2 Z'

// Outer silhouette: heel wraps around at back-bottom, thick midsole extends at toe,
// raised toe box curves up before coming down.
// Clockwise from heel-bottom: back wrap → up heel → over heel counter → collar →
// upper → raised toe → toe front → midsole junction → extended sole toe →
// sole bottom curve → back to heel.
const SHOE = [
  'M 12,68',           // heel bottom-left junction
  'Q 6,68 6,58',       // heel wraps around back-bottom (extends left of upper)
  'L 8,44',            // heel back going up
  'Q 8,32 16,26',      // heel counter top curve
  'Q 24,20 34,20',     // collar/ankle opening
  'L 52,18',           // tongue top toward toe
  'Q 62,16 66,24',     // raised toe box (curves up then down)
  'Q 70,32 68,46',     // toe front
  'Q 66,58 58,62',     // toe-midsole junction
  'Q 68,62 70,66',     // midsole extends past upper at toe
  'Q 68,72 60,72',     // toe bottom of sole
  'Q 40,76 20,72',     // sole bottom sweep (characteristic running sole curve)
  'Q 14,72 12,68',     // back to heel
  'Z',
].join(' ')

// Inner heel counter arc: parallels the outer heel, creates visible heel cup
const HEEL_ARC = 'M 10,64 Q 12,44 20,34 Q 24,26 30,22'

// Midsole panel line: runs across shoe at upper/midsole boundary (Platinum)
const PANEL = 'M 12,62 Q 34,60 58,62'

export default function BadgeIcon({ tier, color, width = 80, height = 96 }: BadgeIconProps) {
  const hasLaces = tier === 'silver' || tier === 'gold' || tier === 'platinum'
  const hasTread = tier === 'gold' || tier === 'platinum'
  const hasPanel = tier === 'platinum'

  return (
    <svg viewBox="0 0 80 96" width={width} height={height} xmlns="http://www.w3.org/2000/svg">
      {/* Shield */}
      <path d={SHIELD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Shoe outer silhouette */}
      <path d={SHOE} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Heel counter inner arc — makes back of shoe recognisable as a running heel */}
      <path d={HEEL_ARC} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      {/* Lace windows — Silver+: rectangular cut-outs across the upper tongue */}
      {hasLaces && (
        <>
          <rect x="36" y="23" width="14" height="6" rx="1" fill="none" stroke={color} strokeWidth="1.5" />
          <rect x="38" y="31" width="14" height="6" rx="1" fill="none" stroke={color} strokeWidth="1.5" />
          <rect x="40" y="39" width="12" height="6" rx="1" fill="none" stroke={color} strokeWidth="1.5" />
        </>
      )}
      {/* Sole tread — Gold+: short horizontal marks at heel and toe */}
      {hasTread && (
        <>
          <line x1="14" y1="68" x2="20" y2="68" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="14" y1="71" x2="20" y2="71" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="56" y1="66" x2="62" y2="66" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="54" y1="69" x2="60" y2="69" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {/* Midsole panel line — Platinum: divides upper from midsole */}
      {hasPanel && (
        <path d={PANEL} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      )}
    </svg>
  )
}
