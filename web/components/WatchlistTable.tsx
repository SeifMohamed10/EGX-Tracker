'use client'

import type { QuoteRow } from '@/lib/api'

function fmtVol(v?: number) {
  if (v == null || !Number.isFinite(v) || v === 0) return '-'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(1) + 'K'
  return String(v)
}

function Spark({ data }: { data?: number[] }) {
  if (!data || data.length < 2) return null
  const w = 90
  const h = 24
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w
      const y = h - ((v - min) / span) * (h - 2) - 1
      return x.toFixed(1) + ',' + y.toFixed(1)
    })
    .join(' ')
  const up = data[data.length - 1] >= data[0]
  return (
    <svg className="spark" width={w} height={h} viewBox={'0 0 ' + w + ' ' + h}>
      <polyline
        points={pts}
        fill="none"
        stroke={up ? 'var(--green)' : 'var(--red)'}
        strokeWidth="1.5"
      />
    </svg>
  )
}

export default function WatchlistTable({
  rows,
  sparks,
}: {
  rows: QuoteRow[]
  sparks: Record<string, number[]>
}) {
  return (
    <table className="wt">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Name</th>
          <th>Last</th>
          <th>Chg %</th>
          <th>Volume</th>
          <th>Spark</th>
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={6} className="muted">
              Waiting for quotes…
            </td>
          </tr>
        ) : (
          rows.map((r) => {
            const key = (r.ticker ?? r.symbol ?? '').replace('EGX:', '')
            const c = r.change ?? 0
            return (
              <tr key={key}>
                <td className="tk">{key}</td>
                <td className="nm">{r.name ?? ''}</td>
                <td>{r.close != null ? r.close.toFixed(2) : '-'}</td>
                <td className={c > 0 ? 'up' : c < 0 ? 'dn' : 'muted'}>
                  {r.change != null ? c.toFixed(2) + '%' : '-'}
                </td>
                <td className="muted">{fmtVol(r.volume)}</td>
                <td>
                  <Spark data={sparks[key]} />
                </td>
              </tr>
            )
          })
        )}
      </tbody>
    </table>
  )
}
