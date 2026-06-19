import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MemberProgress } from '../api/client'

interface Props {
  members: MemberProgress[]
  currentAthleteId: number
}

const MONTH_START_DAYS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Non-blue colors for other members (blue is reserved for current user via --accent)
const OTHER_COLORS = ['#3eb8a0', '#7c5cbf', '#d4884a', '#b85c7c', '#e05252']

function toDayOfYear(dateStr: string, year: number): number {
  const jan1 = new Date(year, 0, 1).getTime()
  const d = new Date(dateStr + 'T00:00:00').getTime()
  return Math.floor((d - jan1) / 86400000) + 1
}

function monthTickFormatter(day: number): string {
  const idx = MONTH_START_DAYS.indexOf(day)
  return idx >= 0 ? MONTH_LABELS[idx] : ''
}

interface PacePoint { day: number; pace: number }
interface MemberPoint { day: number; pct: number }

export default function ClubPaceChart({ members, currentAthleteId }: Props) {
  const year = new Date().getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365

  const style = getComputedStyle(document.documentElement)
  const accent   = style.getPropertyValue('--accent').trim()    || '#4b8cf7'
  const border   = style.getPropertyValue('--border').trim()    || '#272c3d'
  const text3    = style.getPropertyValue('--text-3').trim()    || '#3d4358'
  const text1    = style.getPropertyValue('--text-1').trim()    || '#e8eaf0'
  const surface2 = style.getPropertyValue('--surface-2').trim() || '#1c2030'

  const paceData: PacePoint[] = [
    ...MONTH_START_DAYS.map(day => ({
      day,
      pace: Math.round((day / daysInYear) * 100 * 10) / 10,
    })),
    { day: daysInYear, pace: 100 },
  ]

  // Pre-compute per-member chart data and color assignments
  const memberDataMap = new Map<number, MemberPoint[]>()
  const colorMap = new Map<number, string>()
  let otherIdx = 0
  for (const member of members) {
    memberDataMap.set(
      member.strava_athlete_id,
      member.daily_series.map(p => ({
        day: toDayOfYear(p.date, year),
        pct: Math.round((p.cumulative_km / member.goal_km) * 100 * 10) / 10,
      })),
    )
    if (member.strava_athlete_id === currentAthleteId) {
      colorMap.set(member.strava_athlete_id, accent)
    } else {
      colorMap.set(member.strava_athlete_id, OTHER_COLORS[otherIdx % OTHER_COLORS.length])
      otherIdx++
    }
  }

  const allPcts = Array.from(memberDataMap.values()).flatMap(pts => pts.map(p => p.pct))
  const maxPct = allPcts.length > 0 ? Math.max(...allPcts) : 0
  const yMax = Math.min(Math.ceil(Math.max(maxPct, 100) / 5) * 5, 125)

  // Custom dot: renders a filled circle + name label at the last data point of each member's series
  function renderEndLabel(athleteId: number, displayName: string, color: string) {
    const data = memberDataMap.get(athleteId) ?? []
    const lastDay = data.length > 0 ? data[data.length - 1].day : null
    return (props: { cx: number; cy: number; payload: MemberPoint }) => {
      const { cx, cy, payload } = props
      if (lastDay === null || payload.day !== lastDay) {
        return <circle r={0} cx={cx} cy={cy} fill="transparent" />
      }
      return (
        <g>
          <circle cx={cx} cy={cy} r={4} fill={color} />
          <text
            x={cx + 10}
            y={cy + 4}
            fontSize={11}
            fontFamily="JetBrains Mono, monospace"
            fill={color}
          >
            {displayName}
          </text>
        </g>
      )
    }
  }

  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart margin={{ top: 20, right: 90, bottom: 0, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={border} vertical={false} />
        <XAxis
          dataKey="day"
          type="number"
          domain={[1, daysInYear]}
          ticks={MONTH_START_DAYS}
          tickFormatter={monthTickFormatter}
          tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: text3 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          domain={[0, yMax]}
          tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: text3 }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={{
            background: surface2,
            border: `1px solid ${border}`,
            borderRadius: 8,
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
          }}
          labelFormatter={(label) => {
            const day = typeof label === 'number' ? label : 0
            const idx = MONTH_START_DAYS.findIndex(
              (d, i) => d <= day && (MONTH_START_DAYS[i + 1] ?? 366) > day,
            )
            return MONTH_LABELS[idx] ?? `Day ${day}`
          }}
          formatter={(value, name) => {
            const pct = typeof value === 'number' ? value : 0
            return [`${pct.toFixed(1)}%`, String(name)]
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: text1 }}
        />
        <Line
          data={paceData}
          dataKey="pace"
          name="Goal pace"
          stroke={text3}
          strokeDasharray="4 4"
          strokeWidth={1.5}
          dot={false}
          connectNulls
          legendType="plainline"
        />
        {members.map((member) => {
          const color = colorMap.get(member.strava_athlete_id) ?? accent
          const isCurrent = member.strava_athlete_id === currentAthleteId
          const label = isCurrent
            ? `${member.display_name} (you)`
            : member.display_name
          const memberData = memberDataMap.get(member.strava_athlete_id) ?? []
          return (
            <Line
              key={member.strava_athlete_id}
              data={memberData}
              dataKey="pct"
              name={label}
              stroke={color}
              strokeWidth={isCurrent ? 3 : 2}
              dot={
                renderEndLabel(member.strava_athlete_id, member.display_name, color) as (
                  props: unknown,
                ) => JSX.Element
              }
              connectNulls
              legendType="plainline"
            />
          )
        })}
      </LineChart>
    </ResponsiveContainer>
  )
}
