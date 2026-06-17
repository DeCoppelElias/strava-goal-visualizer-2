import BadgeIcon from './BadgeIcon'

type Tier = 'bronze' | 'silver' | 'gold' | 'platinum'

interface BadgeSpec {
  tier: Tier
  name: string
  threshold: number
  color: string
  label: string
}

const BADGES: BadgeSpec[] = [
  { tier: 'bronze',   name: 'First Steps', threshold: 10,   color: '#9c6b3c', label: '10 km'    },
  { tier: 'silver',   name: 'Century',     threshold: 100,  color: '#8b91a8', label: '100 km'   },
  { tier: 'gold',     name: 'One a Day',   threshold: 365,  color: '#b8922a', label: '365 km'   },
  { tier: 'platinum', name: 'Thousand',    threshold: 1000, color: '#9ab0c8', label: '1,000 km' },
]

const UNEARNED = 'var(--badge-locked)'

interface Props {
  distanceKm: number
}

export default function BadgeRow({ distanceKm }: Props) {
  return (
    <div className="header-badges">
      {BADGES.map((b) => {
        const earned = distanceKm >= b.threshold
        const label = `${b.name} — ${b.label} (${earned ? 'earned' : 'locked'})`
        return (
          <span
            key={b.tier}
            className="header-badges__item"
            tabIndex={0}
            aria-label={label}
          >
            <BadgeIcon tier={b.tier} color={earned ? b.color : UNEARNED} width={60} height={72} />
            <span className="header-badges__tooltip" role="tooltip">
              {label}
            </span>
          </span>
        )
      })}
    </div>
  )
}
