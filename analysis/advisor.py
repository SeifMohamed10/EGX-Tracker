import pandas as pd

from data import indicators, signals

TECH_WEIGHT = 0.55
NEWS_WEIGHT = 0.45


def technical_summary(hist: pd.DataFrame) -> dict:
    enriched = indicators.add_all(hist)
    found = signals.detect_signals(hist)
    bull = sum(1 for s in found if s["direction"] == "bullish")
    bear = sum(1 for s in found if s["direction"] == "bearish")

    last_close = float(hist["Close"].iloc[-1])
    sma50 = float(enriched["SMA50"].iloc[-1]) if pd.notna(enriched["SMA50"].iloc[-1]) else None
    sma200 = float(enriched["SMA200"].iloc[-1]) if pd.notna(enriched["SMA200"].iloc[-1]) else None

    trend_ref, trend_label = None, "unknown"
    if sma200 is not None:
        trend_ref = sma200
        trend_label = "above SMA200 (long-term uptrend)" if last_close > sma200 else "below SMA200 (long-term downtrend)"
        trend_component = 1.0 if last_close > sma200 else -1.0
    elif sma50 is not None:
        trend_ref = sma50
        trend_label = "above SMA50" if last_close > sma50 else "below SMA50"
        trend_component = 1.0 if last_close > sma50 else -1.0
    else:
        trend_component = 0.0

    rsi_val = float(enriched["RSI14"].iloc[-1]) if pd.notna(enriched["RSI14"].iloc[-1]) else None

    signal_score = max(-1.0, min(1.0, (bull - bear) / 3.0))
    tech_score = max(-1.0, min(1.0, 0.6 * signal_score + 0.4 * trend_component))

    return {
        "bull": bull,
        "bear": bear,
        "trend_label": trend_label,
        "rsi": rsi_val,
        "last_close": last_close,
        "score": tech_score,
        "signals": found[:5],
    }


def combine_verdict(tech: dict, news_sum: dict | None, pnl_pct: float | None) -> dict:
    reasons = []

    tech_part = TECH_WEIGHT * tech["score"]
    if news_sum is not None:
        combined = tech_part + NEWS_WEIGHT * news_sum["avg_compound"]
    else:
        combined = tech["score"]
        reasons.append("News sentiment unavailable - verdict based on technicals only.")

    if tech["score"] > 0.2:
        reasons.append(f"Technically constructive: {tech['bull']} bullish vs {tech['bear']} bearish signals, {tech['trend_label']}.")
    elif tech["score"] < -0.2:
        reasons.append(f"Technically weak: {tech['bear']} bearish vs {tech['bull']} bullish signals, {tech['trend_label']}.")
    else:
        reasons.append(f"Technically neutral: {tech['bull']} bullish / {tech['bear']} bearish, {tech['trend_label']}.")

    if tech["rsi"] is not None:
        if tech["rsi"] >= 70:
            reasons.append(f"RSI {tech['rsi']:.0f} overbought - chasing here carries pullback risk.")
        elif tech["rsi"] <= 30:
            reasons.append(f"RSI {tech['rsi']:.0f} oversold - selling here may be near a short-term extreme.")
        else:
            reasons.append(f"RSI {tech['rsi']:.0f} neutral zone.")

    if news_sum is not None:
        tone = "positive" if news_sum["avg_compound"] > 0.05 else ("negative" if news_sum["avg_compound"] < -0.05 else "mixed")
        reasons.append(
            f"News sentiment {tone} ({news_sum['avg_compound']:+.2f}): {news_sum['positive']} positive / "
            f"{news_sum['negative']} negative / {news_sum['neutral']} neutral of {news_sum['n']} recent headlines."
        )

    if pnl_pct is not None:
        if pnl_pct <= -15:
            reasons.append(f"Position is down {pnl_pct:.1f}% - decide whether the original thesis still holds or you are averaging into weakness.")
        elif pnl_pct >= 15:
            reasons.append(f"Position is up {pnl_pct:.1f}% - consider trailing stops to protect gains.")

    if combined >= 0.25:
        label, emoji = "LEAN KEEP", "🟢"
    elif combined <= -0.25:
        label, emoji = "CONSIDER REDUCING / EXITING", "🔴"
    else:
        label, emoji = "HOLD & MONITOR", "🟡"

    return {
        "label": label,
        "emoji": emoji,
        "score": combined,
        "reasons": reasons,
    }
