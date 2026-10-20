export type StatusRow = {
  is_open?: boolean
  state?: string
}

export type QuoteRow = {
  symbol?: string
  ticker?: string
  name?: string
  close?: number
  change?: number
  change_abs?: number
  volume?: number
}

export type SparkRow = {
  ticker: string
  spark?: number[]
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) throw new Error('HTTP ' + String(res.status))
  return res.json()
}

export const getStatus = () => getJson<StatusRow>('/api/status')

export const getQuotes = (symbols: string) =>
  getJson<{ rows?: QuoteRow[] }>('/api/quotes?p=' + encodeURIComponent(symbols))

export const getSparks = (symbols: string[]) =>
  getJson<{ rows?: SparkRow[] }>(
    '/api/sparks?symbols=' + encodeURIComponent(symbols.join(','))
  )

export type Period = '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y'

export const PERIODS: Period[] = ['1mo', '3mo', '6mo', '1y', '2y', '5y']

export type HistoryRow = {
  Date: string
  Open: number
  High: number
  Low: number
  Close: number
  Volume: number
}

export type HistoryData = {
  symbol: string
  rows: HistoryRow[]
  quote: QuoteRow
  detail?: string
}

export const getHistory = (symbol: string, period: string) =>
  getJson<HistoryData>('/api/history/' + encodeURIComponent(symbol) + '?period=' + period)

export type SignalItem = {
  date?: string | null
  type?: string | null
  direction?: 'bullish' | 'bearish' | 'neutral' | null
  detail?: string | null
}

export type SignalsData = {
  symbol: string
  signals: SignalItem[]
  support?: number[] | null
  resistance?: number[] | null
  detail?: string | null
}

export type NewsSummary = {
  avg_compound?: number | null
  positive?: number | null
  negative?: number | null
  neutral?: number | null
  n?: number | null
  pos_pct?: number | null
  neg_pct?: number | null
}

export type Verdict = {
  label?: string | null
  emoji?: string | null
  score?: number | null
  reasons?: string[] | null
}

export type TechnicalSummary = {
  bull?: number | null
  bear?: number | null
  trend_label?: string | null
  rsi?: number | null
  last_close?: number | null
  score?: number | null
  signals?: SignalItem[] | null
}

export type AnalysisData = {
  symbol: string
  price?: number | null
  quote?: QuoteRow
  technical?: TechnicalSummary | null
  news?: NewsSummary | null
  verdict?: Verdict | null
}

export const getSignals = (symbol: string, period: string) =>
  getJson<SignalsData>('/api/signals/' + encodeURIComponent(symbol) + '?period=' + period)

export const getAnalysis = (symbol: string, pnl?: number) =>
  getJson<AnalysisData>('/api/analysis/' + encodeURIComponent(symbol) + (pnl === undefined ? '' : '?pnl=' + String(pnl)))

export type AlertRow = {
  id: number
  symbol: string
  kind: string
  target: number
  note: string
  active: number | null
  created_at: string | null
  triggered_at: string | null
  triggered_value: number | null
}

export type AlertsData = {
  active: AlertRow[]
  triggered: AlertRow[]
  kinds: string[]
}

export type AlertTrigger = {
  id: number
  symbol: string
  kind: string
  target: number
  value: number
  note: string
}

export type EvaluateData = {
  triggers: AlertTrigger[]
}

export const getAlerts = () => getJson<AlertsData>('/api/alerts')

export const evaluateAlerts = () => getJson<EvaluateData>('/api/alerts/evaluate')

export const addAlert = async (symbol: string, kind: string, target: number, note: string) => {
  const res = await fetch('/api/alerts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, kind, target, note }),
    cache: 'no-store',
  })
  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(data.detail || 'failed to create alert')
  }
}

export const deleteAlert = async (id: number) => {
  const res = await fetch('/api/alerts/' + id, { method: 'DELETE', cache: 'no-store' })
  if (!res.ok) throw new Error('failed to delete alert')
}

export type PositionRow = {
  id?: number
  Symbol?: string
  Qty?: number
  'Avg Cost'?: number
  Last?: number
  'Cost Basis'?: number
  Value?: number
  'P&L'?: number
  'P&L %'?: number
  'Day P&L'?: number
}

export type Totals = {
  total_value?: number
  total_cost?: number
  total_pnl?: number
  total_day_pnl?: number
}

export type PositionsData = {
  positions?: PositionRow[]
  totals?: Totals
}

export type RiskStops = {
  close?: number
  atr14?: number
  stop_1x?: number
  stop_2x?: number
  stop_3x?: number
  swing_low?: number
}

export type RiskData = {
  symbol?: string
  stops?: RiskStops | null
}

export type NewsRow = {
  title?: string
  published?: string
  source?: string
  url?: string
  origin?: string
  compound?: number | null
  tag?: string
}

export type NewsData = {
  symbol?: string
  summary?: NewsSummary | null
  rows?: NewsRow[]
}

export type MarketNewsRow = NewsRow & {
  dt?: string | null
}

export type MarketNewsData = {
  rows?: MarketNewsRow[]
}

export const getPositions = () => getJson<PositionsData>('/api/positions')

export const getRisk = (symbol: string) =>
  getJson<RiskData>('/api/risk/' + encodeURIComponent(symbol))

export const getNews = (symbol: string) =>
  getJson<NewsData>('/api/news/' + encodeURIComponent(symbol))

export const getMarketNews = () => getJson<MarketNewsData>('/api/market-news')

export const addPosition = async (symbol: string, qty: number, avgCost: number) => {
  const res = await fetch('/api/positions', {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, qty, avg_cost: avgCost }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'failed to add position')
  }
}

export const deletePosition = async (id: number) => {
  const res = await fetch('/api/positions/' + id, { method: 'DELETE', cache: 'no-store' })
  if (!res.ok) throw new Error('failed to delete position')
}

export type BtStrategy = 'sma_cross' | 'macd_cross' | 'rsi_reversion'

export type BacktestParams = {
  symbol: string
  strategy: BtStrategy
  period?: string
  fast?: number
  slow?: number
  initial?: number
  fee_pct?: number
  rsi_n?: number
  rsi_oversold?: number
  rsi_exit?: number
}

export type BtPoint = {
  date?: string
  value?: number
}

export type BtTrade = {
  entry_date?: string
  entry?: number
  exit_date?: string
  exit?: number
  pnl_pct?: number
}

export type BacktestData = {
  symbol?: string
  strategy?: string
  equity?: BtPoint[]
  buy_hold?: BtPoint[]
  trades?: BtTrade[]
  total_return?: number | null
  ann_return?: number | null
  max_drawdown?: number | null
  sharpe?: number | null
  n_trades?: number | null
  win_rate?: number | null
  avg_win?: number | null
  avg_loss?: number | null
  buy_hold_return?: number | null
  final_equity?: number | null
}

export const runBacktest = async (body: BacktestParams) => {
  const res = await fetch('/api/backtest', {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'backtest failed')
  }
  return (await res.json()) as BacktestData
}

export type MoverRow = {
  Logo?: string | null
  ticker: string
  name: string
  close: number
  change: number
  volume: number
}

export type MoversData = {
  rows?: MoverRow[]
}

export const getMovers = (name: string, limit = 10) => getJson<MoversData>('/api/movers?name=' + encodeURIComponent(name) + '&tab=' + encodeURIComponent('Top Movers') + '&limit=' + limit)

export type CustomSymbolsData = {
  symbols?: string[]
}

export type AddSymbolResult = {
  added?: boolean
  message?: string
}

export const getCustomSymbols = () => getJson<CustomSymbolsData>('/api/custom-symbols')

export const addCustomSymbol = async (symbol: string) => {
  const res = await fetch('/api/custom-symbols', {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(data.detail || 'failed to add symbol')
  }
  return (await res.json()) as AddSymbolResult
}

export const deleteCustomSymbol = async (symbol: string) => {
  const res = await fetch('/api/custom-symbols/' + encodeURIComponent(symbol), {
    method: 'DELETE',
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error('failed to delete symbol')
  }
}
