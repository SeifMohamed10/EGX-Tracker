'use client'

import { useEffect, useState, type CSSProperties } from 'react'
import { getMovers, type MoverRow } from '@/lib/api'

const segWrap: CSSProperties = {
  display: 'inline-flex',
  gap: 4,
  marginBottom: 14,
}

const segBtn = (active: boolean): CSSProperties => ({
  border: '1px solid var(--line)',
  background: active ? 'var(--panel)' : 'transparent',
  color: active ? 'var(--text)' : 'var(--muted)',
  cursor: 'pointer',
  fontSize: 13,
  padding: '4px 10px',
  borderRadius: 6,
  fontFamily: 'inherit',
})

const fmtVol = (v: number | null) => {
  if (v == null || !Number.isFinite(v) || v === 0) return '—'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(1) + 'K'
  return String(v)
}

const chgLabel = (v: number) => (v >= 0 ? '▲ +' + v.toFixed(2) + '%' : '▼ ' + v.toFixed(2) + '%')

const chgClass = (v: number) => (v > 0 ? 'up' : v < 0 ? 'dn' : 'muted')

export default function MoversPage() {
  const [name, setName] = useState('Gainers')
  const [rows, setRows] = useState<MoverRow[]>([])
  const [busy, setBusy] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let done = false
    setBusy(true)
    setErr('')
    getMovers(name, 10)
      .then((d) => {
        if (!done) return
        setRows(d.rows ?? [])
      })
      .catch((e) => {
        if (!done) return
        setErr(String(e.message ?? e))
      })
      .finally(() => {
        if (!done) return
        setBusy(false)
      })
    return () => {
      done = true
    }
  }, [name])

  return (
    <main>
      <h1>🏆 Market Movers</h1>
      <p className="off">Top 10 by {name.toLowerCase()}</p>
      <p style={segWrap}>
        {['Gainers', 'Losers', 'Volume'].map((n) => (
          <button key={n} style={segBtn(name === n)} onClick={() => setName(n)}>
            {n}
          </button>
        ))}
      </p>
      {err ? <p className="off">Error: {err}</p> : null}
      {busy ? <p>Loading …</p> : null}
      <table className="wt">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Name</th>
            <th>Last</th>
            <th>Chg %</th>
            <th>Volume</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.ticker}>
              <td className="tk">{r.ticker}</td>
              <td className="nm">{r.name.slice(0, 28)}</td>
              <td>{r.close.toFixed(2)}</td>
              <td className={chgClass(r.change)}>{chgLabel(r.change)}</td>
              <td>{fmtVol(r.volume)}</td>
            </tr>
          ))}
          {rows.length === 0 && !busy ? (
            <tr>
              <td colSpan={5} className="muted">
                Waiting for quotes…
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </main>
  )
}
