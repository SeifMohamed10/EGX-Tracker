import pandas as pd
import yfinance as yf

from data.tickers import yahoo_symbol
from storage import db


def _is_dead(df: pd.DataFrame) -> bool:
    """Yahoo sometimes serves flat zero-volume placeholder series for delisted/renamed tickers."""
    if df is None or df.empty or len(df) < 10:
        return True
    tail = df.tail(30)
    if (tail["Volume"] == 0).all() and tail["Close"].nunique() <= 2:
        return True
    return False


def _scale_mismatch(df: pd.DataFrame, live_last: float | None) -> bool:
    if df is None or df.empty or not live_last:
        return False
    last = float(df["Close"].iloc[-1])
    if last <= 0:
        return True
    return abs(last - float(live_last)) / float(live_last) > 0.25


def _download(sym: str, period: str, interval: str) -> pd.DataFrame:
    raw = yf.download(sym, period=period, interval=interval, progress=False, auto_adjust=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw[["Open", "High", "Low", "Close", "Volume"]].dropna(how="all")


def _resolve_alias(symbol: str, name_hint: str | None) -> str | None:
    alias = db.get_yahoo_alias(symbol)
    if alias:
        return alias
    query = name_hint or symbol
    try:
        results = yf.Search(query, max_results=8).quotes
    except Exception:
        return None
    for q in results:
        sym = q.get("symbol") or ""
        if sym.endswith(".CA") and sym.upper() != yahoo_symbol(symbol).upper():
            db.set_yahoo_alias(symbol, sym)
            return sym
    return None


def fetch_history(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    name_hint: str | None = None,
    live_last: float | None = None,
) -> pd.DataFrame:
    """Yahoo OHLCV with dead-series detection, alias resolution and SQLite fallback."""
    df = pd.DataFrame()
    try:
        df = _download(yahoo_symbol(symbol), period, interval)
    except Exception:
        df = pd.DataFrame()

    if _is_dead(df) or _scale_mismatch(df, live_last):
        alias = _resolve_alias(symbol, name_hint)
        if alias:
            try:
                alt = _download(alias, period, interval)
                if not _is_dead(alt) and not _scale_mismatch(alt, live_last):
                    db.save_history(symbol, alt)
                    return alt
            except Exception:
                pass

    if not df.empty and not _is_dead(df):
        db.save_history(symbol, df)
        return df

    cached = db.load_history(symbol)
    return cached


def fetch_history_multi(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    return {s: fetch_history(s, period=period) for s in symbols}
