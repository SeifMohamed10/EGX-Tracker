import numpy as np
import pandas as pd

from data import indicators

STRATEGIES = {
    "sma_cross": "SMA Crossover",
    "macd_cross": "MACD Cross",
    "rsi_reversion": "RSI Mean Reversion",
}


def _conditions(df: pd.DataFrame, strategy: str, params: dict) -> tuple[pd.Series, pd.Series]:
    close = df["Close"]
    if strategy == "sma_cross":
        fast = int(params.get("fast", 20))
        slow = int(params.get("slow", 50))
        fma = close.rolling(fast).mean()
        sma = close.rolling(slow).mean()
        entry = (fma > sma) & (fma.shift(1) <= sma.shift(1))
        exit_ = (fma < sma) & (fma.shift(1) >= sma.shift(1))
    elif strategy == "macd_cross":
        macd_line, signal_line, _ = indicators.macd(df)
        diff = macd_line - signal_line
        entry = (diff > 0) & (diff.shift(1) <= 0)
        exit_ = (diff < 0) & (diff.shift(1) >= 0)
    elif strategy == "rsi_reversion":
        n = int(params.get("n", 14))
        oversold = float(params.get("oversold", 30))
        exit_level = float(params.get("exit", 60))
        rsi = indicators.rsi(df, n)
        entry = (rsi < oversold) & (rsi.shift(1) >= oversold)
        exit_ = rsi > exit_level
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    return entry.fillna(False), exit_.fillna(False)


def _simulate(
    df: pd.DataFrame, entry: pd.Series, exit_: pd.Series, initial: float, fee_pct: float
) -> tuple[pd.Series, list[dict]]:
    open_px = df["Open"]
    close_px = df["Close"]
    cash = initial
    shares = 0.0
    equity = []
    trades: list[dict] = []
    open_trade = None

    for i in range(len(df)):
        if i > 0:
            if shares == 0.0 and bool(entry.iloc[i - 1]):
                price = float(open_px.iloc[i])
                if price > 0:
                    fee = cash * fee_pct / 100.0
                    shares = (cash - fee) / price
                    cash = 0.0
                    open_trade = {"entry_date": df.index[i], "entry": price}
            elif shares > 0.0 and bool(exit_.iloc[i - 1]):
                price = float(open_px.iloc[i])
                proceeds = shares * price
                fee = proceeds * fee_pct / 100.0
                cash = proceeds - fee
                if open_trade is not None:
                    pnl_pct = (price / open_trade["entry"] - 1) * 100
                    trades.append(
                        {
                            **open_trade,
                            "exit_date": df.index[i],
                            "exit": price,
                            "pnl_pct": pnl_pct,
                        }
                    )
                    open_trade = None
                shares = 0.0
        equity.append(cash + shares * float(close_px.iloc[i]))

    eq = pd.Series(equity, index=df.index)
    return eq, trades


def run_backtest(
    df: pd.DataFrame,
    strategy: str = "sma_cross",
    params: dict | None = None,
    initial: float = 100_000.0,
    fee_pct: float = 0.15,
) -> dict:
    params = params or {}
    entry, exit_ = _conditions(df, strategy, params)
    eq, trades = _simulate(df, entry, exit_, initial, fee_pct)

    n = len(eq)
    total_return = (eq.iloc[-1] / initial - 1) * 100
    ann_return = ((eq.iloc[-1] / initial) ** (252 / max(n, 1)) - 1) * 100 if n > 30 else float("nan")
    roll_max = eq.cummax()
    drawdown = eq / roll_max - 1
    max_dd = drawdown.min() * 100

    daily_ret = eq.pct_change().dropna()
    sharpe = (
        float(daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0.0
    )

    wins = [t for t in trades if t["pnl_pct"] > 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0.0
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0.0
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0.0

    bh_return = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100

    return {
        "equity": eq,
        "trades": trades,
        "total_return": total_return,
        "ann_return": ann_return,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "n_trades": len(trades),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "buy_hold_return": bh_return,
        "final_equity": float(eq.iloc[-1]),
    }
