from datetime import datetime
import logging
from app.types import Candle
from plotly.subplots import make_subplots
from typing import Any, Dict, List
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_price_cross(
    candles: List[Candle],
    signal_time: datetime,
    target_price: float,
    level_type: str,
) -> tuple:
    try:
        signal_idx = None
        for i, candle in enumerate(candles):
            if candle.time >= signal_time:
                signal_idx = i
                break

        if signal_idx is None:
            return None, None, None

        for i in range(signal_idx, len(candles)):
            candle = candles[i]

            if level_type == "TP":
                if candle.high >= target_price:
                    return candle.time, target_price, "Take-Profit"

            elif level_type == "SL":
                if candle.low <= target_price:
                    return candle.time, target_price, "Stop-Loss"

            if i < len(candles) - 1:
                next_candle = candles[i + 1]

                if level_type == "TP":
                    if candle.close < target_price < next_candle.open:
                        return next_candle.time, target_price, "Take-Profit"

                elif level_type == "SL":
                    if candle.close > target_price > next_candle.open:
                        return next_candle.time, target_price, "Stop-Loss"

        return None, None, None

    except Exception as e:
        logging.error(f"Error in find_price_cross: {str(e)}", exc_info=True)
        return None, None, None


def find_crossings(candles, target_price, level_type, signal_time):
    crossings = []
    signal_passed = False

    for i, candle in enumerate(candles):
        if candle.time >= signal_time:
            signal_passed = True

        if signal_passed:
            if level_type == "TP" and candle.high >= target_price:
                crossings.append((candle.time, target_price, "TP"))
            elif level_type == "SL" and candle.low <= target_price:
                crossings.append((candle.time, target_price, "SL"))

    return crossings[0] if crossings else (None, None, None)


def plot_candles_html(
    candles: List[Candle],
    symbol: str,
    signal_time: datetime,
    entry_prices: List[float],
    stop_loss: float,
    take_profits: List[float],
    signal_id: int,
    auto_open: bool = False,
) -> str:
    if not candles:
        return "⚠️ No data for chart"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03
    )

    times = [c.time for c in candles]

    fig.add_trace(
        go.Candlestick(
            x=times,
            open=[c.open for c in candles],
            high=[c.high for c in candles],
            low=[c.low for c in candles],
            close=[c.close for c in candles],
            name="Price",
            increasing_line_color="#06d6a0",
            decreasing_line_color="#f07167",
            increasing_fillcolor="#06d6a0",
            decreasing_fillcolor="#f07167",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=times,
            y=[c.volume for c in candles],
            name="Volume",
            marker_color="#3c096c",
        ),
        row=2,
        col=1,
    )

    if take_profits:
        for i, tp_price in enumerate(take_profits):
            tp_time, _, _ = find_crossings(candles, tp_price, "TP", signal_time)
            if tp_time:
                fig.add_trace(
                    go.Scatter(
                        x=[tp_time],
                        y=[tp_price],
                        mode="markers+text",
                        marker=dict(
                            color="#ff0000",
                            size=12,
                            symbol="diamond",
                            line=dict(width=2, color="white"),
                        ),
                        text=["TP"],
                        textposition="top center",
                        textfont=dict(color="#dee2ff"),
                        name="TP",
                        hoverinfo="text",
                        hovertext=f"Take Profit {i+1} Hit<br>Time: {tp_time}<br>Price: {tp_price:.8f}",
                    ),
                    row=1,
                    col=1,
                )

    if stop_loss:
        sl_time, _, _ = find_crossings(candles, stop_loss, "SL", signal_time)
        if sl_time:
            fig.add_trace(
                go.Scatter(
                    x=[sl_time],
                    y=[stop_loss],
                    mode="markers+text",
                    marker=dict(
                        color="#a1ff0a",
                        size=12,
                        symbol="x",
                        line=dict(width=2, color="white"),
                    ),
                    text=["SL"],
                    textposition="top center",
                    textfont=dict(color="#dee2ff"),
                    name="SL",
                    hoverinfo="text",
                    hovertext=f"Stop Loss Hit<br>Time: {sl_time}<br>Price: {stop_loss:.8f}",
                ),
                row=1,
                col=1,
            )

    if entry_prices:
        for i, price in enumerate(entry_prices):
            fig.add_hline(
                y=price,
                line_dash="longdash",
                line_color="#e9c46a",
                annotation_text=f"Entry {i+1}",
                annotation_position="right",
                annotation_font_color="#dee2ff",
                annotation_font_size=14,
                row=1,  # type: ignore
            )

    if stop_loss:
        fig.add_hline(
            y=stop_loss,
            line_dash="longdash",
            line_color="#e76f51",
            line_width=2,
            annotation_text="Stop Loss",
            annotation_position="right",
            annotation_font_color="#dee2ff",
            annotation_font_size=14,
            row=1,  # type: ignore
        )

    if take_profits:
        for i, price in enumerate(take_profits):
            fig.add_hline(
                y=price,
                line_dash="longdash",
                line_color="#2a9d8f",
                line_width=2,
                annotation_text=f"Take Profit {i+1}",
                annotation_position="right",
                annotation_font_color="#dee2ff",
                annotation_font_size=14,
                row=1,  # type: ignore
            )

    entry_price = entry_prices[0] if entry_prices else candles[0].close
    fig.add_trace(
        go.Scatter(
            x=[signal_time],
            y=[entry_price],
            mode="markers+text",
            marker=dict(
                color="#9d4edd",
                size=12,
                line=dict(width=2, color="#FFFFFF"),
            ),
            text=["Signal Time"],
            textposition="top center",
            textfont=dict(color="#dee2ff"),
            name="Signal Time",
            hoverinfo="text",
            hovertext=f"Signal Time<br>Time: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}<br>Price: {entry_price:.8f}",
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        margin=dict(r=140),
        height=800,
        title=f"{symbol} (Signal {signal_id})",
        xaxis_title="",
        yaxis_title="Price",
        xaxis2_title="Time",
        yaxis2_title="Vloume",
        showlegend=False,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        plot_bgcolor="#10002b",
        paper_bgcolor="#10002b",
        font=dict(family="Courier New, monospace", size=14, color="#dee2ff"),
        hovermode="x unified",
        xaxis=dict(
            gridcolor="#4e148c",
            tickfont=dict(color="#dee2ff", size=14),
        ),
        yaxis=dict(
            gridcolor="#4e148c",
            tickfont=dict(color="#dee2ff", size=14),
        ),
        xaxis2=dict(
            gridcolor="#4e148c",
            tickfont=dict(color="#dee2ff", size=14),
        ),
        yaxis2=dict(
            gridcolor="#4e148c",
            tickfont=dict(color="#dee2ff", size=14),
        ),
    )

    fig.update_xaxes(type="date", row=1, col=1)
    fig.update_xaxes(type="date", row=2, col=1)

    return fig.to_html(full_html=False)
