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

const UNEARNED = '#3d4358'

interface Props {
  distanceKm: number
}

export default function BadgeRow({ distanceKm }: Props) {
  return (
    <div className="card">
      <div className="card__header">
        <span className="card__label">Badges</span>
      </div>
      <div className="card__body">
        <div className="badge-row">
          {BADGES.map((b) => {
            const earned = distanceKm >= b.threshold
            return (
              <div key={b.tier} className="badge-item">
                <BadgeIcon tier={b.tier} color={earned ? b.color : UNEARNED} />
                <span className={`badge-item__name${earned ? '' : ' badge-item__name--unearned'}`}>
                  {b.name}
                </span>
                <span className="badge-item__threshold">{b.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
