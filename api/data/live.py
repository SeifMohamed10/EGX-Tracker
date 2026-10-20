import requests

import pandas as pd

from data.tickers import tv_symbol

TV_SCAN_URL = "https://scanner.tradingview.com/egypt/scan"

COLUMNS = [
    "name",
    "close",
    "open",
    "high",
    "low",
    "change",
    "change_abs",
    "volume",
    "market_cap_basic",
    "currency",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Content-Type": "application/json",
}


def _scan(payload: dict, columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns if columns is not None else COLUMNS
    resp = requests.post(TV_SCAN_URL, json=payload, headers=_HEADERS, timeout=10)
    resp.raise_for_status()
    body = resp.json()
    rows = []
    for item in body.get("data", []):
        row = {"symbol": item.get("s")}
        row.update(dict(zip(cols, item.get("d", []))))
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["symbol"] + COLUMNS)
    df = pd.DataFrame(rows)
    for col in ("close", "open", "high", "low", "change", "change_abs", "volume", "market_cap_basic"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "close" in df.columns and "change_abs" in df.columns:
        df["prev_close"] = df["close"] - df["change_abs"]
    return df


def get_quotes(symbols: list[str]) -> pd.DataFrame:
    """Live-ish quotes (15 min delayed) for specific EGX symbols."""
    payload = {
        "markets": ["egypt"],
        "symbols": {
            "query": {"types": []},
            "tickers": [tv_symbol(s) for s in symbols],
        },
        "columns": COLUMNS,
        "sort": {"sortBy": "name", "sortOrder": "asc"},
        "range": [0, max(len(symbols), 1)],
    }
    df = _scan(payload)
    if not df.empty:
        df["ticker"] = df["symbol"].str.replace("EGX:", "", regex=False)
    return df


def scan_market(sort_by: str = "market_cap_basic", ascending: bool = False, limit: int = 30) -> pd.DataFrame:
    """Scan the whole EGX market sorted by a field (e.g. change % or volume)."""
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "options": {"lang": "en"},
        "markets": ["egypt"],
        "symbols": {"query": {"types": []}},
        "columns": COLUMNS,
        "sort": {"sortBy": sort_by, "sortOrder": "asc" if ascending else "desc"},
        "range": [0, limit],
    }
    df = _scan(payload)
    if not df.empty:
        df["ticker"] = df["symbol"].str.replace("EGX:", "", regex=False)
    return df

def get_all_symbols(limit: int = 500) -> pd.DataFrame:
    """Full EGX listed-stock universe with company names and logo ids."""
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "options": {"lang": "en"},
        "markets": ["egypt"],
        "symbols": {"query": {"types": []}},
        "columns": ["name", "description", "logoid"],
        "sort": {"sortBy": "name", "sortOrder": "asc"},
        "range": [0, limit],
    }
    df = _scan(payload, columns=["name", "description", "logoid"])
    if not df.empty:
        df["ticker"] = df["symbol"].str.replace("EGX:", "", regex=False)
    return df


def logo_url(logoid) -> str:
    if logoid is None or (isinstance(logoid, float) and pd.isna(logoid)) or str(logoid).strip() in ("", "nan"):
        return ""
    return f"https://s3-symbol-logo.tradingview.com/{logoid}.svg"
