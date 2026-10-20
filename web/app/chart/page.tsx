'use client'

import { useEffect, useState } from 'react'
import { getHistory, PERIODS, type HistoryData, type Period } from '@/lib/api'
import ChartCandles from '@/components/ChartCandles'

const WATCH = ['COMI', 'HRHO', 'ABUK', 'TMGH', 'SWDY', 'EAST', 'ETEL', 'AMOC']

export default function Page() {
  const [symbol, setSymbol] = useState('COMI')
  const [typed, setTyped] = useState('COMI')
  const [period, setPeriod] = useState<Period>('1y')
  const [ma20, setMa20] = useState(true)
  const [ma50, setMa50] = useState(false)
  const [tick, setTick] = useState(0)
  const [data, setData] = useState<HistoryData | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let done = false
    const s = symbol.replace(/^EGX:/, '')
    getHistory(s, period)
      .then((d) => {
        if (done) return
        if (!d.rows || d.rows.length === 0) {
          setErr(`no history for ${s}`)
          setData(null)
          return
        }
        setData(d)
        setErr('')
      })
      .catch((e: unknown) => {
        if (done) return
        setErr(e instanceof Error ? e.message : 'fetch failed')
        setData(null)
      })
    return () => {
      done = true
    }
  }, [symbol, period, tick])

  const q = data?.quote
  const close = q?.close ?? (data?.rows.length ? data.rows[data.rows.length - 1].Close : null)
  const chg = q?.change ?? null
  const up = (chg ?? 0) >= 0
  const bars = data ? `${data.symbol} · ${period} · ${data.rows.length} bars` : ''

  const go = (v: string) => {
    const s = v.trim().replace(/^EGX:/, '')
    if (s) setSymbol(s)
  }
  const opts = WATCH.includes(symbol) ? WATCH : [symbol, ...WATCH]

  return (
    <div className="wrap">
      <h1>Chart</h1>
      <div className="ch-bar">
        <select
          value={symbol}
          onChange={(e) => {
            setTyped(e.target.value)
            setSymbol(e.target.value)
          }}
        >
          {opts.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') go(typed)
          }}
          placeholder="ticker"
        />
        <select value={period} onChange={(e) => setPeriod(e.target.value as Period)}>
          {PERIODS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <label className="ch-lab">
          <input type="checkbox" checked={ma20} onChange={(e) => setMa20(e.target.checked)} /> MA20
        </label>
        <label className="ch-lab">
          <input type="checkbox" checked={ma50} onChange={(e) => setMa50(e.target.checked)} /> MA50
        </label>
        <button type="button" onClick={() => setTick(tick + 1)}>
          Refresh
        </button>
        {close != null ? (
          <span className={`ch-quote ${up ? 'up' : 'dn'}`}>
            {close.toFixed(2)}
            {chg != null ? ` ${up ? '+' : ''}${chg.toFixed(2)}%` : ''}
          </span>
        ) : null}
      </div>
      <div className="ch-meta">{bars}</div>
      {err ? <p className="off">{err}</p> : null}
      {data ? <ChartCandles rows={data.rows} ma20={ma20} ma50={ma50} /> : null}
      <style>{`
.ch-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.ch-bar select, .ch-bar input, .ch-bar button { background: var(--panel); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 5px 9px; font-size: 13px; }
.ch-bar button { cursor: pointer; }
.ch-lab { color: var(--muted); font-size: 12px; display: inline-flex; gap: 5px; align-items: center; }
.ch-quote { margin-left: auto; font-weight: 600; }
.ch-meta { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
`}</style>
    </div>
  )
}
