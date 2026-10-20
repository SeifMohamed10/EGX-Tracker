type Row = { Date: string; Open: number; High: number; Low: number; Close: number; Volume: number }

function movingAvg(values: number[], n: number): (number | null)[] {
  const out: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= n) sum -= values[i - n]
    out.push(i >= n - 1 ? sum / n : null)
  }
  return out
}

export default function ChartCandles({ rows, ma20, ma50 }: { rows: Row[]; ma20: boolean; ma50: boolean }) {
  if (rows.length === 0) return <div className="muted">no history rows</div>

  const W = 960
  const H = 430
  const padL = 58
  const padR = 14
  const padT = 14
  const padB = 26
  const priceH = 300
  const volTop = padT + priceH + 14
  const volH = H - volTop - padB

  let lo = Math.min(...rows.map((r) => r.Low))
  let hi = Math.max(...rows.map((r) => r.High))
  const padY = (hi - lo) * 0.03 || 0.5
  lo -= padY
  hi += padY

  const n = rows.length
  const step = (W - padL - padR) / n
  const bw = Math.max(1.5, Math.min(11, step * 0.62))
  const cx = (i: number) => padL + (i + 0.5) * step
  const py = (p: number) => padT + ((hi - p) / (hi - lo)) * priceH

  let vmax = 0
  for (const r of rows) if (r.Volume > vmax) vmax = r.Volume
  const den = vmax || 1
  const vy = (v: number) => volTop + volH - (v / den) * volH

  const s20 = ma20 && n > 20 ? movingAvg(rows.map((r) => r.Close), 20) : null
  const s50 = ma50 && n > 50 ? movingAvg(rows.map((r) => r.Close), 50) : null

  const maLine = (serie: (number | null)[] | null, color: string) => {
    if (!serie) return null
    const pts: string[] = []
    for (let i = 0; i < serie.length; i++) {
      const v = serie[i]
      if (v != null) pts.push(`${cx(i).toFixed(1)},${py(v).toFixed(1)}`)
    }
    return pts.length < 2 ? null : <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth={1.4} />
  }

  const candle = (r: Row, i: number) => {
    const green = r.Close >= r.Open
    const color = green ? 'var(--green)' : 'var(--red)'
    const x = cx(i)
    const top = py(Math.max(r.Open, r.Close))
    const body = Math.max(1, Math.abs(py(r.Open) - py(r.Close)))
    return (
      <g key={r.Date} stroke={color} fill={color}>
        <line x1={x} y1={py(r.High)} x2={x} y2={py(r.Low)} strokeWidth={1} />
        <rect x={x - bw / 2} y={top} width={bw} height={body} strokeWidth={0} />
      </g>
    )
  }

  const volBar = (r: Row, i: number) => {
    const green = r.Close >= r.Open
    const y = vy(r.Volume)
    return (
      <rect key={`v${i}`} x={cx(i) - bw / 2} y={y} width={bw} height={Math.max(1, volTop + volH - y)} fill={green ? 'var(--green)' : 'var(--red)'} opacity={0.4} />
    )
  }

  const idxs = [...new Set(Array.from({ length: 6 }, (_, i) => Math.round((i * (n - 1)) / 5)))]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      <rect x={0} y={0} width={W} height={H} fill="none" stroke="var(--line)" />
      {Array.from({ length: 6 }, (_, i) => {
        const p = lo + ((hi - lo) * i) / 5
        const y = py(p)
        return (
          <g key={`t${i}`}>
            <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="var(--line)" />
            <text x={padL - 6} y={y + 3} textAnchor="end" fontSize={10} fill="var(--muted)">{p.toFixed(2)}</text>
          </g>
        )
      })}
      {rows.map((r, i) => candle(r, i))}
      {rows.map((r, i) => volBar(r, i))}
      {maLine(s20, 'var(--amber)')}
      {maLine(s50, '#4aa3ff')}
      {idxs.map((i) => (
        <text key={`d${i}`} x={cx(i)} y={H - 8} textAnchor="middle" fontSize={10} fill="var(--muted)">{rows[i].Date}</text>
      ))}
    </svg>
  )
}
