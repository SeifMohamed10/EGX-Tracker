import json


def advanced_chart_html(symbol: str, theme: str = "dark", height: int = 640, interval: str = "D") -> str:
    theme = "dark" if theme == "dark" else "light"
    if interval not in ("D", "W", "M"):
        interval = "D"
    background = "rgba(19,23,34,1)" if theme == "dark" else "rgba(255,255,255,1)"
    config = {
        "width": "100%",
        "height": height,
        "symbol": symbol,
        "interval": interval,
        "timezone": "Africa/Cairo",
        "theme": theme,
        "style": "1",
        "locale": "en",
        "backgroundColor": background,
        "gridColor": "rgba(128,128,128,0.15)",
        "enable_publishing": False,
        "allow_symbol_change": False,
        "save_image": False,
        "calendar": False,
        "withdateranges": True,
        "hide_side_toolbar": False,
        "studies": [
            {"id": "MASimple@tv-basicstudies", "inputs": {"length": 20}},
            {"id": "MASimple@tv-basicstudies", "inputs": {"length": 50}},
            {"id": "MASimple@tv-basicstudies", "inputs": {"length": 200}},
        ],
        "support_host": "https://www.tradingview.com",
    }
    payload = json.dumps(config)
    return (
        '<div class="tradingview-widget-container" style="height:{h}px;width:100%">'
        '<div class="tradingview-widget-container__widget" style="height:{h}px;width:100%"></div>'
        '<script type="text/javascript" src="https://s3.tradingview.com/'
        'external-embedding/embed-widget-advanced-chart.js" async>{p}</script>'
        "</div>"
    ).format(h=height, p=payload)
