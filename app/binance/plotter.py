from app.types import Candle
from plotly.subplots import make_subplots
from typing import Any, Dict, List
import plotly.graph_objects as go


def plot_candles_html(
    raw_candles: List[Candle],
    symbol,
    signal_time,
    entry_prices=None,
    stop_loss=None,
    take_profits=None,
    signal_id=None,
) -> str:
    if not raw_candles:
        return "⚠️ No data for chart"
    candles: List[Dict[str, Any]] = [
        {
            "time": candle.time,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in raw_candles
    ]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03
    )

    times = [c["time"] for c in candles]

    fig.add_trace(
        go.Candlestick(
            x=times,
            open=[c["open"] for c in candles],
            high=[c["high"] for c in candles],
            low=[c["low"] for c in candles],
            close=[c["close"] for c in candles],
            name="Price",
            increasing_line_color="#00CC96",
            decreasing_line_color="#EF4444",
            increasing_fillcolor="#00CC96",
            decreasing_fillcolor="#EF4444",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=times,
            y=[c["volume"] for c in candles],
            name="Volume",
            marker_color="#6B7280",
        ),
        row=2,
        col=1,
    )

    if entry_prices:
        for i, price in enumerate(entry_prices):
            fig.add_hline(
                y=price,
                line_dash="dash",
                line_color="#60A5FA",
                annotation_text=f"Entry {i+1}",
                annotation_position="top left",
                annotation_font_color="#D8BFD8",
                row=1,  # type: ignore
            )

    if stop_loss:
        fig.add_hline(
            y=stop_loss,
            line_dash="dot",
            line_color="#B91C1C",
            annotation_text="Stop Loss",
            annotation_position="bottom right",
            annotation_font_color="#D8BFD8",
            row=1,  # type: ignore
        )

    if take_profits:
        for i, price in enumerate(take_profits):
            fig.add_hline(
                y=price,
                line_dash="dot",
                line_color="#C084FC",
                annotation_text=f"Take Profit {i+1}",
                annotation_position="top right",
                annotation_font_color="#D8BFD8",
                row=1,  # type: ignore
            )

    entry_price = entry_prices[0] if entry_prices else candles[0]["close"]
    fig.add_trace(
        go.Scatter(
            x=[signal_time],
            y=[entry_price],
            mode="markers+text",
            marker=dict(
                color="#A100A1",
                size=12,
                line=dict(width=2, color="#FFFFFF"),
            ),
            text=["Signal Time"],
            textposition="top center",
            textfont=dict(color="#D8BFD8"),
            name="Signal Time",
            hoverinfo="text",
            hovertext=f"Signal Time<br>Время: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}<br>Цена: {entry_price:.8f}",
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        height=800,
        title=f"{symbol} (Signal {signal_id})",
        xaxis_title="",
        yaxis_title="Price",
        xaxis2_title="Time",
        yaxis2_title="Volume",
        showlegend=False,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        plot_bgcolor="#0d0d0d",
        paper_bgcolor="#0d0d0d",
        font=dict(family="Courier New, monospace", size=12, color="#D8BFD8"),
        hovermode="x unified",
        xaxis=dict(
            gridcolor="#4B0082",
            tickfont=dict(color="#D8BFD8"),
        ),
        yaxis=dict(
            gridcolor="#4B0082",
            tickfont=dict(color="#D8BFD8"),
        ),
        xaxis2=dict(
            gridcolor="#4B0082",
            tickfont=dict(color="#D8BFD8"),
        ),
        yaxis2=dict(
            gridcolor="#4B0082",
            tickfont=dict(color="#D8BFD8"),
        ),
    )

    fig.update_xaxes(type="date", row=1, col=1)
    fig.update_xaxes(type="date", row=2, col=1)

    return fig.to_html(full_html=False)
