import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz


class CryptoSignalVisualizer:

    COLORS = {
        "BULL": "rgba(0, 230, 210, 1.0)",
        "BEAR": "rgba(255, 60, 60, 1.0)",
        "SIGNAL": "rgba(255, 165, 0, 1.0)",
        "STOP_LOSS": "rgba(255, 0, 0, 0.7)",
        "TAKE_PROFIT": "rgba(0, 200, 0, 0.7)",
        "CROSS": "rgba(150, 0, 200, 1.0)",
    }

    def __init__(self, data_dir="app/binance/crypto_data", plot_dir=None):
        self.data_dir = data_dir
        self.plot_dir = plot_dir or os.path.join(data_dir, "plots")
        os.makedirs(self.plot_dir, exist_ok=True)
        self.timezone = pytz.timezone("Europe/Moscow")
        self.now = datetime.now(self.timezone)

    def _ensure_datetime(self, dt):
        """Преобразует входное время в datetime с часовым поясом"""
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        if not isinstance(dt, datetime):
            raise ValueError(f"Неподдерживаемый тип времени: {type(dt)}")

        if dt.tzinfo is None:
            return self.timezone.localize(dt)
        return dt.astimezone(self.timezone)

    def load_data_for_signal(self, symbol, signal_time, minutes_before=5):
        """Загружает данные за указанное время до и после сигнала"""
        signal_time = self._ensure_datetime(signal_time)
        interval = self._detect_interval(symbol)
        filepath = os.path.join(self.data_dir, f"{symbol}_{interval}.csv")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл данных для {symbol} не найден: {filepath}")

        df = pd.read_csv(filepath)
        if df.empty:
            raise ValueError(f"Нет данных для {symbol}")

        df["open_time"] = pd.to_datetime(df["open_time"])
        if df["open_time"].dt.tz is None:
            df["open_time"] = df["open_time"].dt.tz_localize(self.timezone)

        end_time = self.now
        filtered_df = df[(df["open_time"] <= end_time)].copy()

        if filtered_df.empty:
            raise ValueError(f"Нет данных для {symbol} в указанном временном диапазоне")

        return filtered_df

    def _detect_interval(self, symbol):
        """Определяет интервал данных по имени файла"""
        for file in os.listdir(self.data_dir):
            if file.startswith(f"{symbol}_") and file.endswith(".csv"):
                return file.split("_")[1].replace(".csv", "")
        return "1s"

    def _find_price_cross(self, df, signal_time, target_price):
        """Находит точное пересечение цены с целевым уровнем"""
        try:
            post_signal_df = df[df["open_time"] >= signal_time]
            if post_signal_df.empty:
                return None, None

            signal_idx = post_signal_df.index[0]
            df_slice = df.iloc[signal_idx:]

            if len(df_slice) < 2:
                return None, None

            full_timeline = pd.date_range(
                start=df_slice.iloc[0]["open_time"],
                end=df_slice.iloc[-1]["open_time"],
                freq="1min",
            )

            interp_prices = np.interp(
                [x.timestamp() for x in full_timeline],
                [x.timestamp() for x in df_slice["open_time"]],
                df_slice["close"],
            )

            for i in range(1, len(full_timeline)):
                prev_price = interp_prices[i - 1]
                curr_price = interp_prices[i]

                if (prev_price < target_price < curr_price) or (
                    prev_price > target_price > curr_price
                ):
                    cross_time = full_timeline[i]
                    cross_price = target_price
                    return cross_time, cross_price

            return None, None
        except Exception as e:
            print(f"Ошибка при поиске пересечения: {str(e)}")
            return None, None

    def create_signal_chart(self, symbol, signal_time, signal_type, price1, price2):
        """Создаёт график с отметкой сигнала и точками пересечения"""
        try:
            signal_time = self._ensure_datetime(signal_time)

            df = self.load_data_for_signal(symbol, signal_time)

            if signal_type.lower() in ["short", "sell"]:
                stop_loss = max(price1, price2)
                take_profit = min(price1, price2)
            else:
                stop_loss = min(price1, price2)
                take_profit = max(price1, price2)

            entry_points = df[df["open_time"] >= signal_time]
            if entry_points.empty:
                raise ValueError("Нет данных для точки входа после сигнального времени")

            entry_point = entry_points.iloc[0]
            entry_price = entry_point["open"]

            tp_time, tp_price = self._find_price_cross(df, signal_time, take_profit)
            sl_time, sl_price = self._find_price_cross(df, signal_time, stop_loss)

            if tp_time and sl_time:
                if tp_time < sl_time:
                    cross_time, cross_price, cross_type = (
                        tp_time,
                        tp_price,
                        "Take-Profit",
                    )
                else:
                    cross_time, cross_price, cross_type = sl_time, sl_price, "Stop-Loss"
            elif tp_time:
                cross_time, cross_price, cross_type = tp_time, tp_price, "Take-Profit"
            elif sl_time:
                cross_time, cross_price, cross_type = sl_time, sl_price, "Stop-Loss"
            else:
                cross_time, cross_price, cross_type = None, None, None

            if cross_time:
                additional_end_time = min(self.now, cross_time + timedelta(minutes=5))
                if additional_end_time > df["open_time"].max():
                    additional_df = self.load_data_for_signal(
                        symbol,
                        signal_time,
                        minutes_before=5,
                        minutes_after=int(
                            (additional_end_time - signal_time).total_seconds() / 60
                        ),
                    )
                    df = additional_df

            df["color"] = np.where(
                df["open"] > df["close"], self.COLORS["BEAR"], self.COLORS["BULL"]
            )

            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.75, 0.25],
                specs=[[{"secondary_y": True}], [{}]],
            )

            # Свечной график
            fig.add_trace(
                go.Candlestick(
                    x=df["open_time"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    increasing_line_color=self.COLORS["BULL"],
                    decreasing_line_color=self.COLORS["BEAR"],
                    increasing_fillcolor=self.COLORS["BULL"],
                    decreasing_fillcolor=self.COLORS["BEAR"],
                    name="Свечи",
                    whiskerwidth=0.9,
                    line={"width": 1},
                    hoverinfo="text",
                    hovertext=[
                        f"<b>{symbol}</b><br>Дата: {x.strftime('%Y-%m-%d %H:%M:%S')}<br>Открытие: {o:.8f}<br>Максимум: {h:.8f}<br>Минимум: {l:.8f}<br>Закрытие: {c:.8f}"
                        for x, o, h, l, c in zip(
                            df["open_time"],
                            df["open"],
                            df["high"],
                            df["low"],
                            df["close"],
                        )
                    ],
                ),
                row=1,
                col=1,
            )

            # Точка входа
            fig.add_trace(
                go.Scatter(
                    x=[entry_point["open_time"]],
                    y=[entry_price],
                    mode="markers+text",
                    marker=dict(
                        color=self.COLORS["SIGNAL"],
                        size=12,
                        line=dict(width=2, color="rgba(0,0,0,0.8)"),
                    ),
                    text=["Точка входа"],
                    textposition="top center",
                    name="Точка входа",
                    hoverinfo="text",
                    hovertext=[
                        f"Точка входа<br>Время: {entry_point['open_time'].strftime('%Y-%m-%d %H:%M:%S')}<br>Цена: {entry_price:.8f}"
                    ],
                ),
                row=1,
                col=1,
            )

            for price, color, name in [
                (stop_loss, self.COLORS["STOP_LOSS"], f"Stop-Loss ({stop_loss:.8f})"),
                (
                    take_profit,
                    self.COLORS["TAKE_PROFIT"],
                    f"Take-Profit ({take_profit:.8f})",
                ),
            ]:
                fig.add_trace(
                    go.Scatter(
                        x=df["open_time"],
                        y=[price] * len(df),
                        mode="lines",
                        line=dict(color=color, width=2, dash="dash"),
                        name=name,
                        hoverinfo="y+name",
                    ),
                    row=1,
                    col=1,
                )

            if cross_time is not None:
                fig.add_trace(
                    go.Scatter(
                        x=[cross_time],
                        y=[cross_price],
                        mode="markers+text",
                        marker=dict(
                            color=self.COLORS["CROSS"],
                            size=12,
                            line=dict(width=2, color="rgba(0,0,0,0.8)"),
                        ),
                        text=[cross_type],
                        textposition="top center",
                        name=cross_type,
                        hoverinfo="text",
                        hovertext=[
                            f"{cross_type}<br>Время: {cross_time.strftime('%Y-%m-%d %H:%M:%S')}<br>Цена: {cross_price:.8f}"
                        ],
                    ),
                    row=1,
                    col=1,
                )

            # Объемы
            fig.add_trace(
                go.Bar(
                    x=df["open_time"],
                    y=df["volume"],
                    marker_color=df["color"],
                    name="Объем",
                    opacity=1.0,
                    width=0.8,
                    hoverinfo="text",
                    hovertext=[f"Объем: {y:.2f}" for y in df["volume"]],
                ),
                row=2,
                col=1,
            )

            fig.update_layout(
                title={
                    "text": f"<b>{symbol}</b> | Сигнал: {signal_type} | Вход: {entry_price:.8f}",
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": {"size": 16},
                },
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_color="black",
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                height=800,
                margin=dict(l=50, r=50, t=100, b=50),
                hoverlabel=dict(
                    bgcolor="rgba(255,255,255,0.9)",
                    font_size=14,
                    font_family="Arial",
                    bordercolor="rgba(0,0,0,0.1)",
                ),
            )

            fig.update_yaxes(title_text="Цена", row=1, col=1)
            fig.update_yaxes(title_text="Объем", row=2, col=1)
            fig.update_xaxes(title_text="Дата", row=2, col=1)

            return fig

        except Exception as e:
            print(f"Ошибка при создании графика: {str(e)}")
            raise

    def save_signal_chart(self, symbol, signal_time, signal_type, price1, price2):
        """Создаёт график с сигналом и возвращает строку с HTML-кодом"""
        try:
            fig = self.create_signal_chart(symbol, signal_time, signal_type, price1, price2)
            
            # Исправлено: удален неподдерживаемый аргумент auto_open
            html_str = fig.to_html(
                full_html=True,
                include_plotlyjs='cdn'
            )
            
            print("График с сигналом успешно сгенерирован")
            return html_str
            
        except Exception as e:
            print(f"Ошибка при создании графика: {str(e)}")
            return None


visualizer = CryptoSignalVisualizer()
signal_tuple = ("BTCUSDT", "2023-10-15 12:00:00", "buy", 28000, 27500)
visualizer.save_signal_chart(*signal_tuple)
