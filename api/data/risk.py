import math

import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def stop_suggestions(df: pd.DataFrame) -> dict | None:
    """Long-side stop ideas below the latest close."""
    if df is None or len(df) < n_atr_min():
        return None
    last_close = float(df["Close"].iloc[-1])
    atr14 = float(atr(df, 14).iloc[-1])
    if not atr14 or math.isnan(atr14):
        return None
    swing_low = float(df["Low"].tail(20).min())
    return {
        "close": last_close,
        "atr14": atr14,
        "stop_1x": last_close - atr14,
        "stop_2x": last_close - 2 * atr14,
        "stop_3x": last_close - 3 * atr14,
        "swing_low": swing_low,
    }


def n_atr_min() -> int:
    return 30


def position_size(capital: float, risk_pct: float, entry: float, stop: float) -> dict | None:
    per_share_risk = abs(entry - stop)
    if capital <= 0 or risk_pct <= 0 or entry <= 0 or per_share_risk <= 0:
        return None
    risk_amount = capital * risk_pct / 100.0
    shares = math.floor(risk_amount / per_share_risk)
    cost = shares * entry
    actual_risk = shares * per_share_risk
    return {
        "shares": int(shares),
        "cost": cost,
        "risk_amount": risk_amount,
        "actual_risk": actual_risk,
        "per_share_risk": per_share_risk,
        "cash_used_pct": cost / capital * 100 if capital else 0.0,
    }
