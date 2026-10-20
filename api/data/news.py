import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from data.tickers import yahoo_symbol

_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
}
_analyzer = SentimentIntensityAnalyzer()


def google_news(query: str, max_items: int = 12) -> list[dict]:
    """Headlines from Google News RSS (free, no key)."""
    url = (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        resp = requests.get(url, headers=_UA, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate") or ""
        link = item.findtext("link") or ""
        source = ""
        src_el = item.find("source")
        if src_el is not None and src_el.text:
            source = src_el.text.strip()
        items.append({"title": title, "published": pub, "source": source, "url": link})
    return [i for i in items if i["title"]]


def yahoo_news(symbol: str, max_items: int = 8) -> list[dict]:
    """Ticker news from Yahoo Finance, best effort."""
    try:
        raw = yf.Ticker(yahoo_symbol(symbol)).news or []
    except Exception:
        return []
    items = []
    for entry in raw[:max_items]:
        content = entry.get("content", entry)
        title = content.get("title") or ""
        if not title:
            continue
        pub = content.get("pubDate") or content.get("providerPublishTime") or ""
        if isinstance(pub, (int, float)):
            pub = datetime.fromtimestamp(pub, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        url = ""
        canonical = content.get("canonicalUrl")
        if isinstance(canonical, dict):
            url = canonical.get("url", "")
        elif isinstance(content.get("clickThroughUrl"), dict):
            url = content["clickThroughUrl"].get("url", "")
        items.append({"title": title.strip(), "published": str(pub), "source": "Yahoo Finance", "url": url})
    return items


def score_headlines(headlines: list[str]) -> list[dict]:
    scored = []
    for h in headlines:
        compound = _analyzer.polarity_scores(h)["compound"]
        if compound >= 0.05:
            tag = "positive"
        elif compound <= -0.05:
            tag = "negative"
        else:
            tag = "neutral"
        scored.append({"title": h, "compound": compound, "tag": tag})
    return scored


def company_query(symbol: str, name: str) -> str:
    base = f'"{name}"' if name else symbol
    return f"{base} OR {symbol} Egypt stock"


def collect_news(symbol: str, name: str = "") -> pd.DataFrame:
    headlines = []
    seen = set()

    def push(items: list[dict], origin: str) -> None:
        for it in items:
            key = it["title"].lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            headlines.append({**it, "origin": origin})

    push(google_news(company_query(symbol, name), 12), "Google News")
    push(yahoo_news(symbol, 8), "Yahoo Finance")

    if not headlines:
        return pd.DataFrame(columns=["title", "published", "source", "url", "origin", "compound", "tag"])

    df = pd.DataFrame(headlines)
    scores = score_headlines(df["title"].tolist())
    df["compound"] = [s["compound"] for s in scores]
    df["tag"] = [s["tag"] for s in scores]
    return df


def summarize_news(df: pd.DataFrame) -> dict | None:
    if df is None or df.empty:
        return None
    pos = int((df["tag"] == "positive").sum())
    neg = int((df["tag"] == "negative").sum())
    neu = int((df["tag"] == "neutral").sum())
    return {
        "n": len(df),
        "avg_compound": float(df["compound"].mean()),
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "pos_pct": pos / len(df) * 100,
        "neg_pct": neg / len(df) * 100,
    }


def market_news(max_per_source: int = 30) -> pd.DataFrame:
    """Market-level EGX news: Google News EGX query + Daily News Egypt feed."""
    queries = [
        ("Google News", "EGX OR \"Egyptian Exchange\" OR EGX30 OR Egypt stocks"),
        ("Daily News Egypt", None),
    ]
    frames = []
    for source, query in queries:
        if query is None:
            url = "https://dailynewsegypt.com/feed/"
            try:
                resp = requests.get(url, headers=_UA, timeout=12)
                root = ET.fromstring(resp.content)
            except Exception:
                continue
            items = []
            for item in root.findall(".//item")[:max_per_source]:
                title = (item.findtext("title") or "").strip()
                if not title:
                    continue
                items.append(
                    {
                        "title": title,
                        "published": item.findtext("pubDate") or "",
                        "source": "Daily News Egypt",
                        "url": item.findtext("link") or "",
                    }
                )
        else:
            items = google_news(query, max_per_source)
            for it in items:
                it["source"] = source
        frames.extend(items)

    if not frames:
        return pd.DataFrame(columns=["title", "published", "source", "url", "compound", "tag"])

    df = pd.DataFrame(frames).drop_duplicates(subset=["title"])
    df["dt"] = pd.to_datetime(df["published"], format="mixed", errors="coerce", utc=True)
    df = df.sort_values("dt", ascending=False).head(60).reset_index(drop=True)
    scored = score_headlines(df["title"].tolist())
    df["compound"] = [s["compound"] for s in scored]
    df["tag"] = [s["tag"] for s in scored]
    return df
