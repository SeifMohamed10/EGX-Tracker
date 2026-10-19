import pandas as pd
import requests

MUBASHER_PRICES_URL = "https://www.mubasher.info/api/1/stocks/prices"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
}

_NUM_COLS = ["value", "change", "open", "high", "low", "volume", "turnover"]


def _to_float(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def fetch_market_snapshot() -> pd.DataFrame:
    """Whole-EGX snapshot from Mubasher's public web API (per-stock updatedAt)."""
    resp = requests.get(MUBASHER_PRICES_URL, params={"country": "eg"}, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    body = resp.json()
    rows = []
    for item in body.get("prices", []):
        pct = _to_float(item.get("changePercentage"))
        rows.append(
            {
                "symbol": f"EGX:{item.get('code')}",
                "ticker": item.get("code"),
                "name": item.get("name"),
                "close": _to_float(item.get("value")),
                "open": _to_float(item.get("open")),
                "high": _to_float(item.get("high")),
                "low": _to_float(item.get("low")),
                "volume": _to_float(item.get("volume")),
                "turnover": _to_float(item.get("turnover")),
                "change_abs": _to_float(item.get("change")),
                "change": pct,
                "status": item.get("status"),
                "updated_at": item.get("updatedAt"),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    prev = df["close"] - df["change_abs"]
    df["prev_close"] = prev
    df["market_cap_basic"] = None
    return df


def get_quotes(symbols: list[str]) -> pd.DataFrame:
    """Quotes filtered to requested EGX tickers."""
    snap = fetch_market_snapshot()
    if snap.empty:
        return pd.DataFrame(columns=["ticker", "name", "close", "change", "change_abs", "open", "high", "low", "volume"])
    out = snap[snap["ticker"].isin(set(symbols))].copy()
    return out.reset_index(drop=True)
