import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailyDistancePoint } from '../api/client'

interface Props {
  dailySeries: DailyDistancePoint[]
  goalKm: number
  showHighlight?: boolean
}

interface ChartPoint {
  day: number
  actual?: number
  pace: number
}

const MONTH_START_DAYS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function toDayOfYear(dateStr: string, year: number): number {
  const jan1 = new Date(year, 0, 1).getTime()
  const d = new Date(dateStr + 'T00:00:00').getTime()
  return Math.floor((d - jan1) / 86400000) + 1
}

function buildChartData(
  dailySeries: DailyDistancePoint[],
  goalKm: number,
): { data: ChartPoint[]; daysInYear: number; todayDayOfYear: number } {
  const year = new Date().getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365

  const today = new Date()
  const todayDayOfYear =
    Math.floor((today.getTime() - new Date(year, 0, 1).getTime()) / 86400000) + 1

  const paceAt = (day: number) => Math.round((day / daysInYear) * goalKm * 10) / 10

  const byDay = new Map<number, ChartPoint>()

  for (const day of [...MONTH_START_DAYS, daysInYear]) {
    byDay.set(day, { day, pace: paceAt(day) })
  }

  if (!byDay.has(todayDayOfYear)) {
    byDay.set(todayDayOfYear, { day: todayDayOfYear, pace: paceAt(todayDayOfYear) })
  }

  // Anchor the actual line at the origin so it always starts from (day 1, 0 km)
  const day1 = byDay.get(1) ?? { day: 1, pace: paceAt(1) }
  if (day1.actual === undefined) {
    byDay.set(1, { ...day1, actual: 0 })
  }

  for (const p of dailySeries) {
    const day = toDayOfYear(p.date, year)
    const existing = byDay.get(day)
    byDay.set(day, {
      day,
      actual: p.cumulative_km,
      pace: existing?.pace ?? paceAt(day),
    })
  }

  return {
    data: [...byDay.values()].sort((a, b) => a.day - b.day),
    daysInYear,
    todayDayOfYear,
  }
}

function monthTickFormatter(day: number): string {
  const idx = MONTH_START_DAYS.indexOf(day)
  return idx >= 0 ? MONTH_LABELS[idx] : ''
}

export default function PaceChart({ dailySeries, goalKm, showHighlight = true }: Props) {
  const { data, daysInYear } = buildChartData(dailySeries, goalKm)
  const style = getComputedStyle(document.documentElement)
  const accent   = style.getPropertyValue('--accent').trim()    || '#4b8cf7'
  const border   = style.getPropertyValue('--border').trim()    || '#272c3d'
  const text1    = style.getPropertyValue('--text-1').trim()    || '#e8eaf0'
  const text3    = style.getPropertyValue('--text-3').trim()    || '#3d4358'
  const surface2 = style.getPropertyValue('--surface-2').trim() || '#1c2030'

  const year = new Date().getFullYear()
  const lastActualDay = dailySeries.length > 0
    ? toDayOfYear(dailySeries[dailySeries.length - 1].date, year)
    : null

  const renderActualDot = (props: { cx: number; cy: number; payload: ChartPoint }) => {
    const { cx, cy, payload } = props
    if (!showHighlight || lastActualDay === null || payload.day !== lastActualDay) {
      return <circle r={0} cx={cx} cy={cy} fill="transparent" />
    }
    return (
      <g>
        <circle cx={cx} cy={cy} r={4} fill={accent} />
        <text
          x={cx + 8}
          y={cy + 4}
          textAnchor="start"
          fontSize={11}
          fontFamily="JetBrains Mono, monospace"
          fill={accent}
        >
          {payload.actual!.toFixed(1)} km
        </text>
      </g>
    )
  }

  const renderPaceDot = (props: { cx: number; cy: number; payload: ChartPoint }) => {
    const { cx, cy, payload } = props
    if (!showHighlight || lastActualDay === null || payload.day !== lastActualDay) {
      return <circle r={0} cx={cx} cy={cy} fill="transparent" />
    }
    return <circle cx={cx} cy={cy} r={3} fill={text3} />
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
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
          tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: text3 }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={(v: number) => String(v)}
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
            const km = typeof value === 'number' ? value : 0
            return [`${km.toFixed(1)} km`, name === 'actual' ? 'Distance' : 'Goal pace']
          }}
        />
        <Line
          dataKey="pace"
          stroke={text3}
          strokeDasharray="4 4"
          strokeWidth={1.5}
          dot={renderPaceDot as (props: unknown) => JSX.Element}
          connectNulls
        />
        <Line
          dataKey="actual"
          stroke={accent}
          strokeWidth={3}
          dot={renderActualDot as (props: unknown) => JSX.Element}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
