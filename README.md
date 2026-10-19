# 📈 EGX Stock Tracker

A personal trading dashboard for the **Egyptian Exchange (EGX)** — live prices, technical
analysis, signals, alerts, portfolio P&L, news sentiment and strategy backtesting in one place.

Built as a local web app with Python + Streamlit. Your data stays on your machine.

---

## ✨ Features

### 📊 Chart
- Interactive candlestick charts (Fri–Sat gaps hidden — EGX trades Sun–Thu)
- Volume, RSI(14) and MACD sub-charts; SMA 20/50/200, EMA 20, Bollinger Bands (incl. mid-line)
- Auto-detected **support/resistance levels** drawn on the chart (ATR projections when price is at highs)
- Watchlist table with **company logos**, **1-month sparkline trends**, color-coded changes and per-stock update times
- Live scrolling **ticker tape** under the header
- Market movers (top gainers / losers / by volume)

### 🎯 Signals & Levels
- Golden/death crosses (SMA20/50, SMA50/200), MACD crosses
- RSI overbought/oversold, volume spikes, near-52-week-high/low flags
- Bullish/bearish scorecard per stock
- Swing-pivot support & resistance with distance % from last price

### 🔔 Alerts
- Price above/below · day-change % · RSI14 thresholds
- Evaluated on every refresh — popup toast + sound beep the moment they trigger
- Trigger history log with one-click clear

### 💼 Portfolio
- Positions with live value, unrealized P&L and day P&L
- Cost bases calibrated to broker statements (fees included)
- **Position size calculator** (capital + risk% + entry + stop → exact share count)
- **ATR-based stop-loss suggestions** (1x/2x/3x ATR + swing low)
- 🔍 **Keep-or-sell analyzer**: verdict banner (🟢 KEEP / 🟡 HOLD / 🔴 REDUCE)
  combining technicals (55%), **company news sentiment** (45%) and your P&L context

### 🧪 Backtest
- Strategies: SMA crossover, MACD cross, RSI mean reversion (tunable params)
- Realistic simulation: next-bar-open execution + commission fees
- Metrics vs buy & hold: return, max drawdown, Sharpe, trades, win rate + equity curve
- Automatic warning when history looks split-unadjusted

### 📰 Market News
- EGX market feed aggregated from Google News + Daily News Egypt
- VADER sentiment score on every headline, positive/neutral/negative counters
- Text filter, clickable article links, manual refresh

### 🖥 Experience
- 🌙/☀️ **Dark & light modes** with an in-app switch (charts adapt automatically)
- **Ticker memory** — Chart, Signals and Backtest reopen on your last-viewed stock, even after browser reload
- **Price source switch** — Mubasher live feed with automatic per-symbol TradingView fallback
- **Search all ~230 live-price stocks** with logos; separate list of delayed-only names
- Market status badge (🟢 OPEN / 🟡 PRE-OPEN / 🔴 CLOSED) computed from real EGX hours (Sun–Thu 10:00–14:30 Cairo)
- Auto-refresh every 60s + manual refresh; custom dark/light design system (Sora + Inter)

---

## 🌐 Data sources (all free, no API keys)

| Source | Used for | Freshness |
|---|---|---|
| **Mubasher web API** | Live quotes, primary (232–235 stocks, per-stock trade timestamps) | Live feed |
| **TradingView scanner** | Fallback quotes, full universe (~291 stocks), logos, movers | ~15 min delayed |
| **Yahoo Finance** | Historical OHLCV charts, extra news | Daily + delayed |
| **Google News RSS + Daily News Egypt** | Headlines for sentiment + market news tab | Near real-time |

Resilience built in:
- Missing symbols automatically top up from TradingView per symbol
- Dead Yahoo series (flat zero-volume placeholders) are detected; the app searches
  Yahoo for the correct symbol and remembers the alias
- Scale-mismatch guard warns when history looks split-unadjusted vs the live price
- History cached in SQLite (`egx.db`); every run also records today's live candle,
  so charts gradually build even for names Yahoo doesn't cover

---

## 🚀 First-time setup

1. **Install Python 3.12+** (the `py` launcher comes with it)
   - During install tick *"Add python.exe to PATH"*

2. **Install dependencies** (one time only):
   ```
   cd "C:\Users\brigh\OneDrive\Documents\Default Project\egx-tracker"
   py -m pip install -r requirements.txt
   ```

3. **Run the app:**
   ```
   py -m streamlit run app.py
   ```
   Your browser opens at `http://localhost:8501`. Stop anytime with `Ctrl+C`.

Every later run is just step 3. Internet connection required.

> ⚠️ The folder lives inside OneDrive, which gives you free cloud backup of your
> portfolio database. In rare cases a sync mid-write can cause a
> "database is locked" error — just close and rerun.

---

## 🗂 Project structure

```
egx-tracker/
├── app.py               # Main dashboard UI (6 tabs)
├── egx.db               # SQLite: positions, alerts, custom symbols, history, settings, Yahoo aliases
├── requirements.txt
├── .streamlit/config.toml   # Dark/light theme definitions
├── data/
│   ├── fetcher.py       # Yahoo history + dead-series/alias/scale handling + cache
│   ├── live.py          # TradingView scanner (quotes, universe, logos)
│   ├── mubasher.py      # Mubasher live feed
│   ├── indicators.py    # SMA/EMA/RSI/MACD/Bollinger
│   ├── signals.py       # Signal detection + support/resistance (+ATR fallback)
│   ├── news.py          # Google News RSS + Yahoo news + DNE feed + VADER sentiment
│   ├── risk.py          # ATR, stops, position sizing
│   └── backtest.py      # Strategy backtester
├── analysis/advisor.py  # Keep-or-sell verdict engine
├── alerts/engine.py     # Alert evaluation
├── ui/charts.py         # Candlestick chart builder
└── storage/db.py        # SQLite layer
```

---

## ✅ Pros

- **100% free** — no subscriptions, no API keys
- **Private & portable** — all data in one local SQLite file (OneDrive-backed up)
- **Redundant data sources** with automatic per-symbol fallback
- Whole-exchange coverage: searchable universe with logos + sparkline trends
- Decision support that goes **beyond numbers** — technical signals, S/R levels,
  news sentiment and an explicit keep/hold/reduce verdict
- Backtesting built in — test an idea before risking money
- Verified end-to-end by an automated **68-check test suite** (UI flows + math + edge cases)

## ⚠️ Known limitations

- **Not true real-time** — EGX offers no free real-time feed; best available sources lag
  (~15 min). Compare freshness against your broker app during market hours.
- **~65 illiquid/suspended stocks** are missing from Mubasher's feed (auto-falls back to TradingView).
- **Thin history for some names** — micro-caps (KRDI, VLMRA) show live prices only; their
  charts build day-by-day from recorded candles. ORAS history depends on Yahoo's flaky
  ISIN-based symbol and may be partial.
- **Split-unadjusted Yahoo data** (e.g., HDBK pre-split) — the app warns when detected,
  but Yahoo-side adjustment is outside our control.
- **News sentiment is rule-based** — headline scoring (VADER), mostly English-language sources;
  it can miss context, Arabic-only stories, or material non-headline events.
- **Alerts run only while the app is open** — it's a local dashboard, not a server-side monitor.
- Backtests are simplified (no slippage modeling, long-only).
- Sound alerts use Windows system beeps; the app is primarily tested on Windows.

---

## 📜 Disclaimer

This tool is for **personal research and education**. Signals, sentiment scores and
verdicts are rule-based calculations — **not financial advice**. Always verify
important news yourself and do your own due diligence before trading.
