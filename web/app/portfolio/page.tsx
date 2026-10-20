'use client'

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import {
  addPosition,
  deletePosition,
  getAnalysis,
  getNews,
  getPositions,
  getRisk,
  type AnalysisData,
  type NewsData,
  type PositionsData,
  type RiskData,
} from '@/lib/api'

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

const muted: CSSProperties = { color: 'var(--muted)', fontSize: 12 }

const cell: CSSProperties = { padding: '4px 8px', borderBottom: '1px solid var(--line)' }

const GRID: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 12,
}

const INPUT: CSSProperties = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '6px 8px',
  fontSize: 14,
}

const GOOD = 'rgba(46, 204, 113, 1)'
const BAD = 'rgba(231, 76, 60, 1)'

const money = (v: number) => Math.round(v).toLocaleString('en-US')
const money2 = (v: number) =>
  v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const spct = (v: number) => (v >= 0 ? '+' : '') + v.toFixed(2)
const smoney = (v: number) => (v >= 0 ? '+' : '') + Math.round(v).toLocaleString('en-US')
const dist = (v: number) => (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
const pct = (v: number) => (v >= 0 ? '+' : '') + v.toFixed(2) + '%'

export default function PortfolioPage() {
  const [sel, setSel] = useState('')
  const [data, setData] = useState<PositionsData | undefined>()
  const [err, setErr] = useState('')
  const [cap, setCap] = useState('100000')
  const [rpct, setRpct] = useState('2')
  const [entry, setEntry] = useState('')
  const [stop, setStop] = useState('95')
  const [a, setA] = useState<AnalysisData | undefined>()
  const [aErr, setAErr] = useState('')
  const [nd, setNd] = useState<NewsData | undefined>()
  const [rsk, setRsk] = useState<RiskData | undefined>()
  const [nsym, setNsym] = useState('')
  const [nqty, setNqty] = useState('')
  const [navg, setNavg] = useState('')
  const [busy, setBusy] = useState(false)
  const [delBusy, setDelBusy] = useState(false)

  const rows = useMemo(() => data?.positions ?? [], [data])
  const totals = data?.totals ?? {}
  const row = useMemo(() => rows.find((r) => r.Symbol === sel), [rows, sel])
  const rowQty = useMemo(
    () => rows.filter((r) => r.Symbol === sel).reduce((s, r) => s + (r.Qty ?? 0), 0),
    [rows, sel],
  )
  const rowAvg = useMemo(() => {
    const rs = rows.filter((r) => r.Symbol === sel)
    const q = rs.reduce((s, r) => s + (r.Qty ?? 0), 0)
    if (q <= 0) return 0
    return rs.reduce((s, r) => s + (r.Qty ?? 0) * (r['Avg Cost'] ?? 0), 0) / q
  }, [rows, sel])
  const rowPctVal = row?.['P&L %']
  const symbols = useMemo(
    () => Array.from(new Set(rows.map((r) => r.Symbol).filter(Boolean))) as string[],
    [rows],
  )

  const vLabel = a?.verdict?.label ?? ''
  const vEmoji = a?.verdict?.emoji ?? ''
  const vScore = typeof a?.verdict?.score === 'number' ? a.verdict.score : null
  const bannerBg = vLabel.includes('KEEP')
    ? 'rgba(46, 204, 113, 0.15)'
    : vLabel.includes('REDUCING') || vLabel.includes('EXITING')
      ? 'rgba(231, 76, 60, 0.15)'
      : 'rgba(241, 196, 15, 0.15)'
  const bannerText = vLabel
    ? `${vEmoji ? vEmoji + ' ' : ''}${vLabel} - score ${spct(vScore ?? 0)}`
    : ''

  const capV = Number(cap)
  const rpctV = Number(rpct)
  const entryV = Number(entry)
  const stopV = Number(stop)
  const perShare = Math.abs(entryV - stopV)
  const rkValid = capV > 0 && rpctV > 0 && entryV > 0 && perShare > 0
  const rkShares = rkValid ? Math.floor((capV * rpctV) / 100 / perShare) : 0
  const rkCost = rkShares * entryV
  const rkActual = rkShares * perShare
  const rkCash = rkValid ? (rkCost / capV) * 100 : 0

  const stops = rsk?.stops
  const stopRows = useMemo(() => {
    if (!stops || !stops.close) return [] as Array<[string, number, number]>
    const close = stops.close
    const items: Array<[string, number | undefined]> = [
      ['Stop (1x ATR)', stops.stop_1x],
      ['Stop (2x ATR)', stops.stop_2x],
      ['Stop (3x ATR)', stops.stop_3x],
      ['Swing low', stops.swing_low],
    ]
    return items
      .filter((x): x is [string, number] => typeof x[1] === 'number')
      .map(([label, price]): [string, number, number] => [label, price, (price / close - 1) * 100])
  }, [stops])

  useEffect(() => {
    getPositions()
      .then((d) => setData(d))
      .catch((ex) => setErr(String((ex as Error).message ?? ex)))
  }, [])

  useEffect(() => {
    if (!sel && rows.length && rows[0].Symbol) setSel(rows[0].Symbol)
  }, [sel, rows])

  useEffect(() => {
    if (!sel) return
    let ok = true
    setA(undefined)
    setAErr('')
    setNd(undefined)
    setRsk(undefined)
    const rs = data?.positions ?? []
    const r = rs.find((x) => x.Symbol === sel)
    const pv = typeof r?.['P&L %'] === 'number' ? (r['P&L %'] as number) : undefined
    Promise.all([getAnalysis(sel, pv), getNews(sel), getRisk(sel)])
      .then(([aa, nn, rr]) => {
        if (ok) {
          setA(aa)
          setNd(nn)
          setRsk(rr)
        }
      })
      .catch((ex) => {
        if (ok) setAErr(String((ex as Error).message ?? ex))
      })
    return () => {
      ok = false
    }
  }, [sel, data])

  useEffect(() => {
    const p = typeof a?.price === 'number' ? a.price : a?.quote?.close
    if (entry === '' && typeof p === 'number') setEntry(String(p))
  }, [a, entry])

  const submitPos = async () => {
    const q = Number(nqty)
    const c = Number(navg)
    if (!nsym.trim() || !Number.isFinite(q) || q <= 0 || !Number.isFinite(c) || c <= 0) return
    setBusy(true)
    setErr('')
    try {
      await addPosition(nsym.trim(), q, c)
      setNsym('')
      setNqty('')
      setNavg('')
      setData(await getPositions())
    } catch (ex) {
      setErr(String((ex as Error).message ?? ex))
    } finally {
      setBusy(false)
    }
  }

  const del = async (id?: number) => {
    if (!id) return
    setDelBusy(true)
    setErr('')
    try {
      await deletePosition(id)
      setData(await getPositions())
    } catch (ex) {
      setErr(String((ex as Error).message ?? ex))
    } finally {
      setDelBusy(false)
    }
  }

  return (
    <main>
      <h1>Portfolio & risk</h1>
      {err ? <p style={{ color: BAD, fontSize: 14 }}>{err}</p> : null}

      <section style={card}>
        <div style={GRID}>
          <div>
            <div style={muted}>Total value</div>
            <div style={{ fontSize: 20 }}>{money(totals.total_value ?? 0)} EGP</div>
          </div>
          <div>
            <div style={muted}>Total invested</div>
            <div style={{ fontSize: 20 }}>{money(totals.total_cost ?? 0)} EGP</div>
          </div>
          <div>
            <div style={muted}>Unrealized P&L</div>
            <div style={{ fontSize: 20, color: (totals.total_pnl ?? 0) >= 0 ? GOOD : BAD }}>
              {smoney(totals.total_pnl ?? 0)} EGP
            </div>
          </div>
          <div>
            <div style={muted}>Day P&L</div>
            <div style={{ fontSize: 20 }}>{money(totals.total_day_pnl ?? 0)} EGP</div>
          </div>
        </div>
      </section>

      <section style={card}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr>
              {['Symbol', 'Qty', 'Avg Cost', 'Last', 'Cost Basis', 'Value', 'P&L', 'P&L %', 'Day P&L', 'Del?'].map(
                (h) => (
                  <th key={h} style={{ ...cell, textAlign: 'left' }}>
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={r.id ?? r.Symbol ?? i}
                onClick={() => {
                  if (r.Symbol) setSel(r.Symbol)
                }}
                style={{
                  background: r.Symbol === sel ? 'rgba(128, 128, 128, 0.08)' : undefined,
                  cursor: 'pointer',
                }}
              >
                <td style={cell}>{r.Symbol}</td>
                <td style={cell}>{typeof r.Qty === 'number' ? r.Qty.toLocaleString('en-US') : ''}</td>
                <td style={cell}>{typeof r['Avg Cost'] === 'number' ? money2(r['Avg Cost']) : ''}</td>
                <td style={cell}>{typeof r.Last === 'number' ? money2(r.Last) : ''}</td>
                <td style={cell}>{typeof r['Cost Basis'] === 'number' ? money(r['Cost Basis']) : ''}</td>
                <td style={cell}>{typeof r.Value === 'number' ? money(r.Value) : ''}</td>
                <td style={{ ...cell, color: (r['P&L'] ?? 0) >= 0 ? GOOD : BAD }}>
                  {typeof r['P&L'] === 'number' ? smoney(r['P&L']) : ''}
                </td>
                <td style={cell}>{typeof r['P&L %'] === 'number' ? spct(r['P&L %']) : ''}</td>
                <td style={{ ...cell, color: (r['Day P&L'] ?? 0) >= 0 ? GOOD : BAD }}>
                  {typeof r['Day P&L'] === 'number' ? smoney(r['Day P&L']) : ''}
                </td>
                <td style={cell}>
                  <button
                    type="button"
                    disabled={delBusy}
                    onClick={(e) => {
                      e.stopPropagation()
                      void del(r.id)
                    }}
                    style={INPUT}
                  >
                    x
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 ? <p style={muted}>No positions yet.</p> : null}
      </section>

      <section style={card}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            placeholder="Symbol"
            value={nsym}
            onChange={(e) => setNsym(e.target.value)}
            style={{ ...INPUT, width: 120 }}
          />
          <input
            placeholder="Quantity"
            value={nqty}
            onChange={(e) => setNqty(e.target.value)}
            inputMode="decimal"
            style={{ ...INPUT, width: 100 }}
          />
          <input
            placeholder="Avg cost"
            value={navg}
            onChange={(e) => setNavg(e.target.value)}
            inputMode="decimal"
            style={{ ...INPUT, width: 120 }}
          />
          <button type="button" disabled={busy} onClick={() => void submitPos()}>
            Add position
          </button>
        </div>
      </section>

      <section style={card}>
        <h2>🛡 Risk tools</h2>
        <div style={{ ...GRID, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Position size calculator</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <label>
                <span style={muted}>Capital (EGP)</span>
                <input value={cap} onChange={(e) => setCap(e.target.value)} inputMode="decimal" style={{ ...INPUT, width: '100%' }} />
              </label>
              <label>
                <span style={muted}>Risk per trade (%)</span>
                <input value={rpct} onChange={(e) => setRpct(e.target.value)} inputMode="decimal" style={{ ...INPUT, width: '100%' }} />
              </label>
              <label>
                <span style={muted}>Entry price</span>
                <input value={entry} onChange={(e) => setEntry(e.target.value)} inputMode="decimal" style={{ ...INPUT, width: '100%' }} />
              </label>
              <label>
                <span style={muted}>Stop loss</span>
                <input value={stop} onChange={(e) => setStop(e.target.value)} inputMode="decimal" style={{ ...INPUT, width: '100%' }} />
              </label>
            </div>
            {rkValid ? (
              <div style={{ marginTop: 8, fontSize: 14 }}>
                <div>
                  Shares: <b>{rkShares.toLocaleString('en-US')}</b>
                </div>
                <div>
                  Position cost: <b>{money(rkCost)}</b>
                </div>
                <div>
                  Cash used: <b>{pct(rkCash)}</b>
                </div>
                <p style={muted}>
                  Risking {rpctV}% = {money((capV * rpctV) / 100)} EGP - actual risk {money(rkActual)} EGP ({money2(perShare)}/share)
                </p>
              </div>
            ) : (
              <p style={muted}>Invalid inputs (stop must differ from entry).</p>
            )}
          </div>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Stop suggestions</div>
            {rsk === undefined ? (
              <p style={muted}>Loading...</p>
            ) : !stops || !stops.close ? (
              <p style={muted}>Not enough history for stops.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr>
                    <th style={{ ...cell, textAlign: 'left' }}>Stop level</th>
                    <th style={{ ...cell, textAlign: 'left' }}>Price</th>
                    <th style={{ ...cell, textAlign: 'left' }}>Distance</th>
                  </tr>
                </thead>
                <tbody>
                  {stopRows.map(([label, v, pct]) => (
                    <tr key={label}>
                      <td style={cell}>{label}</td>
                      <td style={cell}>{money2(v)}</td>
                      <td style={cell}>{dist(pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      <section style={card}>
        <h2>🔍 Keep or sell - position analyzer</h2>
        {symbols.length === 0 ? (
          <p style={muted}>Add a position above first, then analyze it here.</p>
        ) : (
          <>
            <div style={{ marginBottom: 10 }}>
              <select value={sel} onChange={(e) => setSel(e.target.value)} style={INPUT}>
                {symbols.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            {aErr ? <p style={{ color: BAD, fontSize: 14 }}>{aErr}</p> : null}
            {!a && !aErr ? <p style={muted}>Loading analysis...</p> : null}
            {a && bannerText ? (
              <div style={{ background: bannerBg, borderRadius: 8, padding: 10, marginBottom: 10 }}>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{bannerText}</div>
              </div>
            ) : null}
            {a ? (
              <>
                <div style={{ ...GRID, marginBottom: 10 }}>
                  <div>
                    <div style={muted}>Last price</div>
                    <div>{typeof a.price === 'number' ? money2(a.price) : ''}</div>
                  </div>
                  <div>
                    <div style={muted}>Avg cost</div>
                    <div>{money2(rowAvg)}</div>
                  </div>
                  <div>
                    <div style={muted}>Unrealized P&L</div>
                    <div style={{ color: (rowPctVal ?? 0) >= 0 ? GOOD : BAD }}>
                      {typeof rowPctVal === 'number' ? pct(rowPctVal) : ''}
                    </div>
                  </div>
                  <div>
                    <div style={muted}>Total qty</div>
                    <div>{rowQty.toLocaleString('en-US')}</div>
                  </div>
                </div>
                <div style={{ ...GRID, marginBottom: 10 }}>
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>Technical view</div>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14 }}>
                      <li>
                        {a.technical?.bull ?? 0} bullish / {a.technical?.bear ?? 0} bearish signals
                      </li>
                      <li>Trend: {a.technical?.trend_label ?? ''}</li>
                      <li>RSI14: {typeof a.technical?.rsi === 'number' ? a.technical.rsi.toFixed(0) : ''}</li>
                      {(a.technical?.signals ?? []).map((s, j) => (
                        <li key={j}>
                          <span
                            style={{
                              display: 'inline-block',
                              width: 8,
                              height: 8,
                              borderRadius: 999,
                              background:
                                s.direction === 'bullish' ? GOOD : s.direction === 'bearish' ? BAD : '#9aa0a6',
                              marginRight: 6,
                            }}
                          />
                          {s.date ?? ''}: {s.type ?? ''}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>
                      News sentiment
                      {typeof nd?.summary?.n === 'number' ? ` (${nd.summary.n} headlines)` : ''}
                    </div>
                    {(nd?.rows ?? []).length === 0 ? (
                      <p style={muted}>No recent headlines found for this company.</p>
                    ) : (
                      <div>
                        {(nd?.rows ?? []).slice(0, 8).map((r, j) => (
                          <span key={j} style={chip}>
                            {r.title}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                {(a.verdict?.reasons ?? []).length > 0 ? (
                  <div
                    style={{
                      background: 'rgba(52, 152, 219, 0.08)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: 10,
                      marginBottom: 10,
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Why this verdict:</div>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14 }}>
                      {(a.verdict?.reasons ?? []).map((r, j) => (
                        <li key={j}>{r}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <p style={muted}>
                  Rule-based analysis of technicals + headline sentiment. News may lag or miss context - always
                  verify important news yourself. Not financial advice.
                </p>
              </>
            ) : null}
          </>
        )}
      </section>
    </main>
  )
}
