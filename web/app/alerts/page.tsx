'use client'

import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { addAlert, deleteAlert, evaluateAlerts, getAlerts, getQuotes, type AlertsData, type AlertRow } from '@/lib/api'

const WATCH = ['COMI', 'HRHO', 'ABUK', 'TMGH', 'SWDY', 'EAST', 'ETEL', 'AMOC']

const KIND_LABELS: Record<string, string> = {
  price_above: 'Price rises above',
  price_below: 'Price falls below',
  pct_above: 'Day change above %',
  pct_below: 'Day change below %',
  rsi_above: 'RSI14 above',
  rsi_below: 'RSI14 below'
}

const card: CSSProperties = { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 8, padding: 14, marginBottom: 14 }
const chip: CSSProperties = { display: 'inline-block', border: '1px solid var(--line)', borderRadius: 999, padding: '2px 8px', fontSize: 12, margin: '2px 4px 2px 0' }
const muted: CSSProperties = { color: 'var(--muted)', fontSize: 12 }
const cell: CSSProperties = { padding: '4px 8px', borderBottom: '1px solid var(--line)' }

type QuoteLite = { close: number | null, change: number | null }

const kindLabel = (kind: string) => KIND_LABELS[kind] ?? kind

const defaultTarget = (sym: string, map: Record<string, QuoteLite>) => {
  const q = map[sym]
  if (q && q.close !== null) return String(q.close)
  return '100'
}

const currentTxt = (row: AlertRow, map: Record<string, QuoteLite>) => {
  if (row.kind.startsWith('rsi')) return '-'
  const q = map[row.symbol]
  if (!q) return '-'
  const val = row.kind.startsWith('pct') ? q.change : q.close
  if (val === null) return '-'
  return `now ${String(val)}`
}

export default function AlertsPage() {
  const [data, setData] = useState<AlertsData | null>(null)
  const [quotes, setQuotes] = useState<Record<string, QuoteLite>>({})
  const [busy, setBusy] = useState(true)
  const [err, setErr] = useState('')
  const [symbol, setSymbol] = useState(WATCH[0])
  const [kind, setKind] = useState('price_above')
  const [target, setTarget] = useState('100')
  const [note, setNote] = useState('')
  const symbolRef = useRef(WATCH[0])

  const load = useCallback(async () => {
    try {
      const body = await getAlerts()
      setData(body)
      setErr('')
    } catch {
      setErr('backend unavailable')
    }
  }, [])

  useEffect(() => {
    let done = false
    setBusy(true)
    setErr('')
    evaluateAlerts()
      .catch(() => undefined)
      .then(() => Promise.all([getAlerts(), getQuotes(WATCH.join(','))]))
      .then((res) => {
        if (!done) return
        const [alerts, quoteRes] = res
        setData(alerts)
        const map: Record<string, QuoteLite> = {}
        for (const q of quoteRes.rows ?? []) {
          const key = q.ticker || q.symbol || ''
          if (!key) continue
          map[key] = {
            close: Number.isFinite(q.close) ? Number(q.close) : null,
            change: Number.isFinite(q.change) ? Number(q.change) : null
          }
        }
        setQuotes(map)
        setTarget(defaultTarget(symbolRef.current, map))
      })
      .catch(() => {
        if (!done) return
        setErr('backend unavailable')
      })
      .finally(() => {
        if (done) return
        setBusy(false)
      })
    return () => {
      done = true
    }
  }, [])

  const pickSymbol = (sym: string) => {
    symbolRef.current = sym
    setSymbol(sym)
    setTarget(defaultTarget(sym, quotes))
  }

  const handleSubmit = async (ev: FormEvent<HTMLFormElement>) => {
    ev.preventDefault()
    setErr('')
    const rs = symbol.trim().toUpperCase()
    const rt = target.trim()
    if (!rs || !rt) {
      setErr('symbol and target are required')
      return
    }
    const tn = parseFloat(rt)
    if (!Number.isFinite(tn) || tn <= 0) {
      setErr('target must be > 0')
      return
    }
    try {
      await addAlert(rs, kind, tn, note.trim())
      pickSymbol(WATCH[0])
      setKind('price_above')
      setNote('')
      await load()
    } catch (ex) {
      setErr(String((ex as Error).message ?? ex))
    }
  }

  const remove = async (id: number) => {
    try {
      await deleteAlert(id)
      await load()
    } catch (ex) {
      setErr(String((ex as Error).message ?? ex))
    }
  }

  const clearTriggered = async () => {
    try {
      for (const row of data?.triggered ?? []) {
        await deleteAlert(row.id)
      }
      await load()
    } catch (ex) {
      setErr(String((ex as Error).message ?? ex))
    }
  }

  const active = data?.active ?? []
  const triggered = (data?.triggered ?? []).slice(0, 20)

  return (
    <main>
      <h1>Alerts</h1>
      {busy ? <p style={muted}>Loading alerts...</p> : null}
      {err ? <p style={muted}>{err}</p> : null}

      <section style={card}>
        <h2>⏰ Create alert</h2>
        <span style={chip}>checked on every refresh</span>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>Symbol</div>
            <select value={symbol} onChange={(e) => pickSymbol(e.target.value)}>
              {WATCH.map((sym) => (
                <option key={sym} value={sym}>
                  {sym}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>Condition</div>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {Object.entries(KIND_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>Target</div>
            <input type="number" step="0.01" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>Note</div>
            <input type="text" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <button type="submit">Add alert</button>
        </form>
      </section>

      <section style={card}>
        <h2>📡 Active alerts</h2>
        {active.length === 0 ? (
          <p style={muted}>No active alerts.</p>
        ) : (
          active.map((row) => (
            <div key={row.id} style={{ marginBottom: 10 }}>
              <div>
                <b>{row.symbol}</b> - {kindLabel(row.kind)} <b>{String(row.target)}</b> ({currentTxt(row, quotes)})
                <button style={{ marginLeft: 8 }} onClick={() => remove(row.id)}>
                  🗑
                </button>
              </div>
              <div style={muted}>{row.note ? row.note : ' '}</div>
            </div>
          ))
        )}
      </section>

      <section style={card}>
        <h2>🕘 Triggered history</h2>
        {triggered.length === 0 ? (
          <p style={muted}>Nothing triggered yet.</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th style={cell}>Symbol</th>
                  <th style={cell}>Kind</th>
                  <th style={cell}>Target</th>
                  <th style={cell}>Triggered value</th>
                  <th style={cell}>Triggered at</th>
                </tr>
              </thead>
              <tbody>
                {triggered.map((row) => (
                  <tr key={row.id}>
                    <td style={cell}>{row.symbol}</td>
                    <td style={cell}>{kindLabel(row.kind)}</td>
                    <td style={cell}>{String(row.target)}</td>
                    <td style={cell}>{row.triggered_value === null ? '-' : String(row.triggered_value)}</td>
                    <td style={cell}>{row.triggered_at ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button style={{ marginTop: 8 }} onClick={() => clearTriggered()}>
              🧹 Clear triggered history
            </button>
          </>
        )}
      </section>
    </main>
  )
}
