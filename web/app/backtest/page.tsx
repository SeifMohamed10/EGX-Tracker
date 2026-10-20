'use client'

import { useState, type CSSProperties } from 'react'
import { runBacktest, type BacktestData, type BtPoint, type BtStrategy } from '@/lib/api'

const wrap: CSSProperties = { maxWidth: 900, margin: '0 auto' }

const card: CSSProperties = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 8,
  padding: 14,
  marginBottom: 14,
}

const muted: CSSProperties = { color: 'var(--muted)', fontSize: 12 }

const cell: CSSProperties = {
  padding: '4px 8px',
  borderBottom: '1px solid var(--line)',
}

const GRID: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 12,
  marginBottom: 14,
}

const stat: CSSProperties = {
  border: '1px solid var(--line)',
  borderRadius: 8,
  padding: '8px 12px',
}

const INPUT: CSSProperties = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '6px 8px',
  fontSize: 14,
  color: 'var(--fg)',
}

const GOOD = 'rgba(46, 204, 113, 1)'
const BAD = 'rgba(231, 76, 60, 1)'
const WARN = 'rgba(243, 156, 18, 1)'

const num = (s: string, fallback: number) => {
  const v = Number(s)
  return Number.isFinite(v) ? v : fallback
}

const money2 = (v: number | null | undefined) =>
  v == null ? 'N/A' : v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtPct = (v: number | null | undefined) =>
  v == null ? 'N/A' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`

const fmtSigned = (v: number | null | undefined) =>
  v == null ? '-' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}`

const fmtEq = (v: number | null | undefined) =>
  v == null ? 'N/A' : Math.round(v).toLocaleString('en-US')

type WithValue = BtPoint & { value: number }

const withValue = (p: BtPoint): p is WithValue => p.value != null

const SYMBOLS = ['COMI', 'HRHO', 'ABUK', 'TMGH', 'SWDY', 'EAST', 'ETEL', 'AMOC']

const STRATEGIES: Array<{ value: BtStrategy; label: string }> = [
  { value: 'sma_cross', label: 'SMA Crossover' },
  { value: 'macd_cross', label: 'MACD Cross' },
  { value: 'rsi_reversion', label: 'RSI Mean Reversion' },
]

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('COMI')
  const [strategy, setStrategy] = useState<BtStrategy>('sma_cross')
  const [initial, setInitial] = useState('100000')
  const [fee, setFee] = useState('0.15')
  const [fast, setFast] = useState('20')
  const [slow, setSlow] = useState('50')
  const [rsiN, setRsiN] = useState('14')
  const [rsiOs, setRsiOs] = useState('30')
  const [rsiExit, setRsiExit] = useState('60')
  const [data, setData] = useState<BacktestData | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await runBacktest({
        symbol,
        strategy,
        period: '1y',
        initial: num(initial, 100000),
        fee_pct: num(fee, 0.15),
        ...(strategy === 'sma_cross'
          ? { fast: num(fast, 20), slow: num(slow, 50) }
          : {}),
        ...(strategy === 'rsi_reversion'
          ? {
              rsi_n: num(rsiN, 14),
              rsi_oversold: num(rsiOs, 30),
              rsi_exit: num(rsiExit, 60),
            }
          : {}),
      })
      setData(res)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : String(ex))
    } finally {
      setBusy(false)
    }
  }

  const stratPts = data?.equity?.filter(withValue) ?? []
  const holdPts = data?.buy_hold?.filter(withValue) ?? []

  const beat =
    data?.total_return != null && data?.buy_hold_return != null
      ? data.total_return - data.buy_hold_return
      : null

  const chartMin = Math.min(...stratPts.map((p) => p.value), ...holdPts.map((p) => p.value))
  const chartMax = Math.max(...stratPts.map((p) => p.value), ...holdPts.map((p) => p.value))
  const span = chartMax - chartMin || 1
  const px = (i: number, n: number) => 40 + (n <= 1 ? 470 : (i * 940) / (n - 1))
  const py = (v: number) => 30 + (1 - (v - chartMin) / span) * 360

  const stratPoints = stratPts
    .map((p, i) => `${px(i, stratPts.length).toFixed(1)},${py(p.value).toFixed(1)}`)
    .join(' ')
  const holdPoints = holdPts
    .map((p, i) => `${px(i, holdPts.length).toFixed(1)},${py(p.value).toFixed(1)}`)
    .join(' ')

  const inputStyle = (extra?: CSSProperties): CSSProperties => ({ ...INPUT, width: '100%', ...extra })

  const ctl: CSSProperties = { display: 'flex', flexDirection: 'column', gap: 4, minWidth: 120 }

  return (
    <div style={wrap}>
      <h1>🧪 Backtest</h1>

      <div style={card}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <div style={ctl}>
            <span style={muted}>Ticker</span>
            <select
              style={inputStyle()}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            >
              {SYMBOLS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div style={ctl}>
            <span style={muted}>Strategy</span>
            <select
              style={inputStyle()}
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as BtStrategy)}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div style={ctl}>
            <span style={muted}>Initial capital (EGP)</span>
            <input
              style={inputStyle()}
              type="number"
              min={1000}
              step={10000}
              value={initial}
              onChange={(e) => setInitial(e.target.value)}
            />
          </div>
          <div style={ctl}>
            <span style={muted}>Fees per side (%)</span>
            <input
              style={inputStyle()}
              type="number"
              min={0}
              step={0.05}
              value={fee}
              onChange={(e) => setFee(e.target.value)}
            />
          </div>
          {strategy === 'sma_cross' && (
            <>
              <div style={ctl}>
                <span style={muted}>Fast SMA</span>
                <input
                  style={inputStyle()}
                  type="number"
                  min={5}
                  max={60}
                  value={fast}
                  onChange={(e) => setFast(e.target.value)}
                />
              </div>
              <div style={ctl}>
                <span style={muted}>Slow SMA</span>
                <input
                  style={inputStyle()}
                  type="number"
                  min={10}
                  max={250}
                  value={slow}
                  onChange={(e) => setSlow(e.target.value)}
                />
              </div>
            </>
          )}
          {strategy === 'rsi_reversion' && (
            <>
              <div style={ctl}>
                <span style={muted}>RSI period</span>
                <input
                  style={inputStyle()}
                  type="number"
                  min={5}
                  max={30}
                  value={rsiN}
                  onChange={(e) => setRsiN(e.target.value)}
                />
              </div>
              <div style={ctl}>
                <span style={muted}>Entry when RSI &lt;</span>
                <input
                  style={inputStyle()}
                  type="number"
                  min={15}
                  max={45}
                  value={rsiOs}
                  onChange={(e) => setRsiOs(e.target.value)}
                />
              </div>
              <div style={ctl}>
                <span style={muted}>Exit when RSI &gt;</span>
                <input
                  style={inputStyle()}
                  type="number"
                  min={40}
                  max={90}
                  value={rsiExit}
                  onChange={(e) => setRsiExit(e.target.value)}
                />
              </div>
            </>
          )}
        </div>
        {strategy === 'sma_cross' && num(fast, 20) >= num(slow, 50) && (
          <div style={{ ...muted, color: WARN, marginTop: 8 }}>
            Fast SMA should be below slow SMA.
          </div>
        )}
        <div style={{ marginTop: 10 }}>
          <button
            style={{
              background: 'var(--panel)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              padding: '8px 14px',
              fontSize: 14,
              color: 'var(--fg)',
              cursor: busy ? 'wait' : 'pointer',
              opacity: busy ? 0.6 : 1,
            }}
            disabled={busy}
            onClick={run}
          >
            ▶ Run backtest
          </button>
        </div>
        {error && <div style={{ color: BAD, marginTop: 8 }}>{error}</div>}
      </div>

      {data && stratPts.length < 60 && (
        <div style={card}>
          <div style={muted}>Not enough history for a meaningful backtest.</div>
        </div>
      )}

      {data && stratPts.length >= 60 && (
        <>
          <div style={GRID}>
            <div style={stat}>
              <div style={muted}>Strategy return</div>
              <div>{fmtPct(data.total_return)}</div>
              {beat != null && (
                <div style={{ color: beat >= 0 ? GOOD : BAD, fontSize: 12 }}>
                  {fmtPct(beat)} vs buy &amp; hold
                </div>
              )}
            </div>
            <div style={stat}>
              <div style={muted}>Buy &amp; hold</div>
              <div>{fmtPct(data.buy_hold_return)}</div>
            </div>
            <div style={stat}>
              <div style={muted}>Max drawdown</div>
              <div>{fmtPct(data.max_drawdown)}</div>
            </div>
            <div style={stat}>
              <div style={muted}>Sharpe</div>
              <div>{data.sharpe != null ? data.sharpe.toFixed(2) : 'N/A'}</div>
            </div>
            <div style={stat}>
              <div style={muted}>Trades</div>
              <div>
                {data.n_trades ?? 0} (win{' '}
                {data.win_rate != null ? `${data.win_rate.toFixed(0)}%` : 'N/A'})
              </div>
            </div>
          </div>

          <div style={card}>
            <svg viewBox="0 0 1000 420" style={{ width: '100%', height: 'auto' }} role="img">
              {[0, 1, 2, 3, 4].map((i) => {
                const y = 30 + i * 90
                const v = chartMax - (i / 4) * span
                return (
                  <g key={i}>
                    <line x1={40} x2={980} y1={y} y2={y} stroke="var(--line)" />
                    <text x={36} y={y + 4} fontSize={11} textAnchor="end" fill="var(--muted)">
                      {money2(v)}
                    </text>
                  </g>
                )
              })}
              {holdPoints && (
                <polyline
                  points={holdPoints}
                  fill="none"
                  stroke="#888888"
                  strokeWidth={1.4}
                  strokeDasharray="4 3"
                />
              )}
              {stratPoints && (
                <polyline points={stratPoints} fill="none" stroke="#26a69a" strokeWidth={2} />
              )}
              <line x1={700} x2={730} y1={14} y2={14} stroke="#26a69a" strokeWidth={2} />
              <text x={738} y={18} fontSize={12} fill="var(--muted)">
                Strategy
              </text>
              <line x1={820} x2={850} y1={14} y2={14} stroke="#888888" strokeWidth={1.4} strokeDasharray="4 3" />
              <text x={858} y={18} fontSize={12} fill="var(--muted)">
                Buy &amp; Hold
              </text>
            </svg>
          </div>

          <div style={card}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['entry_date', 'Entry', 'exit_date', 'Exit', 'P&L %'].map((h) => (
                    <th key={h} style={{ ...cell, textAlign: 'left', color: 'var(--muted)', fontWeight: 400 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data.trades ?? []).map((t, i) => (
                  <tr key={i}>
                    <td style={cell}>{t.entry_date ?? '-'}</td>
                    <td style={cell}>{money2(t.entry)}</td>
                    <td style={cell}>{t.exit_date ?? '-'}</td>
                    <td style={cell}>{money2(t.exit)}</td>
                    <td style={cell}>{fmtSigned(t.pnl_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(data.trades?.length ?? 0) > 0 ? (
              <div style={{ ...muted, marginTop: 8 }}>
                Avg winner {fmtSigned(data.avg_win)}% - avg loser {fmtSigned(data.avg_loss)}% - final
                equity {fmtEq(data.final_equity)} EGP
              </div>
            ) : (
              <div style={{ ...muted, marginTop: 8 }}>
                Strategy produced no round trips in this period.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
