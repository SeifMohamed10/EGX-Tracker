import sys
import time
import winsound
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

sys.path.insert(0, str(Path(__file__).resolve().parent))

from alerts import engine  # noqa: E402
from analysis import advisor  # noqa: E402
from data import backtest, indicators, live, mubasher, news, risk, signals  # noqa: E402
from data.fetcher import fetch_history  # noqa: E402
from data.tickers import DEFAULT_WATCHLIST, EGX_TICKERS, tv_symbol  # noqa: E402
from storage import db  # noqa: E402
from ui.charts import candlestick_chart  # noqa: E402
from ui.tv_widget import advanced_chart_html  # noqa: E402

st.set_page_config(page_title="EGX Tracker", page_icon="📈", layout="wide")

PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": "hover",
    "displaylogo": False,
    "modeBarButtonsToRemove": ["toImage", "sendDataToCloud", "toggleSpikelines"],
    "modeBarButtonsToAdd": ["drawline", "eraseshape"],
    "doubleClick": "reset",
}

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');

    header[data-testid="stHeader"] {
        background: transparent;
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
        pointer-events: auto;
    }
    .block-container { padding-top: 2.2rem !important; padding-bottom: 2rem; max-width: 1600px; }

    .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
             background: var(--pagebg) !important; }
    .block-container { animation: pagein .45s ease; }
    @keyframes pagein { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { .block-container { animation: none; } .tape-track { animation: none; } }
    h1, h2, h3, .hero-title, .sec-t { font-family: 'Sora', 'Inter', system-ui, sans-serif; }
    div[data-testid="stMetricValue"], .tape-track, div[data-testid="stDataFrame"] {
        font-variant-numeric: tabular-nums;
    }

    .hero { display: flex; align-items: flex-start; justify-content: space-between;
            flex-wrap: wrap; gap: .7rem; margin-bottom: .15rem; }
    .hero-left { display: flex; align-items: center; gap: .8rem; }
    .logo { width: 48px; height: 48px; border-radius: 15px; flex: 0 0 auto;
            background: linear-gradient(135deg, #26a69a 10%, #7e57c2 90%);
            display: flex; align-items: center; justify-content: center; font-size: 25px;
            box-shadow: 0 8px 22px rgba(38,166,154,.35); }
    .hero-title { font-size: 1.72rem; font-weight: 800; letter-spacing: .2px; line-height: 1.2;
                  color: var(--title-fallback); }
    @supports ((-webkit-background-clip: text) or (background-clip: text)) {
        .hero-title { background: var(--title-grad); -webkit-background-clip: text;
                      background-clip: text; color: transparent; -webkit-text-fill-color: transparent; }
    }
    .hero-sub { opacity: .6; font-size: .84rem; margin-top: 3px; }
    .hero-sub b { opacity: 1; font-weight: 600; }
    .hero-right { text-align: right; padding-top: .25rem; }
    .clock { opacity: .55; font-size: .8rem; margin-top: 5px; }

    .tape-wrap { margin: .75rem 0 .2rem 0; overflow: hidden; border-radius: 13px;
                 border: 1px solid var(--line); background: var(--tape);
                 -webkit-mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
                 mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent); }
    .tape-track { display: inline-flex; white-space: nowrap; padding: 9px 0;
                  animation: tape-scroll 36s linear infinite; will-change: transform; }
    .tape-wrap:hover .tape-track { animation-play-state: paused; }
    @keyframes tape-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
    @media (prefers-reduced-motion: reduce) { .tape-track { animation: none; } }
    .t-item { padding: 1px 20px; border-right: 1px solid var(--line); font-size: .86rem; }
    .t-item b { font-weight: 700; margin-right: 7px; letter-spacing: .3px; }
    .t-up { color: var(--up); font-weight: 600; }
    .t-dn { color: var(--down); font-weight: 600; }
    .t-flat { opacity: .55; }

    .sec { display: flex; align-items: center; gap: .6rem; margin: 1.1rem 0 .55rem 0;
           padding-bottom: .5rem; border-bottom: 1px solid var(--line); }
    .sec-ic { width: 30px; height: 30px; border-radius: 9px; flex: 0 0 auto;
              background: linear-gradient(135deg, var(--accent), #7e57c2);
              display: inline-flex; align-items: center; justify-content: center; font-size: 15px; }
    .sec-t { font-size: 1.06rem; font-weight: 700; letter-spacing: .2px; }
    .sec-h { opacity: .55; font-size: .8rem; margin-left: auto; }

    div[data-testid="stMetric"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px 16px 10px 16px;
        box-shadow: var(--card-shadow);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        transition: transform .16s ease, box-shadow .16s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: var(--card-glow); }
    .livedot { width: 9px; height: 9px; border-radius: 50%; background: #2ebd85;
               display: inline-block; margin-right: 8px; vertical-align: 1px;
               box-shadow: 0 0 0 0 rgba(46,189,133,.55); animation: pulse 1.8s infinite; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(46,189,133,.55); }
                       70% { box-shadow: 0 0 0 9px rgba(46,189,133,0); }
                       100% { box-shadow: 0 0 0 0 rgba(46,189,133,0); } }
    @media (prefers-reduced-motion: reduce) { .livedot { animation: none; } }
    div[data-testid="stMetricLabel"] p { font-size: .8rem; opacity: .7; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.42rem; font-weight: 700; }

    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--tab);
        border-radius: 10px 10px 0 0;
        padding: 7px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: var(--tab-active); box-shadow: inset 0 -2px 0 var(--accent); }

    [data-testid="stSidebar"] hr { margin: .85rem 0; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: .2rem; }
    .side-head { font-size: .72rem; font-weight: 700; letter-spacing: 1.1px; text-transform: uppercase;
                 opacity: .5; margin: 1rem 0 .35rem 0; }

    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input { border-radius: 10px; }
    [data-testid="stExpander"] { border-radius: 12px; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
    div[data-testid="stInfo"], div[data-testid="stSuccess"], div[data-testid="stError"], div[data-testid="stWarning"] { border-radius: 12px; }
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] { border-radius: 10px; font-weight: 600; }
    [data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, var(--accent), var(--accent2));
        border: none; box-shadow: 0 6px 18px var(--accent-glow);
        transition: transform .12s ease, box-shadow .12s ease, filter .12s ease; }
    [data-testid="stBaseButton-primary"]:hover { transform: translateY(-1px); filter: brightness(1.08);
        box-shadow: 0 9px 22px var(--accent-glow); }
    .sec-ic { box-shadow: 0 4px 14px rgba(126,87,194,.4); }
    .logo { animation: logoglow 4s ease-in-out infinite; }
    @keyframes logoglow { 0%,100% { box-shadow: 0 8px 22px rgba(38,166,154,.35); }
                          50% { box-shadow: 0 8px 28px rgba(126,87,194,.5); } }
    @media (prefers-reduced-motion: reduce) { .logo { animation: none; } }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-thumb { background: rgba(140,140,150,.35); border-radius: 8px; }

    .foot { margin-top: 1.6rem; padding: .8rem 1.1rem; border-radius: 12px; font-size: .78rem;
            opacity: .75; border: 1px dashed var(--line); }

    [data-testid="stSidebar"] { background: var(--side) !important; border-right: 1px solid var(--line); }
    [data-testid="stSidebarUserContent"] { padding-top: .5rem; }
    [data-testid="stSidebarUserContent"]::before { content: ""; display: block; height: 3px;
        border-radius: 99px; background: linear-gradient(90deg, var(--accent), #7e57c2);
        margin: 0 .2rem .7rem .2rem; }
    [data-testid="stSidebar"] h1 { font-size: 1.08rem !important; font-weight: 800; letter-spacing: .3px; }
    [data-testid="stSidebar"] h3 { font-size: .72rem !important; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1.3px; opacity: .58; margin-top: .5rem; }
    [data-testid="stSidebar"] hr { margin: .7rem 0; }
    [data-testid="stSidebar"] [role="radio"][aria-checked="true"],
    [data-testid="stSidebar"] [role="radiogroup"] [aria-checked="true"] {
        background: var(--accent-soft); border-radius: 8px; }
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background: transparent; border: 1px solid var(--line); border-radius: 10px; }
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover { border-color: var(--accent); }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div { border-radius: 10px; }
    [data-testid="stSidebar"] span[data-baseweb="tag"] { border-radius: 8px; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { background: transparent; }
    div[data-testid="stMetric"] { background: transparent; border: none; }
    div[data-testid="stMetricValue"] { color: var(--metric-fg) !important; }
    div[data-testid="stMetricDelta"] { color: var(--metric-fg) !important; }
    div[data-testid="stMetricLabel"] p { opacity: .85; }
    span[data-baseweb="tag"],
    div[data-baseweb="tag"],
    [data-testid="stMultiselect"] span[data-baseweb="tag"],
    [data-testid="stMultiselect"] div[data-baseweb="tag"] {
        background: var(--tag-bg) !important;
        color: var(--tag-fg) !important;
        border: 1px solid var(--tag-line) !important;
    }
    div[data-testid="stSelectbox"] {
        background: var(--widget-bg);
        border: 1px solid var(--widget-line);
        border-radius: var(--ms-radius);
    }
    div[data-testid="stSelectbox"] > div > div { background: var(--widget-bg); color: var(--widget-fg); }
    div[data-baseweb="select"] > div { background: var(--widget-bg); color: var(--widget-fg); }
    div[data-baseweb="menu"] { background: var(--menu-bg); color: var(--widget-fg); }
    div[data-testid="stMultiselect"] {
        background: var(--widget-bg) !important;
        border: 1px solid var(--widget-line) !important;
        border-radius: var(--ms-radius);
        color: var(--widget-fg) !important;
    }
    div[data-testid="stMultiselect"] > div {
        background: var(--menu-bg) !important;
        color: var(--widget-fg) !important;
    }
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input {
        background: var(--widget-bg);
        color: var(--widget-fg);
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--widget-line); }
    div[data-testid="stDataFrame"] thead tr th {
        background: var(--dash-head-bg) !important;
        color: var(--dash-head-fg) !important;
        border-bottom: 1px solid var(--widget-line);
    }
    div[data-testid="stDataFrame"] tbody tr { background: var(--dash-row-bg); color: var(--dash-row-fg); }
    .stMarkdown code, code, [data-testid="stMarkdown"] code {
        background: var(--code-bg) !important;
        color: var(--code-fg) !important;
        border: 1px solid var(--code-line) !important;
    }
    .tape-wrap { background: var(--tape-bg) !important; border-color: var(--tape-line) !important; }
    .t-item { border-right-color: var(--tape-line) !important; }
    .t-item b { color: var(--tape-tick) !important; }
    .hero-sub { opacity: .85; }
    .clock { opacity: .75; }
    .t-flat { opacity: .75; }
    .sec-h { opacity: .8; }
    .side-head { opacity: .75; }
    [data-testid="stSidebar"] h3 { opacity: .8; }
    [data-testid="stSidebar"] .stMarkdown p { opacity: .85; }
    [data-testid="stSidebar"] small { opacity: .8; }
    .foot { opacity: .85; }
    div[data-testid="stAppDeployButton"] { opacity: 1 !important; }
    div[data-testid="stAppDeployButton"] a,
    div[data-testid="stAppDeployButton"] button,
    div[data-testid="stAppDeployButton"] span {
        color: var(--title-fallback) !important;
        opacity: 1 !important;
    }
    .mcard {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: var(--card-glow);
        transition: transform .15s ease, border-color .15s ease;
    }
    .mrow { display: flex; gap: 14px; align-items: stretch; }
    .mrow .mcard { flex: 1 1 0; min-width: 0; }
    @media (max-width: 980px) { .mrow { flex-wrap: wrap; } .mrow .mcard { flex: 1 1 210px; } }
    .mcard:hover { transform: translateY(-2px); border-color: rgba(38,166,154,.35); }
    .mtop { display: flex; align-items: center; gap: 12px; }
    .mchip {
        width: 34px; height: 34px; border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        background: var(--accent-soft); color: var(--accent);
        font-weight: 700; font-size: .82rem;
    }
    .mlogo {
        width: 34px; height: 34px; border-radius: 9px;
        object-fit: contain; background: #ffffff;
        border: 1px solid var(--line); padding: 3px; box-sizing: border-box;
    }
    .msym { font-family: "Sora", sans-serif; font-weight: 800; font-size: 1.02rem; color: var(--title-fallback); }
    .msub { font-size: .74rem; opacity: .55; }
    .mprice { font-family: "Sora", sans-serif; font-weight: 800; font-size: 1.55rem; color: var(--title-fallback); margin-top: 4px; }
    .mprice small { font-size: .78rem; font-weight: 600; opacity: .6; }
    .mdelta {
        display: inline-flex; align-items: center; gap: 4px;
        margin-top: 8px; padding: 3px 10px;
        border-radius: 999px; font-size: .78rem; font-weight: 700;
    }
    .mdelta.up { background: rgba(46,189,133,.14); color: var(--up); }
    .mdelta.dn { background: rgba(246,70,85,.14); color: var(--down); }
    .mdelta.flat { background: var(--tab); color: var(--title-fallback); }
    .mcard-spark { width: 100%; height: 40px; margin-top: 12px; display: block; }
    .mlabel { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; opacity: .55; margin-bottom: 6px; }
    .mval { font-size: 1.02rem; font-weight: 700; color: var(--title-fallback); }
    .mval small { font-size: .78rem; opacity: .6; }
    .chead-wrap {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 14px;
    }
    .chead { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
    .chsym { font-family: "Sora", sans-serif; font-weight: 800; font-size: 1.05rem; color: var(--title-fallback); }
    .chname { font-size: .8rem; opacity: .6; }
    .chprice { font-family: "Sora", sans-serif; font-weight: 800; font-size: 1.05rem; color: var(--title-fallback); }
    .chprice small { font-size: .74rem; font-weight: 600; opacity: .6; }
    .chchg {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 9px; border-radius: 999px;
        font-size: .74rem; font-weight: 700;
    }
    .chchg.up { background: rgba(46,189,133,.14); color: var(--up); }
    .chchg.dn { background: rgba(246,70,85,.14); color: var(--down); }
    .chchg.flat { background: var(--tab); color: var(--title-fallback); }
    .chmeta { margin-left: auto; font-size: .74rem; opacity: .5; }
    .clegend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .lgd {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 3px 10px; border-radius: 999px;
        background: var(--tab); border: 1px solid var(--line);
        font-size: .74rem; color: var(--title-fallback);
    }
    .lgd-dot { width: 9px; height: 9px; border-radius: 999px; display: inline-block; }
    .sev {
        background: var(--card); border: 1px solid var(--line);
        border-radius: 12px; padding: 14px 16px;
        box-shadow: var(--card-glow);
        border-left-width: 3px;
    }
    .sev.up { border-left-color: var(--up); }
    .sev.dn { border-left-color: var(--down); }
    .sev.flat { border-left-color: var(--accent); }
    .sev-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
    .sev-ic { font-size: 1.1rem; }
    .sev-count { font-family: "Sora", sans-serif; font-weight: 800; font-size: 1.5rem; color: var(--title-fallback); }
    .sev-label { font-size: .85rem; font-weight: 700; color: var(--title-fallback); }
    .sev-sub { font-size: .74rem; opacity: .6; margin-top: 2px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

CONFIG_TOML = Path(__file__).resolve().parent / ".streamlit" / "config.toml"

THEME_COLORS = {
    "dark": {
        "base": "dark",
        "primaryColor": "#26a69a",
        "backgroundColor": "#070b14",
        "secondaryBackgroundColor": "#0d1526",
        "textColor": "#e8eaed",
    },
    "light": {
        "base": "light",
        "primaryColor": "#00897b",
        "backgroundColor": "#ffffff",
        "secondaryBackgroundColor": "#f0f2f6",
        "textColor": "#1a1d21",
    },
}


def get_config_base() -> str:
    section = None
    try:
        for line in CONFIG_TOML.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                section = s[1:-1]
            elif section == "theme" and s.startswith("base"):
                return s.split("=", 1)[1].strip().strip("'\"")
    except Exception:
        pass
    return "dark"


def _theme_sync_error(msg: str) -> None:
    print(msg, flush=True)
    try:
        st.error(msg)
    except Exception:
        pass


def apply_theme_mode(mode: str) -> None:
    colors = THEME_COLORS.get(mode, THEME_COLORS["dark"])
    try:
        lines = CONFIG_TOML.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        _theme_sync_error(f"Could not read config.toml for theme sync ({exc}); theme may not persist.")
        return
    section = None
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1]
            out.append(line)
            continue
        if section == "theme":
            replaced = False
            for key, val in colors.items():
                if s.startswith(key):
                    out.append(f'{key} = "{val}"')
                    replaced = True
                    break
            if not replaced:
                out.append(line)
        else:
            out.append(line)
    try:
        CONFIG_TOML.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception as exc:
        _theme_sync_error(f"Could not write config.toml for theme sync ({exc}); theme may not persist.")
        return
    if get_config_base() != mode:
        _theme_sync_error(
            f"Theme sync verification failed: config base is '{get_config_base()}', expected '{mode}'."
        )


saved_theme = db.get_setting("theme_mode", "dark")
if saved_theme not in ("dark", "light"):
    saved_theme = "dark"
if get_config_base() != saved_theme:
    apply_theme_mode(saved_theme)

if saved_theme == "light":
    st.markdown(
        """
        <style>
            .stApp {
                --card: #ffffff;
                --line: rgba(15,23,42,.12);
                --tab: rgba(15,23,42,.05);
                --tab-active: rgba(0,137,123,.12);
                --accent: #00897b;
                --accent2: #00b386;
                --accent-glow: rgba(0,137,123,.28);
                --up: #0e9f6e;
                --down: #e02424;
                --tape: rgba(15,23,42,.03);
                --card-shadow: 0 2px 10px rgba(15,23,42,.06);
                --card-glow: 0 8px 20px rgba(15,23,42,.1);
                --side: #f4f6f9;
                --accent-soft: rgba(0,137,123,.13);
                --pagebg: radial-gradient(1000px 480px at 12% -5%, rgba(0,137,123,.07), transparent 60%),
                          radial-gradient(900px 480px at 88% -2%, rgba(109,91,208,.07), transparent 60%),
                          #fbfcfe;
                --title-grad: linear-gradient(92deg, #0f172a 10%, #00897b 55%, #6d5bd0 95%);
                --title-fallback: #0f172a;
            }
            .stApp {
                --metric-fg: #1a1d21;
                --widget-fg: #1a1d21;
                --dash-head-fg: #1a1d21;
                --dash-row-fg: #1a1d21;
                --tag-fg: #1a1d21;
                --code-fg: #1a1d21;
                --tape-tick: #1a1d21;
                --widget-bg: #ffffff;
                --menu-bg: #ffffff;
                --dash-row-bg: #ffffff;
                --widget-line: rgba(0,0,0,.15);
                --ms-radius: 4px;
                --tag-bg: #e3eaf2;
                --tag-line: rgba(0,0,0,.12);
                --code-bg: #e3eaf2;
                --code-line: rgba(0,0,0,.12);
                --dash-head-bg: #f8f9fa;
                --tape-bg: #f1f5f9;
                --tape-line: rgba(15,23,42,.14);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
            .stApp {
                --card: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.018));
                --line: rgba(255,255,255,.1);
                --tab: rgba(255,255,255,.04);
                --tab-active: rgba(38,166,154,.16);
                --accent: #26a69a;
                --accent2: #00c389;
                --accent-glow: rgba(38,166,154,.35);
                --up: #00e5a0;
                --down: #ff4d67;
                --tape: rgba(255,255,255,.03);
                --card-shadow: none;
                --card-glow: 0 10px 26px rgba(0,0,0,.45);
                --side: linear-gradient(180deg, #090e1a 0%, #0b1322 100%);
                --accent-soft: rgba(38,166,154,.18);
                --pagebg: radial-gradient(1100px 520px at 12% -5%, rgba(38,166,154,.09), transparent 60%),
                          radial-gradient(950px 500px at 88% -2%, rgba(126,87,194,.1), transparent 60%),
                          radial-gradient(700px 600px at 50% 110%, rgba(0,195,137,.05), transparent 60%),
                          #070b14;
                --title-grad: linear-gradient(92deg, #ffffff 20%, #7de8d3 58%, #b79df5 95%);
                --title-fallback: #ffffff;
                --metric-fg: #e8eaed;
                --metric-fg-soft: #e8eaed;
                --widget-fg: #e8eaed;
                --dash-head-fg: #e8eaed;
                --dash-row-fg: #e8eaed;
                --tag-fg: #e8eaed;
                --code-fg: #e8eaed;
                --tape-tick: #e8eaed;
                --widget-bg: #0d1526;
                --menu-bg: #0d1526;
                --dash-row-bg: transparent;
                --widget-line: rgba(255,255,255,.14);
                --ms-radius: 4px;
                --tag-bg: rgba(255,255,255,.12);
                --tag-line: rgba(255,255,255,.14);
                --code-bg: rgba(255,255,255,.08);
                --code-line: rgba(255,255,255,.12);
                --dash-head-bg: rgba(255,255,255,.06);
                --tape-bg: rgba(255,255,255,.04);
                --tape-line: rgba(255,255,255,.14);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def egx_market_status() -> tuple[pd.Timestamp, bool, str]:
    now = pd.Timestamp.now(tz="Africa/Cairo")
    wd = now.weekday()
    trading_day = wd in (6, 0, 1, 2, 3)
    minutes = now.hour * 60 + now.minute
    pre_open = trading_day and 9 * 60 <= minutes < 10 * 60
    is_open = trading_day and (10 * 60) <= minutes < (14 * 60 + 30)
    if is_open:
        state = "🟢 MARKET OPEN"
    elif pre_open:
        state = "🟡 PRE-OPEN"
    else:
        next_day = "Sunday" if wd in (3, 4, 5) else "tomorrow" if trading_day else "Sunday"
        state = f"🔴 CLOSED · opens {next_day} 10:00"
    return now, is_open, state


now_cairo, market_is_open, market_badge = egx_market_status()

if market_is_open:
    badge_inner = f"<span class='livedot'></span>{market_badge.replace('🟢 ', '')}"
else:
    badge_inner = market_badge

if "PRE-OPEN" in market_badge:
    pill_fg, pill_bg, pill_bd = "#f0b90b", "rgba(240,185,11,.13)", "rgba(240,185,11,.45)"
elif "OPEN" in market_badge and "CLOSED" not in market_badge:
    pill_fg, pill_bg, pill_bd = "#2ebd85", "rgba(46,189,133,.14)", "rgba(46,189,133,.45)"
else:
    pill_fg, pill_bg, pill_bd = "#f6465d", "rgba(246,70,85,.12)", "rgba(246,70,85,.4)"

def tape_html(quotes_df: pd.DataFrame) -> str:
    import html as _html

    if quotes_df is None or quotes_df.empty:
        return ""
    items = []
    for _, r in quotes_df.iterrows():
        sym = _html.escape(str(r.get("ticker", "")))
        px = r.get("close")
        chg = r.get("change")
        if pd.isna(px):
            continue
        if pd.notna(chg) and chg > 0:
            tail = f"<span class='t-up'>+{chg:.2f}%</span>"
        elif pd.notna(chg) and chg < 0:
            tail = f"<span class='t-dn'>{chg:.2f}%</span>"
        else:
            tail = "<span class='t-flat'>0.00%</span>"
        items.append(f"<span class='t-item'><b>{sym}</b>{px:,.2f} {tail}</span>")
    if not items:
        return ""
    seq = "".join(items)
    return f"<div class='tape-wrap'><div class='tape-track'>{seq}{seq}</div></div>"


st.markdown(
    f"""
    <div class="hero">
      <div class="hero-left">
        <div class="logo">📈</div>
        <div>
          <div class="hero-title">EGX Stock Tracker</div>
          <div class="hero-sub"><b>Live quotes</b> · Mubasher + TradingView &nbsp;—&nbsp; <b>History &amp; indicators</b> · Yahoo Finance &nbsp;—&nbsp; <b>News</b> · Google News</div>
        </div>
      </div>
      <div class="hero-right">
        <span style="background:{pill_bg};color:{pill_fg};border:1px solid {pill_bd};
                     padding:7px 16px;border-radius:999px;font-weight:650;font-size:.98rem;
                     white-space:nowrap;display:inline-block;">
          {badge_inner}
        </span>
        <div class="clock">Cairo time {now_cairo:%a %H:%M}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=45, show_spinner=False)
def cached_quotes(provider: str, symbols: tuple) -> pd.DataFrame:
    syms = [s for s in dict.fromkeys(symbols) if s]
    if provider == "Mubasher (live)":
        try:
            df = mubasher.get_quotes(syms)
        except Exception:
            df = pd.DataFrame()
        priced = df["close"].apply(lambda v: isinstance(v, (int, float)) and not pd.isna(v)) if not df.empty else pd.Series(dtype=bool)
        got = set(df.loc[priced, "ticker"].dropna()) if not df.empty else set()
        missing = [s for s in syms if s not in got]
        if missing:
            tv_part = live.get_quotes(missing)
            df = pd.concat([df, tv_part], ignore_index=True) if not df.empty else tv_part
        if not df.empty:
            return df
    return live.get_quotes(syms)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_history(symbol: str, period: str, name_hint: str = "") -> pd.DataFrame:
    return fetch_history(symbol, period=period, name_hint=name_hint or None)


def symbol_name(sym: str) -> str:
    return EGX_TICKERS.get(sym) or (universe_desc.get(sym) or "")


def upsert_today_ohlcv(quotes_df: pd.DataFrame) -> None:
    """Persist today's live OHLC per symbol so history grows even where Yahoo has none."""
    if quotes_df is None or quotes_df.empty or "open" not in quotes_df.columns:
        return
    now_cairo = pd.Timestamp.now(tz="Africa/Cairo")
    if now_cairo.weekday() in (4, 5):
        return
    today = now_cairo.normalize().tz_localize(None)
    for _, r in quotes_df.iterrows():
        if pd.isna(r.get("close")) or pd.isna(r.get("open")):
            continue
        row = pd.DataFrame(
            {
                "Open": [float(r["open"])],
                "High": [float(r["high"]) if pd.notna(r.get("high")) else float(r["close"])],
                "Low": [float(r["low"]) if pd.notna(r.get("low")) else float(r["close"])],
                "Close": [float(r["close"])],
                "Volume": [float(r["volume"]) if pd.notna(r.get("volume")) else 0.0],
            },
            index=[today],
        )
        try:
            db.save_history(str(r["ticker"]), row)
        except Exception:
            pass


def get_history_for_alerts(symbol: str) -> pd.DataFrame | None:
    df = cached_history(symbol, "6mo")
    return None if df.empty else df


def fmt_pct(x: float) -> str:
    return f"{x:+,.2f}%"


def _restore_index(options: list, saved: str) -> int:
    try:
        return options.index(saved) if saved in options else 0
    except Exception:
        return 0


def _chg_color(v):
    up, dn = ("#00e5a0", "#ff4d67") if saved_theme == "dark" else ("#0e9f6e", "#e02424")
    if not isinstance(v, (int, float)) or pd.isna(v):
        return ""
    if v > 0:
        return f"color:{up};font-weight:600"
    if v < 0:
        return f"color:{dn};font-weight:600"
    return "color:#9aa0a6"


@st.cache_data(ttl=900, show_spinner=False)
def cached_news(symbol: str, name: str) -> pd.DataFrame:
    return news.collect_news(symbol, name)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_universe() -> pd.DataFrame:
    return live.get_all_symbols()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_mub_tickers() -> set:
    try:
        snap = mubasher.fetch_market_snapshot()
        return set(snap["ticker"].dropna().tolist()) if not snap.empty else set()
    except Exception:
        return set()


@st.cache_data(ttl=300, show_spinner=False)
def cached_market_news() -> pd.DataFrame:
    return news.market_news()


universe = cached_universe()
universe_desc = dict(zip(universe["ticker"], universe["description"].fillna("")))
universe_logo = {
    r["ticker"]: live.logo_url(r.get("logoid"))
    for _, r in universe.iterrows()
}


custom_syms = db.list_custom_symbols()
all_options = list(dict.fromkeys(list(EGX_TICKERS.keys()) + custom_syms))

with st.sidebar:
    st.header("Settings")
    st.subheader("Appearance")
    picked_theme = st.segmented_control(
        "Theme",
        options=["Dark", "Light"],
        default=saved_theme.capitalize(),
        label_visibility="collapsed",
        key="theme_selector",
    )
    new_theme = (picked_theme or saved_theme).lower()
    if new_theme != saved_theme:
        db.set_setting("theme_mode", new_theme)
        apply_theme_mode(new_theme)
        with st.spinner("Applying theme..."):
            time.sleep(2.5)
        st.rerun()
    price_source = st.segmented_control(
        "Price source",
        options=["Mubasher (live)", "TradingView (delayed)"],
        default="Mubasher (live)",
        help="Mubasher is Mubasher's public web feed with per-stock update times. TradingView is the fallback (15 min delayed).",
    )
    if not price_source:
        price_source = "Mubasher (live)"
    watchlist = st.multiselect(
        "Watchlist",
        options=all_options,
        default=list(dict.fromkeys([s for s in DEFAULT_WATCHLIST if s in all_options] + custom_syms)),
        format_func=lambda s: f"{s} - {EGX_TICKERS.get(s, s)}",
    )

    st.divider()
    st.subheader("➕ Add stock")
    mub_tickers: set = set()
    live_options: list = []
    delayed_only: list = []
    try:
        mub_tickers = cached_mub_tickers()
    except Exception:
        mub_tickers = set()
    if not universe.empty:
        live_options = sorted(t for t in universe_desc.keys() if not mub_tickers or t in mub_tickers)
        delayed_only = sorted(t for t in universe_desc.keys() if mub_tickers and t not in mub_tickers)
        pick_q = st.text_input(
            f"Search {len(live_options)} stocks with live prices",
            placeholder="Type a name or symbol...",
        ).strip().lower()
        pick_tbl = pd.DataFrame(
            {
                "Logo": [universe_logo.get(t, "") for t in live_options],
                "Symbol": live_options,
                "Company": [(universe_desc.get(t) or "")[:48] for t in live_options],
            }
        )
        if pick_q:
            pick_tbl = pick_tbl[
                pick_tbl["Symbol"].str.lower().str.contains(pick_q, regex=False)
                | pick_tbl["Company"].str.lower().str.contains(pick_q, regex=False)
            ]
        pick_tbl = pick_tbl.sort_values("Symbol").reset_index(drop=True)
        pick_rows = st.dataframe(
            pick_tbl.head(120),
            column_config={
                "Logo": st.column_config.ImageColumn("Logo", width="small"),
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Company": st.column_config.TextColumn("Company", width="medium"),
            },
            selection_mode="single-row",
            on_select="rerun",
            key="stock_picker",
            hide_index=True,
            use_container_width=True,
            height=260,
        )
        psym = None
        if pick_rows.selection.rows:
            psym = pick_tbl.iloc[pick_rows.selection.rows[0]]["Symbol"]
        if psym:
            pv1, pv2 = st.columns([1, 3])
            logo = universe_logo.get(psym, "")
            if logo:
                pv1.image(logo, width=44)
            pq = cached_quotes(price_source, (psym,))
            if not pq.empty and pd.notna(pq.iloc[0]["close"]):
                pv2.markdown(f"**{psym}**  \n{pq.iloc[0]['close']:,.2f} EGP")
            else:
                pv2.markdown(f"**{psym}**")
            if st.button("Add to watchlist", use_container_width=True):
                if psym in all_options:
                    st.info(f"{psym} is already in your list.")
                else:
                    db.add_custom_symbol(psym)
                    st.success(f"{psym} added to watchlist.")
                    st.rerun()
    else:
        new_sym = st.text_input("EGX ticker (e.g. ETEL)", key="add_symbol").strip().upper()
        if st.button("Add to watchlist", use_container_width=True):
            if not new_sym:
                st.warning("Enter a ticker first.")
            elif new_sym in all_options:
                st.info(f"{new_sym} is already in your list.")
            else:
                test = live.get_quotes([new_sym])
                if test.empty or (not test.empty and pd.isna(test.iloc[0].get("close"))):
                    st.error(f"'{new_sym}' not found on EGX. Check the symbol.")
                else:
                    db.add_custom_symbol(new_sym)
                    px = test.iloc[0]["close"]
                    st.success(f"{new_sym} added - last {px:,.2f} EGP.")
                    st.rerun()
    if custom_syms:
        st.caption("Your added symbols:")
        for csym in custom_syms:
            rc1, rc2 = st.columns([4, 1])
            rc1.markdown(f"`{csym}`")
            if rc2.button("✕", key=f"rm_{csym}"):
                db.delete_custom_symbol(csym)
                st.rerun()
    if not universe.empty and mub_tickers:
        with st.expander(f"⚠️ {len(delayed_only)} stocks without live prices (delayed only)"):
            st.caption("These EGX names are not in Mubasher's feed - quotes come from TradingView (~15 min delayed).")
            st.code(", ".join(delayed_only), language=None)
    st.divider()
    movers_sort = st.segmented_control("Market movers", options=["Gainers", "Losers", "Volume"], default="Gainers")
    if not movers_sort:
        movers_sort = "Gainers"

    with st.expander("🖥 Display & indicators", expanded=False):
        period = st.select_slider("History period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
        show_sma = st.checkbox("SMA 20/50/200", value=True)
        show_ema = st.checkbox("EMA 20", value=False)
        show_bb = st.checkbox("Bollinger Bands", value=False)
        show_rsi = st.checkbox("RSI 14", value=True)
        show_macd = st.checkbox("MACD", value=True)
        show_volume = st.checkbox("Volume", value=True)
        chart_style = st.segmented_control(
            "Chart style",
            options=["TradingView", "Technical"],
            default="TradingView",
            help="TradingView embeds the official Advanced Chart widget (EGX:SYMBOL). Technical renders the built-in Plotly candlestick chart with SMA/EMA/BB/RSI/MACD overlays.",
        )
        if not chart_style:
            chart_style = "TradingView"

    st.divider()
    st.subheader("Refresh")
    auto_refresh = st.checkbox("Auto-refresh every 60s", value=False)
    if auto_refresh:
        st_autorefresh(interval=60_000, key="auto_refresh")
    if st.button("🔄 Refresh now", use_container_width=True):
        cached_quotes.clear()
        st.rerun()

if not watchlist:
    st.info("Select at least one ticker from the sidebar.")
    st.stop()

quotes = cached_quotes(price_source, tuple(watchlist))
quote_by_ticker = {r["ticker"]: r for _, r in quotes.iterrows()} if not quotes.empty else {}
upsert_today_ohlcv(quotes)

tape = tape_html(quotes)
if tape:
    st.markdown(tape, unsafe_allow_html=True)


def h2(icon: str, title: str, hint: str = "") -> None:
    import html as _html

    hint_html = f"<span class='sec-h'>{_html.escape(hint)}</span>" if hint else ""
    st.markdown(
        f"<div class='sec'><span class='sec-ic'>{icon}</span>"
        f"<span class='sec-t'>{_html.escape(title)}</span>{hint_html}</div>",
        unsafe_allow_html=True,
    )


def _spark_svg(vals) -> str:
    pts = [v for v in vals if pd.notna(v)]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    rng = hi - lo or 1.0
    coords = [f"{(i / (len(pts) - 1)) * 100:.2f},{(30 - ((v - lo) / rng) * 30):.2f}" for i, v in enumerate(pts)]
    color = "var(--up)" if pts[-1] >= pts[0] else "var(--down)"
    return (
        f"<svg class='mcard-spark' viewBox='0 0 100 30' preserveAspectRatio='none'>"
        f"<polyline points='{','.join(coords)}' fill='none' stroke='{color}' "
        f"stroke-width='2' vector-effect='non-scaling-stroke'/></svg>"
    )


def _sev_card(icon: str, count, label: str, sub: str, cls: str) -> str:
    import html as _html

    return (
        f"<div class='sev {cls}'>"
        f"<div class='sev-top'>"
        f"<span class='sev-ic'>{icon}</span>"
        f"<span class='sev-count'>{count}</span>"
        f"</div>"
        f"<div class='sev-label'>{_html.escape(label)}</div>"
        f"<div class='sev-sub'>{_html.escape(sub)}</div>"
        f"</div>"
    )


@st.cache_data(ttl=1800, show_spinner=False)
def cached_sparks(symbols: tuple) -> dict:
    import yfinance as yf

    syms = [s for s in dict.fromkeys(symbols) if s]
    if not syms:
        return {}
    try:
        raw = yf.download(
            [f"{s}.CA" for s in syms],
            period="1mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            group_by="ticker",
        )
    except Exception:
        return {}
    out = {}
    try:
        for s in syms:
            key = f"{s}.CA"
            closes = raw[key]["Close"]
            vals = [float(v) for v in closes.dropna().tail(22).tolist()]
            if vals:
                out[s] = vals
    except Exception:
        pass
    return out


@st.cache_data(ttl=120, show_spinner=False)
def cached_movers(sort_field: str, ascending: bool, limit: int) -> pd.DataFrame:
    try:
        return live.scan_market(sort_by=sort_field, ascending=ascending, limit=limit)
    except Exception:
        return pd.DataFrame()


def _movers_mini(df: pd.DataFrame):
    m = df[["ticker", "close", "change", "volume"]].copy()
    m["Chg %"] = m["change"].map(lambda v: f"{v:+.2f}%" if pd.notna(v) else "—")
    m["Logo"] = [universe_logo.get(t, "") for t in m["ticker"]]
    return (
        m[["Logo", "ticker", "close", "Chg %", "volume"]]
        .style.format({"close": "{:,.2f}", "volume": "{:,.0f}"})
        .map(_chg_color, subset=["Chg %"])
    )

active_alerts = db.list_alerts(active_only=True)
new_triggers = engine.evaluate(active_alerts, quotes, get_history_for_alerts)
for t in new_triggers:
    st.toast(engine.describe(t), icon="🔔")
    try:
        winsound.Beep(1200, 250)
        winsound.Beep(1600, 350)
    except Exception:
        pass

tab_chart, tab_signals, tab_alerts, tab_portfolio, tab_backtest, tab_news = st.tabs(
    ["📊 Chart", "🎯 Signals & Levels", "🔔 Alerts", "💼 Portfolio", "🧪 Backtest", "📰 Market News"]
)

with tab_chart:
    pick_c, _pad_c = st.columns([1, 2])
    with pick_c:
        wl_tbl = pd.DataFrame(
            {
                "Logo": [universe_logo.get(t, "") for t in watchlist],
                "Symbol": watchlist,
                "Company": [EGX_TICKERS.get(t, t)[:48] for t in watchlist],
            }
        )
        pick_rows = st.dataframe(
            wl_tbl,
            column_config={
                "Logo": st.column_config.ImageColumn("Logo", width="small"),
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Company": st.column_config.TextColumn("Company", width="medium"),
            },
            selection_mode="single-row",
            on_select="rerun",
            key="chart_ticker_pick",
            hide_index=True,
            use_container_width=True,
            height=min(45 + 35 * max(len(wl_tbl), 1), 280),
        )
        _rows = pick_rows.selection.rows
        if _rows:
            selected = wl_tbl.iloc[_rows[0]]["Symbol"]
        else:
            saved = db.get_setting("chart_ticker")
            selected = saved if saved in watchlist else (watchlist[0] if watchlist else None)
    if selected:
        db.set_setting("chart_ticker", selected)

    q = quote_by_ticker.get(selected)
    if q is not None and pd.notna(q["close"]):
        c1, c2, c3, c4 = st.columns(4)
        chg_abs = q["change_abs"]
        chg_pct = q["change"]
        if pd.notna(chg_pct):
            chg_cls = "up" if (chg_abs or 0) >= 0 else "dn"
            chg_arrow = "▲" if (chg_abs or 0) >= 0 else "▼"
            chg_txt = f"{chg_abs:+.2f} ({chg_pct:+.2f}%)"
        else:
            chg_cls, chg_arrow, chg_txt = "flat", "●", "—"
        if pd.notna(q["low"]) and pd.notna(q["high"]):
            day_span = f"{q['low']:,.2f} – {q['high']:,.2f}"
        else:
            day_span = "—"
        spark = _spark_svg(cached_sparks((selected,)).get(selected, []))
        vol = q["volume"]
        vol_txt = f"{vol:,.0f}" if pd.notna(vol) else "—"
        mc = q["market_cap_basic"]
        mc_txt = f"{mc / 1e9:,.1f}<small>B EGP</small>" if pd.notna(mc) else "—"
        _html = __import__("html")
        logo_now = universe_logo.get(selected, "")
        if logo_now:
            chip_html = (
                f"<span class='mchip'><img class='mlogo' src='{_html.escape(logo_now, quote=True)}' alt='{_html.escape(selected)}'></span>"
            )
        else:
            chip_html = f"<span class='mchip'>{_html.escape(selected[:2])}</span>"
        cards = [
            (
                f"<div class='mcard'>"
                f"<div class='mtop'>{chip_html}"
                f"<span class='msym'>{_html.escape(selected)}</span></div>"
                f"<div class='mprice'>{q['close']:,.2f}<small>EGP</small></div>"
                f"<div class='mdelta {chg_cls}'>{chg_arrow} {_html.escape(chg_txt)}</div>"
                f"{spark}</div>"
            ),
            (
                f"<div class='mcard'>"
                f"<div class='mtop'><span class='mchip'>↔</span>"
                f"<span class='msym'>Day range</span></div>"
                f"<div class='mval'>{day_span}</div></div>"
            ),
            (
                f"<div class='mcard'>"
                f"<div class='mtop'><span class='mchip'>⚙</span>"
                f"<span class='msym'>Volume</span></div>"
                f"<div class='mval'>{vol_txt}</div></div>"
            ),
            (
                f"<div class='mcard'>"
                f"<div class='mtop'><span class='mchip'>₪</span>"
                f"<span class='msym'>Market cap</span></div>"
                f"<div class='mval'>{mc_txt}</div></div>"
            ),
        ]
        st.markdown(
            "<div class='mrow'>" + "".join(cards) + "</div>",
            unsafe_allow_html=True,
        )

    gainers = cached_movers("change", False, 5)
    losers = cached_movers("change", True, 5)
    if not gainers.empty or not losers.empty:
        h2("🚀", "Top movers", "Biggest gainers and losers across the EGX today")
        gcol, lcol = st.columns(2)
        with gcol:
            st.caption("🟢 Top gainers")
            if not gainers.empty:
                st.dataframe(
                    _movers_mini(gainers),
                    column_config={"Logo": st.column_config.ImageColumn("", width="small")},
                    use_container_width=True,
                    height=250,
                    hide_index=True,
                )
            else:
                st.info("No data right now.")
        with lcol:
            st.caption("🔴 Top losers")
            if not losers.empty:
                st.dataframe(
                    _movers_mini(losers),
                    column_config={"Logo": st.column_config.ImageColumn("", width="small")},
                    use_container_width=True,
                    height=250,
                    hide_index=True,
                )
            else:
                st.info("No data right now.")

    hist = cached_history(selected, period, symbol_name(selected))
    live_last = float(q["close"]) if q is not None and pd.notna(q["close"]) else None
    if not hist.empty and live_last:
        last_hist = float(hist["Close"].iloc[-1])
        if last_hist > 0 and abs(last_hist - live_last) / live_last > 0.25:
            hist = fetch_history(
                selected,
                period=period,
                name_hint=symbol_name(selected),
                live_last=live_last,
            )
        if (
            not hist.empty
            and float(hist["Close"].iloc[-1]) > 0
            and abs(float(hist["Close"].iloc[-1]) - live_last) / live_last > 0.25
        ):
            st.warning(
                f"Yahoo's stored history for {selected} looks out of scale vs the live price "
                f"(history {float(hist['Close'].iloc[-1]):,.2f} vs live {live_last:,.2f}) - "
                f"likely an unadjusted split/corporate action. Chart levels may be indicative only."
            )
    enriched = None
    if hist.empty:
        st.error(
            f"No historical data available for {selected} yet. "
            f"Live prices still work above - the app now records daily candles automatically, "
            f"so a chart will build up over coming sessions."
        )
    elif len(hist) < 15:
        st.warning(f"Not enough data for {selected} ({len(hist)} rows).")
    else:
        enriched = indicators.add_all(hist)
        support, resistance = signals.pivot_levels(enriched)
        import html as _html

        if pd.notna(chg_pct):
            d_cls = "up" if (chg_abs or 0) >= 0 else "dn"
            d_arrow = "▲" if (chg_abs or 0) >= 0 else "▼"
            badge = f"{d_arrow} {chg_abs:+.2f} ({chg_pct:+.2f}%)"
        else:
            d_cls, badge = "flat", "—"
        st.markdown(
            f"<div class='chead-wrap'><div class='chead'>"
            f"<span class='chsym'>{_html.escape(selected)}</span>"
            f"<span class='chname'>{_html.escape(symbol_name(selected))}</span>"
            f"<span class='chprice'>{q['close']:,.2f}<small>EGP</small></span>"
            f"<span class='chchg {d_cls}'>{_html.escape(badge)}</span>"
            f"<span class='chmeta'>{period} · {len(hist)} bars</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    if chart_style == "TradingView" and selected:
        st.components.v1.html(
            advanced_chart_html(tv_symbol(selected), theme=saved_theme, height=680),
            height=700,
            scrolling=False,
        )
    elif enriched is None:
        st.info(
            f"Technical chart needs historical data, which isn't ready for {selected} yet "
            f"({len(hist)} bars). Live prices still work above, and charts build up over "
            f"coming sessions. Switch the chart style to 'TradingView' in the sidebar for "
            f"an interactive chart right now."
        )
    else:
        fig = candlestick_chart(
            enriched,
            selected,
            show_sma=show_sma,
            show_ema=show_ema,
            show_bb=show_bb,
            show_rsi=show_rsi,
            show_macd=show_macd,
            show_volume=show_volume,
            levels=(support, resistance),
            theme=saved_theme,
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOTLY_CONFIG)
        lgds = []
        for tr in fig.data:
            nm = getattr(tr, "name", None)
            if not nm or nm == selected:
                continue
            color = getattr(tr, "line", None)
            color = getattr(color, "color", None) if color is not None else None
            if not isinstance(color, str):
                color = getattr(tr, "marker", None)
                color = getattr(color, "color", None) if color is not None else None
            color = color if isinstance(color, str) else "var(--side)"
            lgds.append(f"<div class='lgd'><span class='lgd-dot' style='background:{color}'></span>{_html.escape(nm)}</div>")
        if lgds:
            st.markdown(f"<div class='clegend'>{''.join(lgds)}</div>", unsafe_allow_html=True)

    st.divider()
    src_note = "Mubasher live feed" if price_source.startswith("Mubasher") else "TradingView (15 min delayed)"
    h2("📋", "Watchlist quotes", f"{len(quotes)} symbols · {src_note}")
    if quotes.empty:
        st.warning("Could not load live quotes right now.")
    else:
        table = quotes[
            ["ticker", "name", "close", "change", "change_abs", "open", "high", "low", "volume", "market_cap_basic"]
        ].copy()
        if "updated_at" in quotes.columns:
            table["updated_at"] = quotes["updated_at"]
        else:
            table["updated_at"] = None
        table = table.set_index("ticker").reindex([t for t in watchlist if t in table.index])
        table = table.rename(
            columns={
                "name": "Name",
                "close": "Last",
                "change": "Chg %",
                "change_abs": "Chg",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "volume": "Volume",
                "market_cap_basic": "Mkt Cap (EGP)",
                "updated_at": "Updated",
            }
        )
        table["Name"] = table["Name"].str.slice(0, 34)
        table.insert(0, "Logo", [universe_logo.get(t, "") for t in table.index])
        sparks = cached_sparks(tuple(table.index.tolist()))
        table["Trend"] = [sparks.get(t, []) for t in table.index]

        st.dataframe(
            table.style.format(
                {
                    "Last": "{:,.2f}",
                    "Chg %": "{:+.2f}",
                    "Chg": "{:+.2f}",
                    "Open": "{:,.2f}",
                    "High": "{:,.2f}",
                    "Low": "{:,.2f}",
                    "Volume": "{:,.0f}",
                    "Mkt Cap (EGP)": "{:,.0f}",
                }
            ).map(_chg_color, subset=["Chg %", "Chg"]),
            column_config={
                "Logo": st.column_config.ImageColumn("", width="small"),
                "Trend": st.column_config.AreaChartColumn("Trend (1M)", width="medium", y_min="auto", y_max="auto"),
            },
            use_container_width=True,
        )
        st.caption(f"Quotes updated: {pd.Timestamp.now():%Y-%m-%d %H:%M:%S} · source: {src_note}.")

with tab_signals:
    sig_symbol = st.selectbox(
        "Ticker",
        watchlist,
        index=_restore_index(watchlist, db.get_setting("signals_ticker")),
        format_func=lambda s: f"{s} - {EGX_TICKERS.get(s, s)}",
        key="signals_ticker",
    )
    if sig_symbol:
        db.set_setting("signals_ticker", sig_symbol)
    sig_hist = cached_history(sig_symbol, period, symbol_name(sig_symbol))
    if sig_hist.empty or len(sig_hist) < 30:
        st.warning("Not enough history to compute signals.")
    else:
        found = signals.detect_signals(sig_hist)
        if not found:
            st.info("No notable signals right now.")
        else:
            dir_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
            sig_df = pd.DataFrame(
                [
                    {
                        "Date": s["date"].strftime("%Y-%m-%d") if hasattr(s["date"], "strftime") else str(s["date"]),
                        "Signal": s["type"],
                        "Bias": dir_icon[s["direction"]] + " " + s["direction"].capitalize(),
                        "Detail": s["detail"],
                    }
                    for s in found[:12]
                ]
            )
            st.dataframe(sig_df, use_container_width=True, hide_index=True)
            counts = pd.Series([s["direction"] for s in found]).value_counts()
            bull_n = int(counts.get("bullish", 0))
            bear_n = int(counts.get("bearish", 0))
            net = "BULLISH" if bull_n > bear_n else ("BEARISH" if bear_n > bull_n else "MIXED")
            st.markdown(
                _sev_card("▲", bull_n, "Bullish signals", f"{bull_n} detected", "up")
                + _sev_card("▼", bear_n, "Bearish signals", f"{bear_n} detected", "dn")
                + _sev_card("●", bull_n + bear_n, "Net bias", net, "flat"),
                unsafe_allow_html=True,
            )

        st.divider()
        h2("🧭", "Support & Resistance", "swing pivots · ATR projections when at highs")
        support, resistance = signals.pivot_levels(sig_hist)
        last_close = float(sig_hist["Close"].iloc[-1])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Support**")
            if support:
                for lv in support:
                    dist = (lv / last_close - 1) * 100
                    st.markdown(f"🟢 `{lv:,.2f}` ({dist:+.1f}% from last)")
            else:
                st.caption("None detected")
        with c2:
            st.markdown("**Resistance**")
            if resistance:
                for lv in resistance:
                    dist = (lv / last_close - 1) * 100
                    st.markdown(f"🔴 `{lv:,.2f}` ({dist:+.1f}% from last)")
            else:
                st.caption("None detected")

with tab_alerts:
    h2("⏰", "Create alert", "checked on every refresh")
    with st.form("alert_form", clear_on_submit=True):
        fa1, fa2, fa3 = st.columns([2, 3, 2])
        a_sym = fa1.selectbox("Symbol", watchlist)
        a_kind = fa2.selectbox("Condition", options=list(db.ALERT_KINDS.keys()), format_func=db.ALERT_KINDS.get)
        default_target = (
            float(quote_by_ticker[a_sym]["close"]) if a_sym in quote_by_ticker and pd.notna(quote_by_ticker[a_sym]["close"]) else 100.0
        )
        a_target = fa3.number_input("Target value", value=default_target, step=0.01, format="%g")
        a_note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("➕ Add alert", use_container_width=True)
        if submitted:
            db.add_alert(a_sym, a_kind, float(a_target), a_note)
            st.rerun()

    st.divider()
    h2("📡", "Active alerts")
    active = db.list_alerts(active_only=True)
    if active.empty:
        st.caption("No active alerts.")
    else:
        for _, row in active.iterrows():
            ca, cb, cc = st.columns([4, 4, 1])
            current_txt = "-"
            q_row = quote_by_ticker.get(row["symbol"])
            val = engine.current_value(row["kind"], q_row, None) if not row["kind"].startswith("rsi") else None
            if val is not None:
                current_txt = f"now {val:g}"
            ca.markdown(f"**{row['symbol']}** - {db.ALERT_KINDS[row['kind']]} **{row['target']:g}** ({current_txt})")
            cb.caption(row["note"] or " ")
            if cc.button("🗑", key=f"del_{row['id']}"):
                db.delete_alert(int(row["id"]))
                st.rerun()

    h2("🕘", "Triggered alerts")
    done = db.list_alerts(active_only=False)
    done = done[done["active"] == 0] if not done.empty else done
    if done.empty:
        st.caption("Nothing triggered yet.")
    else:
        trig_table = done[["symbol", "kind", "target", "triggered_value", "triggered_at"]].head(20).copy()
        trig_table["kind"] = trig_table["kind"].map(db.ALERT_KINDS).fillna(trig_table["kind"])
        st.dataframe(trig_table, use_container_width=True, hide_index=True)
        if st.button("Clear triggered history"):
            for _, row in done.iterrows():
                db.delete_alert(int(row["id"]))
            st.rerun()

with tab_portfolio:
    positions = db.list_positions()

    h2("💼", "Positions", "live P&L")
    if positions.empty:
        st.caption("No positions yet. Add your first one below.")
    else:
        rows = []
        total_value = total_cost = total_day_pnl = 0.0
        for _, p in positions.iterrows():
            sym = p["symbol"]
            last_px = float(quote_by_ticker[sym]["close"]) if sym in quote_by_ticker and pd.notna(quote_by_ticker[sym]["close"]) else float(cached_history(sym, "6mo", symbol_name(sym))["Close"].iloc[-1]) if not cached_history(sym, "6mo", symbol_name(sym)).empty else p["avg_cost"]
            day_chg_abs = float(quote_by_ticker[sym]["change_abs"]) if sym in quote_by_ticker and pd.notna(quote_by_ticker[sym]["change_abs"]) else 0.0
            qty = float(p["qty"])
            cost_basis = qty * float(p["avg_cost"])
            value = qty * last_px
            pnl = value - cost_basis
            rows.append(
                {
                    "id": int(p["id"]),
                    "Symbol": sym,
                    "Qty": qty,
                    "Avg Cost": float(p["avg_cost"]),
                    "Last": last_px,
                    "Cost Basis": cost_basis,
                    "Value": value,
                    "P&L": pnl,
                    "P&L %": pnl / cost_basis * 100 if cost_basis else 0.0,
                    "Day P&L": qty * day_chg_abs,
                }
            )
            total_value += value
            total_cost += cost_basis
            total_day_pnl += qty * day_chg_abs

        pf = pd.DataFrame(rows)
        k1, k2, k3, k4 = st.columns(4)
        total_pnl = total_value - total_cost
        k1.metric("Total value", f"{total_value:,.0f} EGP")
        k2.metric("Total invested", f"{total_cost:,.0f} EGP")
        k3.metric(
            "Unrealized P&L",
            f"{total_pnl:+,.0f} EGP",
            delta=fmt_pct(total_pnl / total_cost * 100) if total_cost else None,
            delta_color=("normal" if total_pnl >= 0 else "inverse"),
        )
        k4.metric(
            "Day P&L",
            f"{total_day_pnl:+,.0f} EGP",
            delta_color=("normal" if total_day_pnl >= 0 else "inverse"),
        )

        disp = pf.copy()
        disp["Delete"] = False
        edited = st.data_editor(
            disp.style.format(
                {
                    "Qty": "{:,.0f}",
                    "Avg Cost": "{:,.2f}",
                    "Last": "{:,.2f}",
                    "Cost Basis": "{:,.0f}",
                    "Value": "{:,.0f}",
                    "P&L": "{:+,.0f}",
                    "P&L %": "{:+.2f}",
                    "Day P&L": "{:+,.0f}",
                }
            ),
            column_config={
                "id": None,
                "Delete": st.column_config.CheckboxColumn("Del?", default=False),
            },
            hide_index=True,
            use_container_width=True,
            key="positions_editor",
        )
        to_delete = edited[edited["Delete"] == True]["id"].tolist()  # noqa: E712
        if to_delete:
            for pid in to_delete:
                db.delete_position(int(pid))
            st.rerun()

    st.divider()
    h2("➕", "Add position")
    with st.form("position_form", clear_on_submit=True):
        fp1, fp2, fp3, fp4 = st.columns(4)
        p_sym = fp1.selectbox("Symbol", watchlist, key="pos_sym")
        p_qty = fp2.number_input("Quantity", min_value=0.0, step=1.0, format="%g")
        p_cost = fp3.number_input("Avg cost / share", min_value=0.0, step=0.01, format="%g")
        p_date = fp4.text_input("Buy date (optional)", placeholder="2026-08-01")
        p_note = st.text_input("Note (optional)", key="pos_note")
        if st.form_submit_button("➕ Add position", use_container_width=True) and p_qty > 0 and p_cost > 0:
            db.add_position(p_sym, float(p_qty), float(p_cost), p_date, p_note)
            st.rerun()

    st.divider()
    h2("🛡", "Risk tools", "size it · stop it")
    rk1, rk2 = st.columns(2)

    with rk1:
        st.markdown("**Position size calculator**")
        with st.form("sizing_form"):
            s1, s2 = st.columns(2)
            cap = s1.number_input("Capital (EGP)", min_value=0.0, value=100000.0, step=1000.0, format="%g")
            rpct = s2.number_input("Risk per trade (%)", min_value=0.0, value=2.0, step=0.25, format="%g")
            e1, e2 = st.columns(2)
            entry = e1.number_input("Entry price", min_value=0.0, value=float(quote_by_ticker[selected]["close"]) if selected in quote_by_ticker and pd.notna(quote_by_ticker[selected]["close"]) else 100.0, step=0.01, format="%g")
            stop_px = e2.number_input("Stop loss", min_value=0.0, value=95.0, step=0.01, format="%g")
            calc = st.form_submit_button("Calculate", use_container_width=True)
        if calc:
            res = risk.position_size(cap, rpct, entry, stop_px)
            if res is None:
                st.error("Invalid inputs (stop must differ from entry).")
            else:
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Shares", f"{res['shares']:,}")
                sc2.metric("Position cost", f"{res['cost']:,.0f}")
                sc3.metric("Cash used", fmt_pct(res["cash_used_pct"]))
                st.caption(f"Risking {rpct:g}% = {res['risk_amount']:,.0f} EGP - actual risk {res['actual_risk']:,.0f} EGP ({res['per_share_risk']:.2f}/share)")

    with rk2:
        st.markdown(f"**ATR stop suggestions - {selected}**")
        sel_hist = cached_history(selected, period, symbol_name(selected))
        stops = risk.stop_suggestions(sel_hist)
        if stops is None:
            st.caption("Not enough data.")
        else:
            last = stops["close"]
            sd1, sd2 = st.columns(2)
            sd1.metric("ATR (14d)", f"{stops['atr14']:,.2f}")
            sd2.metric("20d swing low", f"{stops['swing_low']:,.2f}")
            st.table(
                pd.DataFrame(
                    {
                        "Stop level": ["1x ATR (tight)", "2x ATR (standard)", "3x ATR (wide)", "Swing low"],
                        "Price": [stops["stop_1x"], stops["stop_2x"], stops["stop_3x"], stops["swing_low"]],
                    }
                ).assign(**{"Distance": lambda d: (d["Price"] / last - 1).map("{:+.1%}".format)})
                .style.format({"Price": "{:,.2f}"})
            )

    st.divider()
    h2("🔍", "Keep or sell — position analyzer", "technicals · news · your P&L")
    positions_now = db.list_positions()
    if positions_now.empty:
        st.caption("Add a position above first, then analyze it here.")
    else:
        held_symbols = sorted(positions_now["symbol"].unique().tolist())
        an_col1, an_col2 = st.columns([3, 2])
        an_sym = an_col1.selectbox("Position", held_symbols, key="an_sym", format_func=lambda s: f"{s} - {EGX_TICKERS.get(s, s)}")
        run_analysis = an_col2.button("🔍 Analyze", type="primary", use_container_width=True)
        if run_analysis:
            st.session_state["analyze_target"] = an_sym

        target = st.session_state.get("analyze_target")
        if target and target in held_symbols:
            pos_rows = positions_now[positions_now["symbol"] == target]
            qty = float(pos_rows["qty"].sum())
            avg_cost = float((pos_rows["qty"] * pos_rows["avg_cost"]).sum() / max(qty, 1e-9))
            q_row = quote_by_ticker.get(target)
            last_px = float(q_row["close"]) if q_row is not None and pd.notna(q_row["close"]) else None
            pnl_pct = (last_px / avg_cost - 1) * 100 if last_px else None

            an_hist = cached_history(target, "1y", symbol_name(target))
            if an_hist.empty:
                st.error("No price history available for analysis.")
            else:
                with st.spinner("Analyzing technicals + news..."):
                    tech = advisor.technical_summary(an_hist)
                    ndf = cached_news(target, EGX_TICKERS.get(target, ""))
                    nsum = news.summarize_news(ndf)
                verdict = advisor.combine_verdict(tech, nsum, pnl_pct)

                banner = (
                    st.success
                    if "KEEP" in verdict["label"]
                    else (st.error if "REDUCING" in verdict["label"] else st.warning)
                )
                banner(f"### {verdict['emoji']} {verdict['label']} — score {verdict['score']:+.2f}")
                am1, am2, am3, am4 = st.columns(4)
                if last_px is not None:
                    am1.metric("Last price", f"{last_px:,.2f}")
                am2.metric("Avg cost", f"{avg_cost:,.2f}")
                if pnl_pct is not None:
                    am3.metric(
                        "Unrealized P&L",
                        fmt_pct(pnl_pct),
                        delta_color=("normal" if pnl_pct >= 0 else "inverse"),
                    )
                am4.metric("Total qty", f"{qty:,.0f}")

                tc1, tc2 = st.columns([1, 1])
                with tc1:
                    st.markdown("**Technical view**")
                    st.markdown(f"- {tech['bull']} bullish / {tech['bear']} bearish signals")
                    st.markdown(f"- Trend: {tech['trend_label']}")
                    if tech["rsi"] is not None:
                        st.markdown(f"- RSI14: {tech['rsi']:.0f}")
                    sig_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
                    for s in tech["signals"]:
                        dt = s["date"].strftime("%Y-%m-%d") if hasattr(s["date"], "strftime") else str(s["date"])
                        st.markdown(f"- {sig_icon[s['direction']]} {dt}: {s['type']}")
                with tc2:
                    st.markdown("**News sentiment**" + (f" ({nsum['n']} headlines)" if nsum else ""))
                    if nsum:
                        nc1, nc2, nc3 = st.columns(3)
                        nc1.metric("Positive", nsum["positive"])
                        nc2.metric("Neutral", nsum["neutral"])
                        nc3.metric("Negative", nsum["negative"])
                        st.progress(
                            min(max((nsum["avg_compound"] + 1) / 2, 0.0), 1.0),
                            text=f"Avg sentiment {nsum['avg_compound']:+.2f}",
                        )
                        st.dataframe(
                            ndf.head(8)[["title", "tag"]],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "title": st.column_config.TextColumn("Headline", width="large"),
                                "tag": st.column_config.TextColumn("Tone"),
                            },
                        )
                    else:
                        st.caption("No recent headlines found for this company.")

                why_lines = "\n".join(f"- {r}" for r in verdict["reasons"])
                st.info(f"**Why this verdict:**\n\n{why_lines}")
                st.caption(
                    "Rule-based analysis of technicals + headline sentiment. News may lag or miss context - "
                    "always verify important news yourself. Not financial advice."
                )

with tab_backtest:
    bt1, bt2, bt3, bt4 = st.columns([2, 2, 2, 2])
    bt_symbol = bt1.selectbox(
        "Ticker",
        watchlist,
        index=_restore_index(watchlist, db.get_setting("bt_ticker")),
        key="bt_symbol",
        format_func=lambda s: f"{s} - {EGX_TICKERS.get(s, s)}",
    )
    if bt_symbol:
        db.set_setting("bt_ticker", bt_symbol)
    strat_name = bt2.selectbox("Strategy", options=list(backtest.STRATEGIES.keys()), format_func=backtest.STRATEGIES.get)
    initial_cap = bt3.number_input("Initial capital (EGP)", min_value=1000.0, value=100000.0, step=10000.0, format="%g")
    fee = bt4.number_input("Fees per side (%)", min_value=0.0, value=0.15, step=0.05, format="%g")

    params = {}
    if strat_name == "sma_cross":
        sp1, sp2 = st.columns(2)
        params["fast"] = sp1.slider("Fast SMA", 5, 60, 20)
        params["slow"] = sp2.slider("Slow SMA", 10, 250, 50)
        if params["fast"] >= params["slow"]:
            st.warning("Fast SMA should be below slow SMA.")
    elif strat_name == "rsi_reversion":
        rp1, rp2, rp3 = st.columns(3)
        params["n"] = rp1.slider("RSI period", 5, 30, 14)
        params["oversold"] = rp2.slider("Entry when RSI <", 15, 45, 30)
        params["exit"] = rp3.slider("Exit when RSI >", 40, 90, 60)

    run_bt = st.button("▶ Run backtest", type="primary")
    if run_bt:
        bt_hist = cached_history(bt_symbol, period, symbol_name(bt_symbol))
        if bt_hist.empty or len(bt_hist) < 60:
            st.error("Not enough history for a meaningful backtest.")
        else:
            bt_q = quote_by_ticker.get(bt_symbol)
            bt_live = float(bt_q["close"]) if bt_q is not None and pd.notna(bt_q["close"]) else None
            if bt_live and abs(float(bt_hist["Close"].iloc[-1]) - bt_live) / bt_live > 0.25:
                st.warning(
                    f"Yahoo history for {bt_symbol} looks out of scale vs the live price "
                    f"(history {float(bt_hist['Close'].iloc[-1]):,.2f} vs live {bt_live:,.2f}) - "
                    f"likely an unadjusted split. Backtest results may be misleading."
                )
            result = backtest.run_backtest(bt_hist, strategy=strat_name, params=params, initial=initial_cap, fee_pct=fee)
            bm1, bm2, bm3, bm4, bm5 = st.columns(5)
            beat = result["total_return"] - result["buy_hold_return"]
            bm1.metric(
                "Strategy return",
                fmt_pct(result["total_return"]),
                delta=f"{beat:+.1f}% vs B&H",
                delta_color=("normal" if beat >= 0 else "inverse"),
            )
            bm2.metric("Buy & hold", fmt_pct(result["buy_hold_return"]))
            bm3.metric("Max drawdown", fmt_pct(result["max_drawdown"]))
            bm4.metric("Sharpe", f"{result['sharpe']:.2f}")
            bm5.metric("Trades", f"{result['n_trades']} (win {result['win_rate']:.0f}%)")

            eq = result["equity"]
            bh_eq = initial_cap * bt_hist["Close"] / bt_hist["Close"].iloc[0]
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=eq.index, y=eq, name="Strategy", line=dict(color="#26a69a", width=2)))
            fig_bt.add_trace(go.Scatter(x=bh_eq.index, y=bh_eq, name="Buy & Hold", line=dict(color="#888888", width=1.4, dash="dash")))
            fig_bt.update_layout(template="plotly_dark" if saved_theme == "dark" else "plotly_white", height=420, margin=dict(l=40, r=20, t=30, b=30), legend=dict(orientation="h"), hovermode="x unified")
            st.plotly_chart(fig_bt, use_container_width=True, theme=None, config=PLOTLY_CONFIG)

            if result["trades"]:
                tr = pd.DataFrame(result["trades"])
                tr["entry_date"] = pd.to_datetime(tr["entry_date"]).dt.strftime("%Y-%m-%d")
                tr["exit_date"] = pd.to_datetime(tr["exit_date"]).dt.strftime("%Y-%m-%d")
                tr = tr.rename(columns={"entry": "Entry", "exit": "Exit", "pnl_pct": "P&L %"})
                st.dataframe(
                    tr[["entry_date", "Entry", "exit_date", "Exit", "P&L %"]].style.format({"Entry": "{:,.2f}", "Exit": "{:,.2f}", "P&L %": "{:+.2f}"}),
                    use_container_width=True,
                    hide_index=True,
                )
                aw = result["avg_win"]
                al = result["avg_loss"]
                st.caption(f"Avg winner {aw:+.2f}% - avg loser {al:+.2f}% - final equity {result['final_equity']:,.0f} EGP")
            else:
                st.caption("Strategy produced no round trips in this period.")

with tab_news:
    h2("📰", "EGX market news", "Google News · Daily News Egypt · auto sentiment")
    st.caption("Aggregated from Google News (EGX queries) and Daily News Egypt. Headline sentiment scored automatically.")
    ncol1, ncol2 = st.columns([3, 1])
    news_filter = ncol1.text_input("Filter headlines", placeholder="e.g. COMI, dividend, EGX30...")
    refresh_mode = ncol2.segmented_control("Auto-refresh", options=["Off", "1m", "5m"], default="Off")
    if refresh_mode in ("1m", "5m"):
        tick = st_autorefresh(interval=(60 if refresh_mode == "1m" else 300) * 1000, key="news_auto_tick")
        if tick != st.session_state.get("news_last_tick", 0):
            st.session_state.news_last_tick = tick
            cached_market_news.clear()
    if ncol2.button("🔄 Refresh news", use_container_width=True):
        cached_market_news.clear()
        st.rerun()

    mnews = cached_market_news()
    if mnews.empty:
        st.warning("Could not load market news right now.")
    else:
        shown = mnews
        if news_filter.strip():
            flt = news_filter.strip().lower()
            shown = mnews[mnews["title"].str.lower().str.contains(flt, na=False)]
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Headlines", len(shown))
        sc2.metric("🟢 Positive", int((shown["tag"] == "positive").sum()))
        sc3.metric("⚪ Neutral", int((shown["tag"] == "neutral").sum()))
        sc4.metric("🔴 Negative", int((shown["tag"] == "negative").sum()))

        disp = shown.copy()
        disp["When"] = disp["dt"].dt.strftime("%b %d, %H:%M")
        disp["Sentiment"] = disp["compound"].map(lambda v: f"{v:+.2f}")
        st.dataframe(
            disp[["When", "source", "title", "Sentiment", "url"]],
            column_config={
                "When": st.column_config.TextColumn("When", width="small"),
                "source": st.column_config.TextColumn("Source", width="small"),
                "title": st.column_config.TextColumn("Headline", width="large"),
                "Sentiment": st.column_config.ProgressColumn(
                    "Sentiment", min_value=-1.0, max_value=1.0, format="%+.2f", width="small"
                ),
                "url": st.column_config.LinkColumn("Link", display_text="Open ↗", width="small"),
            },
            use_container_width=True,
            height=520,
            hide_index=True,
        )

movers_map = {"Gainers": ("change", False), "Losers": ("change", True), "Volume": ("volume", False)}
sort_field, ascending = movers_map[movers_sort]
movers = cached_movers(sort_field, ascending, 10)
if not movers.empty:
    st.divider()
    with st.expander(f"🏆 Market movers — top 10 by {movers_sort.lower()}", expanded=False):
        mv = movers[["ticker", "name", "close", "change", "volume"]].copy()
        mv["name"] = mv["name"].str.slice(0, 28)
        mv["Logo"] = [universe_logo.get(t, "") for t in mv["ticker"]]
        mv.insert(3, "Chg % ▲▼", mv["change"].map(lambda v: f"{'▲' if v >= 0 else '▼'} {v:+.2f}%"))
        st.dataframe(
            mv[["Logo", "ticker", "name", "close", "Chg % ▲▼", "volume"]].style.format(
                {"close": "{:,.2f}", "volume": "{:,.0f}"}
            ).map(_chg_color, subset=["Chg % ▲▼"]),
            column_config={"Logo": st.column_config.ImageColumn("", width="small")},
            use_container_width=True,
            height=380,
            hide_index=True,
        )

st.markdown(
    "<div class='foot'>⚠️ Educational tool for personal research. Prices are delayed; "
    "indicators and news sentiment are rule-based — not financial advice.</div>",
    unsafe_allow_html=True,
)
