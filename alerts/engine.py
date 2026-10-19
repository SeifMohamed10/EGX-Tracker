import pandas as pd

from data import indicators
from storage import db


def current_value(kind: str, quote: dict | None, hist: pd.DataFrame | None) -> float | None:
    if kind in ("price_above", "price_below"):
        if quote is not None and pd.notna(quote.get("close")):
            return float(quote["close"])
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    if kind in ("pct_above", "pct_below"):
        if quote is not None and pd.notna(quote.get("change")):
            return float(quote["change"])
        return None
    if kind in ("rsi_above", "rsi_below"):
        if hist is None or len(hist) < 20:
            return None
        return float(indicators.rsi(hist).iloc[-1])
    return None


def _condition_met(kind: str, value: float, target: float) -> bool:
    if kind.endswith("_above"):
        return value >= target
    return value <= target


def evaluate(alerts: pd.DataFrame, quotes: pd.DataFrame, history_getter) -> list[dict]:
    """Check active alerts. Returns newly triggered ones (and persists the trigger).

    history_getter(symbol) -> DataFrame, used only for RSI alerts.
    """
    triggered = []
    if alerts is None or alerts.empty:
        return triggered
    quote_map = {}
    if quotes is not None and not quotes.empty:
        quote_map = {r["ticker"]: r for _, r in quotes.iterrows()}

    for _, alert in alerts[alerts["active"] == 1].iterrows():
        symbol = alert["symbol"]
        kind = alert["kind"]
        target = float(alert["target"])
        quote = quote_map.get(symbol)
        hist = history_getter(symbol) if kind.startswith("rsi") else None
        value = current_value(kind, quote, hist)
        if value is None:
            continue
        if _condition_met(kind, value, target):
            db.mark_triggered(int(alert["id"]), value)
            triggered.append(
                {
                    "id": int(alert["id"]),
                    "symbol": symbol,
                    "kind": kind,
                    "target": target,
                    "value": value,
                    "note": alert.get("note", ""),
                }
            )
    return triggered


def describe(trigger: dict) -> str:
    label = db.ALERT_KINDS.get(trigger["kind"], trigger["kind"])
    return f"{trigger['symbol']}: {label} {trigger['target']:g} - now {trigger['value']:g}"
