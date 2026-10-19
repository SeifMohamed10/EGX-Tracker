import pandas as pd

from data import indicators

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


def _sma_crosses(df: pd.DataFrame, fast: int, slow: int) -> list[dict]:
    signals = []
    if len(df) < slow + 5:
        return signals
    fast_ma = df["Close"].rolling(fast).mean()
    slow_ma = df["Close"].rolling(slow).mean()
    diff = (fast_ma - slow_ma).dropna()
    if diff.empty:
        return signals
    cross_up = diff.index[(diff.shift(1) < 0) & (diff >= 0)]
    cross_dn = diff.index[(diff.shift(1) > 0) & (diff <= 0)]
    for idx in cross_up[-2:]:
        signals.append(
            {
                "date": idx,
                "type": f"Golden Cross SMA{fast}/SMA{slow}",
                "direction": BULLISH,
                "detail": f"SMA{fast} crossed above SMA{slow}",
            }
        )
    for idx in cross_dn[-2:]:
        signals.append(
            {
                "date": idx,
                "type": f"Death Cross SMA{fast}/SMA{slow}",
                "direction": BEARISH,
                "detail": f"SMA{fast} crossed below SMA{slow}",
            }
        )
    return signals


def _macd_crosses(df: pd.DataFrame) -> list[dict]:
    signals = []
    macd_line, signal_line, _ = indicators.macd(df)
    diff = (macd_line - signal_line).dropna()
    if diff.empty:
        return signals
    bull = diff.index[(diff.shift(1) < 0) & (diff >= 0)]
    bear = diff.index[(diff.shift(1) > 0) & (diff <= 0)]
    for idx in bull[-1:]:
        signals.append({"date": idx, "type": "MACD Bullish Cross", "direction": BULLISH, "detail": "MACD crossed above signal"})
    for idx in bear[-1:]:
        signals.append({"date": idx, "type": "MACD Bearish Cross", "direction": BEARISH, "detail": "MACD crossed below signal"})
    return signals


def _rsi_state(df: pd.DataFrame) -> list[dict]:
    rsi = indicators.rsi(df)
    if len(rsi.dropna()) < 15:
        return []
    last = float(rsi.iloc[-1])
    prev = float(rsi.iloc[-6])
    signals = []
    if last >= 70:
        direction = NEUTRAL if last <= prev else BEARISH
        signals.append({"date": df.index[-1], "type": f"RSI Overbought ({last:.0f})", "direction": direction, "detail": f"RSI14 at {last:.1f} (>=70)"})
    elif last <= 30:
        direction = NEUTRAL if last >= prev else BULLISH
        signals.append({"date": df.index[-1], "type": f"RSI Oversold ({last:.0f})", "direction": direction, "detail": f"RSI14 at {last:.1f} (<=30)"})
    return signals


def _volume_spike(df: pd.DataFrame, mult: float = 2.0) -> list[dict]:
    if len(df) < 21 or df["Volume"].iloc[-1] == 0:
        return []
    avg = float(df["Volume"].iloc[-21:-1].mean())
    if avg <= 0:
        return []
    ratio = float(df["Volume"].iloc[-1]) / avg
    if ratio >= mult:
        change_pct = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-2]) - 1) * 100
        direction = BULLISH if change_pct >= 0 else BEARISH
        signals = [
            {
                "date": df.index[-1],
                "type": f"Volume Spike ({ratio:.1f}x)",
                "direction": direction,
                "detail": f"Volume {ratio:.1f}x the 20-day average ({change_pct:+.1f}% day)",
            }
        ]
        return signals
    return []


def _week52(df: pd.DataFrame) -> list[dict]:
    close = df["Close"]
    window = close.tail(252)
    if len(window) < 60:
        return []
    hi = float(window.max())
    lo = float(window.min())
    last = float(close.iloc[-1])
    signals = []
    if lo > 0 and last <= lo * 1.03:
        signals.append({"date": df.index[-1], "type": "Near 52w Low", "direction": NEUTRAL, "detail": f"Price within 3% of 52-week low ({lo:,.2f})"})
    elif last >= hi * 0.97:
        signals.append({"date": df.index[-1], "type": "Near 52w High", "direction": NEUTRAL, "detail": f"Price within 3% of 52-week high ({hi:,.2f})"})
    return signals


def detect_signals(df: pd.DataFrame) -> list[dict]:
    if df is None or len(df) < 30:
        return []
    signals = []
    for f, s in ((50, 200), (20, 50)):
        signals.extend(_sma_crosses(df, f, s))
    signals.extend(_macd_crosses(df))
    signals.extend(_rsi_state(df))
    signals.extend(_volume_spike(df))
    signals.extend(_week52(df))
    signals.sort(key=lambda x: x["date"], reverse=True)
    return signals


def _cluster(levels: list[float], tol: float = 0.01) -> list[float]:
    levels = sorted(levels)
    groups: list[list[float]] = []
    for lv in levels:
        if groups and abs(lv - groups[-1][-1]) / groups[-1][-1] < tol:
            groups[-1].append(lv)
        else:
            groups.append([lv])
    return [sum(g) / len(g) for g in groups]


def pivot_levels(
    df: pd.DataFrame, window: int = 8, max_each: int = 4
) -> tuple[list[float], list[float]]:
    """Return (support_levels, resistance_levels), nearest first.

    When one side has no swing pivots (e.g. price at all-time highs), ATR-projected
    levels are added so the chart always shows reference lines.
    """
    if df is None or len(df) < window * 2 + 10:
        return [], []
    highs = df["High"]
    lows = df["Low"]
    last_close = float(df["Close"].iloc[-1])
    swing_highs, swing_lows = [], []
    for i in range(window, len(df) - window):
        seg_h = highs.iloc[i - window : i + window + 1]
        seg_l = lows.iloc[i - window : i + window + 1]
        if highs.iloc[i] >= seg_h.max():
            swing_highs.append(float(highs.iloc[i]))
        if lows.iloc[i] <= seg_l.min():
            swing_lows.append(float(lows.iloc[i]))
    resistance = [lv for lv in _cluster(swing_highs) if lv > last_close][:max_each]
    support = sorted((lv for lv in _cluster(swing_lows) if lv < last_close), reverse=True)[:max_each]

    if not resistance or not support:
        try:
            from data.risk import atr

            atr14 = float(atr(df, 14).iloc[-1])
        except Exception:
            atr14 = 0.0
        if atr14 and not pd.isna(atr14) and atr14 > 0:
            if not resistance:
                resistance = [last_close + atr14, last_close + 2 * atr14]
            if not support:
                support = [last_close - atr14, last_close - 2 * atr14]
    return support, resistance
