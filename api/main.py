import math
import os
import time
from datetime import date, datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import Body, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from alerts import engine
from analysis import advisor
from data import backtest, live, news, risk, signals
from data.fetcher import fetch_history
from data.tickers import DEFAULT_WATCHLIST, EGX_TICKERS
from storage import db

app = FastAPI(title="EGX Tracker API", version="1.0.0")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CACHE: dict[str, tuple[float, Any]] = {}

DEFAULT_QUOTE_SYMBOLS = list(dict.fromkeys(DEFAULT_WATCHLIST + db.list_custom_symbols()))

MOVER_FIELDS = {
    "Gainers": ("change", False),
    "Losers": ("change", True),
    "Volume": ("volume", False),
}

TOTALS_EMPTY = {
    "total_value": 0.0,
    "total_cost": 0.0,
    "total_pnl": 0.0,
    "total_day_pnl": 0.0,
}


def _cached(key: str, ttl: int, fn):
    now = time.time()
    hit = _CACHE.get(key)
    if hit is not None and now - hit[0] < ttl:
        return hit[1]
    value = fn()
    _CACHE[key] = (now, value)
    return value


def _clean(obj):
    if obj is None or isinstance(obj, bool) or isinstance(obj, str):
        return obj
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, (pd.Timestamp, datetime)):
        if isinstance(obj, pd.Timestamp):
            if pd.isna(obj):
                return "NaT"
            return obj.isoformat(sep=" ")
        return obj.isoformat(sep=" ")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, pd.DataFrame):
        rows = obj.where(pd.notna(obj), None).to_dict("records")
        return [_clean(rec) for rec in rows]
    if isinstance(obj, (pd.Series, pd.Index)):
        return [_clean(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, np.ndarray)):
        return [_clean(v) for v in list(obj)]
    return str(obj)


def _market_status():
    now = pd.Timestamp.now(tz="Africa/Cairo")
    wd = int(now.weekday())
    minutes = int(now.hour) * 60 + int(now.minute)
    trading_day = wd in (6, 0, 1, 2, 3)
    pre_open = trading_day and 540 <= minutes < 600
    is_open = trading_day and 600 <= minutes < 870
    if is_open:
        state = "🟢 MARKET OPEN"
    elif pre_open:
        state = "🟡 PRE-OPEN"
    else:
        next_day = "Sunday" if wd in (3, 4, 5) else ("tomorrow" if trading_day else "Sunday")
        state = f"🔴 CLOSED · opens {next_day} 10:00"
    return {"is_open": bool(is_open), "state": state}


def _symbol_name(sym: str, universe_desc: dict):
    return EGX_TICKERS.get(sym) or (universe_desc.get(sym) or "")


def _default_syms():
    return list(dict.fromkeys(list(DEFAULT_WATCHLIST) + db.list_custom_symbols()))


def _live_quotes(syms):
    df = live.get_quotes(syms)
    if not df.empty:
        priced = pd.Series(dtype=bool)
        close = df.get("close")
        if close is not None:
            priced = close.apply(lambda v: isinstance(v, (int, float)) and not pd.isna(v))
        got = set()
        if priced.any() and "ticker" in df.columns:
            got = set(df.loc[priced, "ticker"].dropna())
        missing = [s for s in syms if s not in got]
        if missing:
            extra = live.get_quotes(missing)
            if not extra.empty:
                df = pd.concat([df, extra], ignore_index=True) if not df.empty else extra
    return df


def _quotes_df(symbols):
    syms = [s for s in dict.fromkeys(symbols) if s]
    if not syms:
        return pd.DataFrame()
    key = "quotes:" + ",".join(sorted(syms))
    return _cached(key, 45, lambda: _live_quotes(syms))


def _quote_row_map(qdf):
    by_ticker = {}
    if qdf is None or qdf.empty or "ticker" not in qdf.columns:
        return by_ticker
    for _, row in qdf.iterrows():
        tk = str(row.get("ticker", "")).upper()
        by_ticker[tk] = row
    return by_ticker


def _quote_row(qdf, sym):
    if qdf is None or qdf.empty:
        return None
    match = qdf[qdf["ticker"].astype(str).str.upper() == sym]
    if match.empty:
        return None
    return _clean(match.iloc[0].to_dict())


def _get_price_history(symbol: str, period: str = "1y", name_hint: str | None = None):
    return _cached(
        "hist:" + symbol + ":" + period + ":" + str(name_hint or ""),
        1800,
        lambda: fetch_history(symbol, period=period, name_hint=name_hint or None),
    )


def _universe_pack():
    def _compute():
        uni = live.get_all_symbols()
        desc = dict(zip(uni["ticker"], uni["description"].fillna("")))
        logos = {}
        for _, r in uni.iterrows():
            t = r.get("ticker", "")
            try:
                logos[t] = live.logo_url(r.get("logoid"))
            except Exception:
                logos[t] = None
        return {"desc": desc, "logos": logos}

    return _cached("universe", 86400, _compute)


def _get_news(symbol: str, name: str = ""):
    if name is None:
        name = ""
    return _cached("news:" + symbol, 900, lambda: news.collect_news(symbol, name))


def _news_summary(ndf):
    if ndf is None or ndf.empty:
        return None
    return news.summarize_news(ndf)


def _sparks_vals(syms):
    if not syms:
        return {}
    out = {}
    try:
        raw = yf.download(
            [f"{s}.CA" for s in syms],
            period="1mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            group_by="ticker",
        )
        if raw is None or raw.empty:
            return {}
        top = raw.columns.get_level_values(0) if isinstance(raw.columns, pd.MultiIndex) else None
        for s in syms:
            key = f"{s}.CA"
            try:
                if top is not None and key not in top:
                    continue
                block = raw[key]["Close"] if top is not None else raw.get("Close")
                if block is None:
                    continue
                vals = [float(v) for v in block.dropna().tail(22).tolist()]
                if vals:
                    out[s] = vals
            except Exception:
                continue
    except Exception:
        return {}
    return out


@app.get("/")
def root():
    return {
        "status": "ok",
        "name": "EGX Tracker API",
        "version": "1.0.0",
        "endpoints": [
            "/api/status",
            "/api/quotes",
            "/api/history/{symbol}",
            "/api/analysis/{symbol}",
            "/api/signals/{symbol}",
            "/api/news/{symbol}",
            "/api/sparks",
            "/api/universe",
            "/api/custom-symbols",
            "/api/custom-symbols/{symbol}",
            "/api/market-news",
            "/api/movers",
            "/api/alerts",
            "/api/alerts/evaluate",
            "/api/positions",
            "/api/backtest",
            "/api/risk/{symbol}",
        ],
    }


@app.get("/api/status")
def api_status():
    return _market_status()


@app.get("/api/quotes")
def api_quotes(request: Request):
    params = request.query_params
    p = params.get("p")
    if p is not None and p.strip():
        symbols = [s.strip().upper() for s in p.split(",") if s.strip()]
    else:
        symbols = _default_syms()
    qdf = _quotes_df(symbols)
    return {"rows": _clean(qdf), "status": _market_status()}


@app.get("/api/history/{symbol}")
def api_history(symbol: str, request: Request):
    params = request.query_params
    period = params.get("period", "1y")
    sym = symbol.strip().upper()
    hist = _get_price_history(sym, period, _symbol_name(sym, _universe_pack()["desc"]))
    if hist is None or hist.empty:
        raise HTTPException(status_code=404, detail="no history")
    out = hist.reset_index()
    first = out.columns[0]
    out = out.rename(columns={first: "Date"})
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    qdf = _quotes_df([sym])
    quote = _quote_row(qdf, sym)
    return {"symbol": sym, "rows": _clean(out), "quote": quote}


class AlertCreate(BaseModel):
    symbol: str
    kind: str
    target: float
    note: str = ""


@app.get("/api/alerts")
def api_alerts():
    df = db.list_alerts()
    if df.empty:
        return {"active": [], "triggered": [], "kinds": list(db.ALERT_KINDS)}
    active = df[df["triggered_at"].isna() & (df["active"] == 1)]
    triggered = df[df["triggered_at"].notna()]
    return {"active": _clean(active), "triggered": _clean(triggered), "kinds": list(db.ALERT_KINDS)}


@app.post("/api/alerts", status_code=200)
def api_add_alert(payload: AlertCreate):
    sym = payload.symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")
    if payload.kind not in db.ALERT_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {list(db.ALERT_KINDS)}")
    if payload.target <= 0:
        raise HTTPException(status_code=400, detail="target must be > 0")
    db.add_alert(sym, payload.kind, float(payload.target), payload.note)
    return {"ok": True}


@app.delete("/api/alerts/{alert_id}")
def api_delete_alert(alert_id: int):
    db.delete_alert(int(alert_id))
    return {"ok": True}


@app.get("/api/alerts/evaluate")
def api_alerts_evaluate():
    alerts = db.list_alerts(active_only=True)
    alert_syms = [str(v).strip().upper() for v in alerts["symbol"].tolist()] if not alerts.empty else []
    symbols = list(dict.fromkeys(_default_syms() + alert_syms))
    qdf = _quotes_df(symbols)

    def hist_get(qsym: str):
        desc = _universe_pack()["desc"]
        return _get_price_history(qsym, "6mo", _symbol_name(qsym, desc))

    triggers = engine.evaluate(alerts, qdf, hist_get)
    return {"triggers": _clean(triggers)}


class PositionCreate(BaseModel):
    symbol: str
    qty: float
    avg_cost: float


@app.get("/api/positions")
def api_positions():
    pos = db.list_positions()
    if pos is None or pos.empty:
        return {"rows": [], "totals": TOTALS_EMPTY}
    syms = list(dict.fromkeys([str(v).strip().upper() for v in pos["symbol"].tolist() if str(v).strip()]))
    qdf = _quotes_df(syms) if syms else pd.DataFrame()
    quote_map = _quote_row_map(qdf)
    desc = _universe_pack()["desc"]
    rows = []
    total_cost = 0.0
    total_value = 0.0
    total_day_pnl = 0.0
    for _, p in pos.iterrows():
        sym = str(p["symbol"]).strip().upper()
        qty = float(p["qty"])
        avg = float(p["avg_cost"])
        price = None
        day_change = None
        if sym in quote_map:
            qrow = quote_map[sym]
            try:
                close_raw = qrow.get("close", None)
                if close_raw is not None and pd.notna(close_raw):
                    price = float(close_raw)
            except Exception:
                price = None
            try:
                ch = qrow.get("change_abs", None)
                if ch is not None and pd.notna(ch):
                    day_change = float(ch)
            except Exception:
                day_change = None
        if price is None:
            hist = _get_price_history(sym, "6mo", _symbol_name(sym, desc))
            if hist is not None and not hist.empty:
                px = hist["Close"].iloc[-1]
                if px is not None and pd.notna(px):
                    price = float(px)
        if price is None:
            price = avg
        if day_change is None:
            day_change = 0.0
        cost = qty * avg
        value = qty * price
        pnl = value - cost
        pnl_pct = (pnl / cost * 100.0) if cost != 0.0 else 0.0
        day_pnl = qty * day_change
        rows.append(
            {
                "id": int(p["id"]),
                "Symbol": sym,
                "Qty": qty,
                "Avg Cost": avg,
                "Last": price,
                "Cost Basis": cost,
                "Value": value,
                "P&L": pnl,
                "P&L %": pnl_pct,
                "Day P&L": day_pnl,
            }
        )
        total_cost += cost
        total_value += value
        total_day_pnl += day_pnl
    totals = {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_value - total_cost,
        "total_day_pnl": total_day_pnl,
    }
    return {"rows": _clean(rows), "totals": _clean(totals)}


@app.post("/api/positions", status_code=200)
def api_add_position(payload: PositionCreate):
    sym = payload.symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")
    db.add_position(sym, float(payload.qty), float(payload.avg_cost))
    return {"ok": True}


@app.delete("/api/positions/{position_id}")
def api_delete_position(position_id: int):
    db.delete_position(int(position_id))
    return {"ok": True}


@app.get("/api/analysis/{symbol}")
def api_analysis(symbol: str, pnl: float | None = None):
    sym = symbol.strip().upper()
    desc = _universe_pack()["desc"]
    an_hist = _get_price_history(sym, "1y", _symbol_name(sym, desc))
    if an_hist is None or an_hist.empty:
        raise HTTPException(status_code=503, detail="no price data")
    tech = advisor.technical_summary(an_hist)
    last_px = float(an_hist["Close"].iloc[-1]) if pd.notna(an_hist["Close"].iloc[-1]) else None
    qdf = _quotes_df([sym])
    quote = _quote_row(qdf, sym)
    ndf = _get_news(sym, _symbol_name(sym, desc))
    nsum = _news_summary(ndf)
    verdict = advisor.combine_verdict(tech, nsum, pnl)
    return {"symbol": sym, "price": last_px, "quote": quote, "technical": tech, "news": nsum, "verdict": verdict}


@app.get("/api/signals/{symbol}")
def api_signals(symbol: str, request: Request):
    params = request.query_params
    period = params.get("period", "1y")
    sym = symbol.strip().upper()
    desc = _universe_pack()["desc"]
    hist = _get_price_history(sym, period, _symbol_name(sym, desc))
    if hist is None or hist.empty:
        raise HTTPException(status_code=503, detail="no price data")
    sig = signals.detect_signals(hist)
    support, resistance = signals.pivot_levels(hist, window=8, max_each=4)
    return {
        "symbol": sym,
        "signals": _clean(sig),
        "support": _clean(list(support)),
        "resistance": _clean(list(resistance)),
    }


@app.get("/api/news/{symbol}")
def api_news(symbol: str):
    sym = symbol.strip().upper()
    desc = _universe_pack()["desc"]
    ndf = _get_news(sym, _symbol_name(sym, desc))
    if ndf is None or ndf.empty:
        return {"symbol": sym, "summary": None, "rows": []}
    return {"symbol": sym, "summary": _clean(_news_summary(ndf)), "rows": _clean(ndf)}


@app.get("/api/sparks")
def api_sparks(request: Request):
    params = request.query_params
    p = params.get("symbols")
    if p is not None and p.strip():
        syms = [s.strip().upper() for s in p.split(",") if s.strip()]
    else:
        syms = _default_syms()
    key = "sparks:" + ",".join(sorted(set(syms)))

    def _compute():
        return _sparks_vals(list(dict.fromkeys(syms)))

    vals = _cached(key, 1800, _compute)
    return {"rows": [{"ticker": t, "spark": v} for t, v in sorted(vals.items())]}


@app.get("/api/universe")
def api_universe():
    pack = _universe_pack()
    desc, logos = pack["desc"], pack["logos"]
    items = [
        {"ticker": str(t), "description": desc.get(t, ""), "logo": logos.get(t)}
        for t in sorted(desc.keys())
    ]
    return {"count": len(items), "items": _clean(items)}


class CustomSymbolRequest(BaseModel):
    symbol: str


@app.get("/api/custom-symbols")
def api_custom_symbols():
    symbols = db.list_custom_symbols()
    return {"ok": True, "count": len(symbols), "symbols": symbols}


@app.post("/api/custom-symbols", status_code=200)
def api_add_custom_symbol(payload: CustomSymbolRequest):
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    if symbol in db.list_custom_symbols():
        return {"ok": True, "added": False, "message": f"{symbol} already in your list."}
    df = live.get_quotes([symbol])
    px = None
    if df is not None and not df.empty:
        rows = df
        if "ticker" in df.columns:
            rows = df[df["ticker"].astype(str).str.upper() == symbol]
        if not rows.empty and "close" in df.columns:
            val = rows.iloc[0]["close"]
            if isinstance(val, (int, float)) and not pd.isna(val):
                px = val
    if px is None:
        return {"ok": True, "added": False, "message": f"'{symbol}' not found on EGX. Check the symbol."}
    db.add_custom_symbol(symbol)
    return {"ok": True, "added": True, "symbol": symbol, "message": f"added - last {px:,.2f} EGP"}


@app.delete("/api/custom-symbols/{symbol}")
def api_delete_custom_symbol(symbol: str):
    db.delete_custom_symbol(symbol.strip().upper())
    return {"ok": True}


@app.get("/api/market-news")
def api_market_news():
    df = _cached("marketnews", 300, news.market_news)
    if df is None or df.empty:
        return {"rows": []}
    return {"rows": _clean(df.head(60))}


@app.get("/api/movers")
def api_movers(request: Request):
    params = request.query_params
    name = params.get("name", "")
    tab = params.get("tab", "Top Movers")
    d = params.get("d", "desc")
    limit = int(params.get("limit", 12))
    if tab != "Top Movers":
        raise HTTPException(status_code=400, detail="tab must be 'Top Movers'")
    field_entry = MOVER_FIELDS.get(name)
    if field_entry is None:
        raise HTTPException(status_code=404, detail=f"unknown mover set: {name}")
    sort_field, base_asc = field_entry
    descending = d != "asc"
    ascending = base_asc if descending else not base_asc
    key = f"movers:{sort_field}:{int(ascending)}:{limit}"

    def _scan():
        try:
            return live.scan_market(sort_by=sort_field, ascending=ascending, limit=limit)
        except Exception:
            return pd.DataFrame()

    df = _cached(key, 120, _scan)
    if df is None or df.empty:
        return {"rows": []}
    out = df.copy()
    if "Logo" in out.columns:
        out = out.drop(columns=["Logo"])
    logos = _universe_pack()["logos"]
    out["Logo"] = out["ticker"].astype(str).map(lambda t: logos.get(t))
    return {"rows": _clean(out)}


class BacktestReq(BaseModel):
    symbol: str
    strategy: Literal["sma_cross", "macd_cross", "rsi_reversion"] = "sma_cross"
    period: str = "1y"
    fast: int = 20
    slow: int = 50
    initial: float = 100000.0
    fee_pct: float = 0.15
    rsi_n: int = 14
    rsi_oversold: int = 30
    rsi_exit: int = 60


def _bt_params(b: BacktestReq):
    if b.strategy == "sma_cross":
        return {"fast": int(b.fast), "slow": int(b.slow)}
    if b.strategy == "rsi_reversion":
        return {"n": int(b.rsi_n), "oversold": int(b.rsi_oversold), "exit": int(b.rsi_exit)}
    return None


@app.post("/api/backtest")
def api_backtest(payload: BacktestReq):
    sym = payload.symbol.strip().upper()
    if payload.initial <= 0:
        raise HTTPException(status_code=400, detail="initial must be > 0")
    if payload.fee_pct < 0:
        raise HTTPException(status_code=400, detail="fee_pct must be >= 0")
    desc = _universe_pack()["desc"]
    hist = _get_price_history(sym, payload.period, _symbol_name(sym, desc))
    if hist is None or hist.empty:
        raise HTTPException(status_code=503, detail="no price data")
    try:
        res = backtest.run_backtest(
            hist,
            payload.strategy,
            _bt_params(payload),
            initial=payload.initial,
            fee_pct=payload.fee_pct,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"backtest failed: {exc}")
    if not isinstance(res, dict) or "equity" not in res:
        raise HTTPException(status_code=500, detail="backtest returned no equity")
    equity = res["equity"]
    equity_rows = []
    if isinstance(equity, (pd.Series, pd.DataFrame)) and not equity.empty:
        for dt, val in equity.items():
            equity_rows.append(
                {"date": pd.to_datetime(dt).strftime("%Y-%m-%d"), "value": float(val)}
            )
    else:
        raise HTTPException(status_code=500, detail="backtest returned no equity")
    closes = res.get("closes")
    if closes is None:
        closes = hist["Close"].dropna()
    closes = closes.dropna()
    bh_rows = []
    if len(closes) > 0:
        bh_series = payload.initial * closes / closes.iloc[0]
        for dt, val in bh_series.items():
            bh_rows.append(
                {"date": pd.to_datetime(dt).strftime("%Y-%m-%d"), "value": float(val)}
            )
    trades = []
    for t in res.get("trades", []) or []:
        trades.append(
            {
                "entry_date": pd.to_datetime(t["entry_date"]).strftime("%Y-%m-%d"),
                "entry": float(t["entry"]),
                "exit_date": pd.to_datetime(t["exit_date"]).strftime("%Y-%m-%d"),
                "exit": float(t["exit"]),
                "pnl_pct": float(t["pnl_pct"]),
            }
        )
    return {
        "symbol": sym,
        "strategy": payload.strategy,
        "equity": equity_rows,
        "buy_hold": bh_rows,
        "trades": trades,
        "total_return": _clean(res.get("total_return")),
        "ann_return": _clean(res.get("ann_return")),
        "max_drawdown": _clean(res.get("max_drawdown")),
        "sharpe": _clean(res.get("sharpe")),
        "n_trades": _clean(res.get("n_trades")),
        "win_rate": _clean(res.get("win_rate")),
        "avg_win": _clean(res.get("avg_win")),
        "avg_loss": _clean(res.get("avg_loss")),
        "buy_hold_return": _clean(res.get("buy_hold_return")),
        "final_equity": _clean(res.get("final_equity")),
    }


@app.get("/api/risk/{symbol}")
def api_risk(symbol: str):
    sym = symbol.strip().upper()
    desc = _universe_pack()["desc"]
    hist = _get_price_history(sym, "6mo", _symbol_name(sym, desc))
    if hist is None or hist.empty:
        return {"symbol": sym, "stops": {}}
    try:
        stops = risk.stop_suggestions(hist)
    except Exception:
        return {"symbol": sym, "stops": {}}
    if stops is None:
        return {"symbol": sym, "stops": {}}
    return {"symbol": sym, "stops": _clean(stops)}
