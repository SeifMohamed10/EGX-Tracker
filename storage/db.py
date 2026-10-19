import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "egx.db"

_OHLCV_COLS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT NOT NULL,
                date   TEXT NOT NULL,
                open   REAL,
                high   REAL,
                low    REAL,
                close  REAL,
                volume REAL,
                PRIMARY KEY (symbol, date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol          TEXT NOT NULL,
                kind            TEXT NOT NULL,
                target          REAL NOT NULL,
                note            TEXT DEFAULT '',
                active          INTEGER DEFAULT 1,
                created_at      TEXT,
                triggered_at    TEXT,
                triggered_value REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol   TEXT NOT NULL,
                qty      REAL NOT NULL,
                avg_cost REAL NOT NULL,
                bought_at TEXT,
                note     TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS custom_symbols (symbol TEXT PRIMARY KEY)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS yahoo_alias (symbol TEXT PRIMARY KEY, yahoo TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )


def get_setting(key: str, default: str = "") -> str:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row and row[0] is not None else default


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))


def get_yahoo_alias(symbol: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT yahoo FROM yahoo_alias WHERE symbol = ?", (symbol,)).fetchone()
    return row[0] if row else None


def set_yahoo_alias(symbol: str, yahoo_symbol: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO yahoo_alias (symbol, yahoo) VALUES (?, ?)",
            (symbol, yahoo_symbol),
        )


def add_custom_symbol(symbol: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO custom_symbols (symbol) VALUES (?)", (symbol,))


def list_custom_symbols() -> list[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT symbol FROM custom_symbols ORDER BY symbol").fetchall()
    return [r[0] for r in rows]


def delete_custom_symbol(symbol: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM custom_symbols WHERE symbol = ?", (symbol,))


def add_position(symbol: str, qty: float, avg_cost: float, bought_at: str = "", note: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO positions (symbol, qty, avg_cost, bought_at, note) VALUES (?, ?, ?, ?, ?)",
            (symbol, qty, avg_cost, bought_at, note),
        )


def list_positions() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql_query("SELECT * FROM positions ORDER BY symbol, id", conn)


def delete_position(position_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))


ALERT_KINDS = {
    "price_above": "Price rises above",
    "price_below": "Price falls below",
    "pct_above": "Day change above %",
    "pct_below": "Day change below %",
    "rsi_above": "RSI14 above",
    "rsi_below": "RSI14 below",
}


def add_alert(symbol: str, kind: str, target: float, note: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO alerts (symbol, kind, target, note, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (symbol, kind, target, note, pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def list_alerts(active_only: bool = False) -> pd.DataFrame:
    query = "SELECT * FROM alerts"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id DESC"
    with _connect() as conn:
        return pd.read_sql_query(query, conn)


def delete_alert(alert_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))


def mark_triggered(alert_id: int, value: float) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE alerts SET active = 0, triggered_at = ?, triggered_value = ? WHERE id = ?",
            (pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), value, alert_id),
        )


def save_history(symbol: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    rows = [
        (
            symbol,
            pd.Timestamp(idx).strftime("%Y-%m-%d"),
            float(row["Open"]),
            float(row["High"]),
            float(row["Low"]),
            float(row["Close"]),
            float(row["Volume"]),
        )
        for idx, row in df.iterrows()
        if pd.notna(row["Open"])
        and pd.notna(row["High"])
        and pd.notna(row["Low"])
        and pd.notna(row["Close"])
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO ohlcv (symbol, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def load_history(symbol: str) -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT date AS Date, open AS Open, high AS High, low AS Low, "
            "close AS Close, volume AS Volume FROM ohlcv WHERE symbol = ? ORDER BY date",
            conn,
            params=(symbol,),
        )
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    return df


init_db()
