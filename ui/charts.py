import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    show_sma: bool = True,
    show_ema: bool = False,
    show_bb: bool = False,
    show_rsi: bool = True,
    show_macd: bool = True,
    show_volume: bool = True,
    levels: tuple[list[float], list[float]] | None = None,
    theme: str = "dark",
) -> go.Figure:
    rows = 1 + int(show_volume) + int(show_rsi) + int(show_macd)
    row_heights = []
    base = 1.0
    if show_volume:
        row_heights.append(0.18)
    if show_rsi:
        row_heights.append(0.22)
    if show_macd:
        row_heights.append(0.22)
    chart_h = base - sum(row_heights)
    row_heights.insert(0, max(chart_h, 0.3))
    heights = tuple(h / sum(row_heights) for h in row_heights)

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=list(heights),
    )

    price_row = 1
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=price_row,
        col=1,
    )

    if show_sma:
        for col, color in (("SMA20", "#ff9800"), ("SMA50", "#2196f3"), ("SMA200", "#9c27b0")):
            if col in df and df[col].notna().any():
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[col], name=col, line=dict(width=1.4, color=color)),
                    row=price_row,
                    col=1,
                )
    if show_ema and "EMA20" in df and df["EMA20"].notna().any():
        fig.add_trace(
            go.Scatter(x=df.index, y=df["EMA20"], name="EMA20", line=dict(width=1.4, dash="dot", color="#00bcd4")),
            row=price_row,
            col=1,
        )
    if show_bb and all(c in df for c in ("BB_Upper", "BB_Mid", "BB_Lower")) and df["BB_Mid"].notna().any():
        fig.add_trace(
            go.Scatter(x=df.index, y=df["BB_Mid"], name="BB Mid", line=dict(width=1, dash="dot", color="rgba(150,150,150,0.9)")),
            row=price_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper", line=dict(width=1, color="rgba(150,150,150,0.6)")),
            row=price_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower", fill="tonexty",
                       fillcolor="rgba(150,150,150,0.08)", line=dict(width=1, color="rgba(150,150,150,0.6)")),
            row=price_row,
            col=1,
        )

    if levels:
        support, resistance = levels
        x0, x1 = df.index[0], df.index[-1]
        for lv in resistance:
            fig.add_trace(
                go.Scatter(x=[x0, x1], y=[lv, lv], name=f"R {lv:,.2f}",
                           line=dict(width=1.2, color="#ef5350", dash="dash"), showlegend=False,
                           hovertemplate=f"Resistance {lv:,.2f}<extra></extra>"),
                row=price_row,
                col=1,
            )
        for lv in support:
            fig.add_trace(
                go.Scatter(x=[x0, x1], y=[lv, lv], name=f"S {lv:,.2f}",
                           line=dict(width=1.2, color="#26a69a", dash="dash"), showlegend=False,
                           hovertemplate=f"Support {lv:,.2f}<extra></extra>"),
                row=price_row,
                col=1,
            )

    r = 2
    if show_volume:
        colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=colors, showlegend=False),
            row=r,
            col=1,
        )
        fig.update_yaxes(title_text="Vol", row=r, col=1)
        r += 1

    if show_rsi:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["RSI14"], name="RSI14", line=dict(width=1.3, color="#7e57c2"), showlegend=False),
            row=r,
            col=1,
        )
        fig.add_hline(y=70, line=dict(color="#ef5350", width=1, dash="dash"), row=r, col=1)
        fig.add_hline(y=30, line=dict(color="#26a69a", width=1, dash="dash"), row=r, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=r, col=1)
        r += 1

    if show_macd:
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_Hist"]]
        fig.add_trace(
            go.Bar(x=df.index, y=df["MACD_Hist"], name="MACD Hist", marker_color=hist_colors, showlegend=False),
            row=r,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(width=1.3, color="#2196f3"), showlegend=False),
            row=r,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(width=1.3, color="#ff9800"), showlegend=False),
            row=r,
            col=1,
        )
        fig.update_yaxes(title_text="MACD", row=r, col=1)

    is_dark = theme == "dark"
    paper = "rgb(17,17,17)" if is_dark else "#ffffff"
    plot_bg = "rgb(17,17,17)" if is_dark else "#ffffff"
    font_color = "#f2f5fa" if is_dark else "#2a3f5f"
    grid = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"
    accent = "#26a69a"

    fig.update_layout(
        height=320 + 210 * (rows - 1),
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor=paper,
        plot_bgcolor=plot_bg,
        font=dict(color=font_color),
        margin=dict(l=40, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        dragmode="pan",
    )
    fig.update_xaxes(
        gridcolor=grid,
        zerolinecolor=grid,
        showspikes=True,
        spikemode="across",
        spikedash="dot",
        spikecolor=accent,
        spikesnap="cursor",
        rangebreaks=[dict(bounds=["fri", "sun"])],
    )
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid)
    return fig
