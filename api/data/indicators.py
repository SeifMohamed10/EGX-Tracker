import pandas as pd


def sma(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return df["Close"].rolling(window=n).mean()


def ema(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return df["Close"].ewm(span=n, adjust=False).mean()


def rsi(df: pd.DataFrame, n: int = 14) -> pd.Series:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd_line = df["Close"].ewm(span=fast, adjust=False).mean() - df["Close"].ewm(
        span=slow, adjust=False
    ).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = df["Close"].rolling(window=n).mean()
    std = df["Close"].rolling(window=n).std()
    return mid + k * std, mid, mid - k * std


def add_all(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["SMA20"] = sma(out, 20)
    out["SMA50"] = sma(out, 50)
    out["SMA200"] = sma(out, 200)
    out["EMA20"] = ema(out, 20)
    out["RSI14"] = rsi(out, 14)
    out["MACD"], out["MACD_Signal"], out["MACD_Hist"] = macd(out)
    out["BB_Upper"], out["BB_Mid"], out["BB_Lower"] = bollinger(out)
    return out
