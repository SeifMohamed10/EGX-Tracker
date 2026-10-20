'use client'

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { getMarketNews, type MarketNewsData } from '@/lib/api'

const card: CSSProperties = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 8,
  padding: 14,
  marginBottom: 14,
}

const chip: CSSProperties = {
  display: 'inline-block',
  border: '1px solid var(--line)',
  borderRadius: 999,
  padding: '2px 8px',
  fontSize: 12,
  margin: '2px 4px 2px 0',
}

const fmtWhen = (dt: string | null | undefined): string => {
  if (!dt) return '—'
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return dt
  return d.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const fmtSent = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

const sentClass = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return 'muted'
  if (v > 0) return 'up'
  if (v < 0) return 'dn'
  return 'muted'
}

export default function NewsPage() {
  const [data, setData] = useState<MarketNewsData | null>(null)
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let done = false
    setBusy(true)
    setErr('')
    getMarketNews()
      .then((d) => {
        if (!done) return
        setData(d)
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
  }, [])

  const rows = data?.rows ?? []
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return rows
    return rows.filter((r) => (r.title ?? '').toLowerCase().includes(needle))
  }, [rows, q])

  const pos = filtered.filter((r) => r.tag === 'positive').length
  const neu = filtered.filter((r) => r.tag === 'neutral').length
  const neg = filtered.filter((r) => r.tag === 'negative').length

  return (
    <main>
      <h1>📰 Market News</h1>

      <p className="off">
        Aggregated from Google News (EGX queries) and Daily News Egypt. Headline
        sentiment scored automatically.
      </p>

      <p className="ctl">
        <label>
          Filter{' '}
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. COMI, dividend, EGX30..."
          />
        </label>
      </p>

      {err ? <p className="off">Error: {err}</p> : null}
      {busy ? <p>Loading news…</p> : null}

      <section style={card}>
        <p>
          <span style={chip}>Headlines {filtered.length}</span>
          <span style={chip}>🟢 Positive {pos}</span>
          <span style={chip}>⚪ Neutral {neu}</span>
          <span style={chip}>🔴 Negative {neg}</span>
        </p>

        {filtered.length ? (
          <table className="wt">
            <thead>
              <tr>
                <th>When</th>
                <th>Source</th>
                <th>Headline</th>
                <th>Sentiment</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={i}>
                  <td className="tk">{fmtWhen(r.dt)}</td>
                  <td>{r.source ?? '—'}</td>
                  <td className="nm">{r.title ?? '—'}</td>
                  <td className={sentClass(r.compound)}>{fmtSent(r.compound)}</td>
                  <td>
                    {r.url ? (
                      <a href={r.url} target="_blank" rel="noreferrer">
                        Open ↗
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}

        {!busy && !err && !filtered.length ? (
          <p className="off">No headlines match.</p>
        ) : null}
      </section>
    </main>
  )
}
