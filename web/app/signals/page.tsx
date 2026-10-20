'use client'

import { useEffect, useState, type CSSProperties } from 'react'
import { PERIODS, getAnalysis, getSignals, type AnalysisData, type Period, type SignalsData } from '@/lib/api'

const WATCH = ['COMI', 'HRHO', 'ABUK', 'TMGH', 'SWDY', 'EAST', 'ETEL', 'AMOC']

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

const fmt = (v: number | null | undefined, dec = 2): string => {
  if (v === null || v === undefined) return '—'
  if (Number.isNaN(v)) return '—'
  return v.toFixed(dec)
}

const dirClass = (direction: string | null | undefined): string => {
  if (direction === 'bullish') return 'up'
  if (direction === 'bearish') return 'dn'
  return 'muted'
}

export default function SignalsPage() {
  const [symbol, setSymbol] = useState('COMI')
  const [period, setPeriod] = useState<Period>('1y')
  const [sig, setSig] = useState<SignalsData | null>(null)
  const [ana, setAna] = useState<AnalysisData | null>(null)
  const [busy, setBusy] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let done = false
    setBusy(true)
    setErr('')
    Promise.all([getSignals(symbol, period), getAnalysis(symbol)])
      .then(([s, a]) => {
        if (!done) return
        setSig(s)
        setAna(a)
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
  }, [symbol, period])

  const opts = WATCH.includes(symbol) ? WATCH : [symbol, ...WATCH]
  const verdict = ana?.verdict ?? null
  const tech = ana?.technical ?? null
  const news = ana?.news ?? null
  const reasons = verdict?.reasons ?? []
  const sigs = sig?.signals ?? []

  return (
    <main>
      <h1>Signals</h1>

      <p className="ctl">
        <label>
          Symbol{' '}
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {opts.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>{' '}
        <label>
          Period{' '}
          <select value={period} onChange={(e) => setPeriod(e.target.value as Period)}>
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </p>

      {err ? <p className="off">Error: {err}</p> : null}
      {busy ? <p>Loading {symbol}…</p> : null}

      <section style={card}>
        <h2>Verdict</h2>
        {verdict ? (
          <>
            <p className="h2">
              {verdict.emoji} {verdict.label} · score {fmt(verdict.score)}
            </p>
            <ul>
              {reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
            <p>
              Price {fmt(ana?.price)} · last close {fmt(tech?.last_close)}
            </p>
          </>
        ) : (
          <p>No verdict data for this symbol.</p>
        )}
      </section>

      <section style={card}>
        <h2>Technical</h2>
        <p>
          Trend: {tech?.trend_label ?? '—'} · score {fmt(tech?.score)}
        </p>
        <p>
          <span className="up">Bulls {fmt(tech?.bull)}</span> · <span className="dn">Bears {fmt(tech?.bear)}</span> ·{' '}
          RSI {fmt(tech?.rsi, 1)}
        </p>
      </section>

      <section style={card}>
        <h2>News</h2>
        {news && news.n ? (
          <p>
            Avg sentiment {fmt(news.avg_compound)} · {news.positive ?? 0} positive / {news.negative ?? 0} negative /{' '}
            {news.neutral ?? 0} neutral (n = {news.n})
          </p>
        ) : (
          <p>No news data for this symbol.</p>
        )}
      </section>

      <section style={card}>
        <h2>Levels</h2>
        <p>
          Support:{' '}
          {(sig?.support ?? []).length ? (
            (sig?.support ?? []).map((v, i) => (
              <span key={i} style={chip} className="up">
                {fmt(v)}
              </span>
            ))
          ) : (
            <span className="muted">none</span>
          )}
        </p>
        <p>
          Resistance:{' '}
          {(sig?.resistance ?? []).length ? (
            (sig?.resistance ?? []).map((v, i) => (
              <span key={i} style={chip} className="dn">
                {fmt(v)}
              </span>
            ))
          ) : (
            <span className="muted">none</span>
          )}
        </p>
      </section>

      <section style={card}>
        <h2>Detections ({sigs.length})</h2>
        {sigs.length ? (
          <table className="wt">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {sigs.map((s, i) => (
                <tr key={i}>
                  <td className="tk">{s.date ?? '—'}</td>
                  <td className={dirClass(s.direction)}>{s.type ?? '—'}</td>
                  <td className="nm">{s.detail ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No signals detected in this period.</p>
        )}
      </section>
    </main>
  )
}
