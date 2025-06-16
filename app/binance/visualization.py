import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import pytz
from decimal import Decimal
from typing import Union, Optional

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
        self.now = datetime.datetime.now(self.timezone)

    def _ensure_datetime(self, dt: Union[str, datetime.datetime, pd.Timestamp]) -> datetime.datetime:
        """Преобразует входное время в datetime с часовым поясом"""
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        
        if isinstance(dt, datetime.datetime) and dt.tzinfo is None:
            return self.timezone.localize(dt)
        
        if isinstance(dt, datetime.datetime) and dt.tzinfo is not None:
            return dt.astimezone(self.timezone)
        
        raise ValueError(f"Неподдерживаемый тип времени: {type(dt)}")

    def load_data_for_signal(self, symbol: str, signal_time: datetime.datetime, minutes_before: int = 5, minutes_after: Optional[int] = None) -> pd.DataFrame:
        """Загружает данные за указанное время до и после сигнала"""
        interval = self._detect_interval(symbol)
        filepath = os.path.join(self.data_dir, f"{symbol}_{interval}.csv")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл данных для {symbol} не найден: {filepath}")

        df = pd.read_csv(filepath)
        if df.empty:
            raise ValueError(f"Нет данных для {symbol}")

        df["open_time"] = pd.to_datetime(df["open_time"])
        
        start_time = signal_time - datetime.timedelta(minutes=minutes_before)
        end_time = self.now if minutes_after is None else signal_time + datetime.timedelta(minutes=minutes_after)
        
        filtered_df = df[(df["open_time"] >= start_time) & (df["open_time"] <= end_time)].copy()
        
        if filtered_df.empty:
            raise ValueError(f"Нет данных для {symbol} в указанном временном диапазоне")

        if filtered_df["open_time"].dt.tz is None:
            filtered_df["open_time"] = filtered_df["open_time"].dt.tz_localize(self.timezone)
        else:
            filtered_df["open_time"] = filtered_df["open_time"].dt.tz_convert(self.timezone)

        return filtered_df

    def _detect_interval(self, symbol: str) -> str:
        """Определяет интервал данных по имени файла"""
        for file in os.listdir(self.data_dir):
            if file.startswith(f"{symbol}_") and file.endswith(".csv"):
                return file.split("_")[1].replace(".csv", "")
        return "1s"

    def _find_price_cross(self, df: pd.DataFrame, signal_time: datetime.datetime, target_price: float) -> tuple:
        """Находит точное пересечение цены с целевым уровнем"""
        try:
            post_signal_df = df[df["open_time"] >= signal_time]
            if post_signal_df.empty:
                return None, None

            signal_idx = post_signal_df.index[0]
            df_slice = df.iloc[signal_idx:]
            
            if len(df_slice) < 2:
                return None, None

            prices = df_slice[['open', 'high', 'low', 'close']].values
            times = df_slice['open_time'].values
            
            for i in range(1, len(df_slice)):
                prev_row = df_slice.iloc[i-1]
                curr_row = df_slice.iloc[i]
                
                if (prev_row['low'] <= target_price <= prev_row['high'] or
                    curr_row['low'] <= target_price <= curr_row['high'] or
                    (prev_row['close'] < target_price < curr_row['open']) or
                    (prev_row['close'] > target_price > curr_row['open'])):
                    
                    return curr_row['open_time'], target_price
                    
            return None, None
        except Exception as e:
            print(f"Ошибка при поиске пересечения: {str(e)}")
            return None, None

    def create_signal_chart(self, symbol: str, signal_time: datetime.datetime, signal_type: str, price1: Union[float, Decimal], price2: Union[float, Decimal]) -> go.Figure:
        """Создаёт график с отметкой сигнала и точками пересечения"""
        try:
            price1 = float(price1)
            price2 = float(price2)
            signal_time = self._ensure_datetime(signal_time)
            
            if signal_type.lower() in ["short", "sell"]:
                stop_loss = max(price1, price2)
                take_profit = min(price1, price2)
            else:
                stop_loss = min(price1, price2)
                take_profit = max(price1, price2)
            
            df = self.load_data_for_signal(symbol, signal_time)
            
            entry_points = df[df["open_time"] >= signal_time]
            if entry_points.empty:
                raise ValueError("Нет данных для точки входа после сигнального времени")
            
            entry_point = entry_points.iloc[0]
            entry_price = entry_point["close"]
            
            tp_time, tp_price = self._find_price_cross(df, signal_time, take_profit)
            sl_time, sl_price = self._find_price_cross(df, signal_time, stop_loss)
            
            cross_time, cross_price, cross_type = None, None, None
            if tp_time and sl_time:
                if tp_time < sl_time:
                    cross_time, cross_price, cross_type = tp_time, tp_price, "Take-Profit"
                else:
                    cross_time, cross_price, cross_type = sl_time, sl_price, "Stop-Loss"
            elif tp_time:
                cross_time, cross_price, cross_type = tp_time, tp_price, "Take-Profit"
            elif sl_time:
                cross_time, cross_price, cross_type = sl_time, sl_price, "Stop-Loss"
            
            if cross_time:
                additional_minutes = 5
                additional_end_time = min(
                    self.now, 
                    cross_time + datetime.timedelta(minutes=additional_minutes))
                
                if additional_end_time > df["open_time"].max():
                    minutes_after = int((additional_end_time - signal_time).total_seconds() / 60)
                    df = self.load_data_for_signal(
                        symbol, 
                        signal_time,
                        minutes_after=minutes_after
                    )
            
            # Создание графика
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
                    name="Свечи",
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
                    hovertext=f"Точка входа<br>Время: {entry_point['open_time'].strftime('%Y-%m-%d %H:%M:%S')}<br>Цена: {entry_price:.8f}",
                ),
                row=1,
                col=1,
            )
            
            # Уровни SL и TP
            for price, color, name in [
                (stop_loss, self.COLORS["STOP_LOSS"], f"Stop-Loss ({stop_loss:.8f})"),
                (take_profit, self.COLORS["TAKE_PROFIT"], f"Take-Profit ({take_profit:.8f})"),
            ]:
                fig.add_trace(
                    go.Scatter(
                        x=df["open_time"],
                        y=[price] * len(df),
                        mode="lines",
                        line=dict(color=color, width=2, dash="dash"),
                        name=name,
                    ),
                    row=1,
                    col=1,
                )
            
            # Точка пересечения
            if cross_time:
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
                        hovertext=f"{cross_type}<br>Время: {cross_time.strftime('%Y-%m-%d %H:%M:%S')}<br>Цена: {cross_price:.8f}",
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
                ),
                row=2,
                col=1,
            )
            
            # Настройка оформления
            fig.update_layout(
                title=dict(
                    text=f"<b>{symbol}</b> | Сигнал: {signal_type} | Вход: {entry_price:.8f}",
                    y=0.95,
                    x=0.5,
                    xanchor="center",
                    yanchor="top",
                    font=dict(size=16),
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_color="black",
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
                showlegend=True,
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1
                ),
                height=800,
            )
            
            fig.update_yaxes(title_text="Цена", row=1, col=1)
            fig.update_yaxes(title_text="Объем", row=2, col=1)
            fig.update_xaxes(title_text="Дата", row=2, col=1)
            
            return fig
        
        except Exception as e:
            print(f"Ошибка при создании графика: {str(e)}")
            raise

    def save_signal_chart(self, symbol: str, signal_time: datetime.datetime, signal_type: str, price1: Union[float, Decimal], price2: Union[float, Decimal]) -> Optional[str]:
        """Создаёт график с сигналом и возвращает строку с HTML-кодом"""
        try:
            signal_time = self._ensure_datetime(signal_time)
            
            fig = self.create_signal_chart(symbol, signal_time, signal_type, price1, price2)
            
            html_str = fig.to_html(
                full_html=True,
                include_plotlyjs='cdn',
                default_height='80vh'
            )
            
            print("График с сигналом успешно сгенерирован")
            return html_str
            
        except Exception as e:
            print(f"Ошибка при создании графика для {symbol} ")
            return None
