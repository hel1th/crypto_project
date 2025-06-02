import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import schedule
from datetime import datetime

class CryptoDataVisualizer:
    def __init__(self, data_dir="app/binance/crypto_data", plot_dir=None):
        self.data_dir = data_dir
        self.plot_dir = plot_dir if plot_dir else os.path.join(data_dir, "plots")
        self.symbols = self._get_available_symbols()
        self.interval = self._detect_interval()
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.plot_dir, exist_ok=True)
        self._plots_initialized = False

    def _get_available_symbols(self):
        symbols = set()
        for file in os.listdir(self.data_dir):
            if file.endswith(".csv"):
                symbol = file.split("_")[0]
                symbols.add(symbol)
        return list(symbols)

    def _detect_interval(self):
        for file in os.listdir(self.data_dir):
            if file.endswith(".csv"):
                return file.split("_")[1].replace(".csv", "")
        return "1s"

    def create_chart(self, df, symbol):
        COLOR_BULL = 'rgba(0, 230, 210, 1.0)'
        COLOR_BEAR = 'rgba(255, 60, 60, 1.0)'
        
        df['color'] = np.where(df['open'] > df['close'], COLOR_BEAR, COLOR_BULL)
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.75, 0.25],
            specs=[[{"secondary_y": True}], [{}]]
        )
        
        # Настройки для свечей
        candle_settings = {
            'x': df.index,
            'open': df['open'],
            'high': df['high'],
            'low': df['low'],
            'close': df['close'],
            'increasing_line_color': COLOR_BULL,
            'decreasing_line_color': COLOR_BEAR,
            'increasing_fillcolor': COLOR_BULL,
            'decreasing_fillcolor': COLOR_BEAR,
            'name': 'Свечи',
            'whiskerwidth': 0.9,
            'line': {'width': 1},
            'hoverinfo': 'text',
            'hovertext': [
                f"<b>{symbol}</b><br>Дата: {x}<br>Открытие: {o:.8f}<br>Максимум: {h:.8f}<br>Минимум: {l:.8f}<br>Закрытие: {c:.8f}"
                for x, o, h, l, c in zip(df.index, df['open'], df['high'], df['low'], df['close'])
            ]
        }
        
        fig.add_trace(go.Candlestick(**candle_settings), row=1, col=1)
        
        # Линия цены открытия
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['open'],
            mode='lines',
            name='Цена открытия',
            line=dict(color='rgba(65, 105, 225, 0.7)', width=1.5),
            hoverinfo='text',
            hovertext=[f"Цена открытия: {y:.8f}" for y in df['open']]
        ), row=1, col=1)
        
        # Объемы
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['volume'],
            marker_color=df['color'],
            name='Объем',
            opacity=1.0,
            width=0.8, 
            hoverinfo='text',
            hovertext=[f"Объем: {y:.2f}" for y in df['volume']]
        ), row=2, col=1)

        fig.update_layout(
            title={
                'text': f'<b>{symbol}</b> - {self.interval} | Обновлено: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 16}
            },
            plot_bgcolor='white',
            paper_bgcolor='white',
            font_color='black',
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            showlegend=False,
            height=1000,
            margin=dict(l=50, r=50, t=100, b=50),
            hoverlabel=dict(
                bgcolor="rgba(255,255,255,0.9)",
                font_size=14,
                font_family="Arial",
                bordercolor='rgba(0,0,0,0.1)'
            )
        )
        
        # Настройки осей
        fig.update_yaxes(
            title_text="Цена",
            row=1, col=1,
            title_font=dict(size=14),
            tickfont=dict(size=12),
            gridcolor='rgba(0,0,0,0.05)'
        )
        fig.update_yaxes(
            title_text="Объем",
            row=2, col=1,
            title_font=dict(size=14),
            tickfont=dict(size=12),
            gridcolor='rgba(0,0,0,0.05)'
        )
        fig.update_xaxes(
            title_text="Дата",
            row=2, col=1,
            title_font=dict(size=14),
            tickfont=dict(size=12),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        return fig

    def update_plots(self):
        """Обновление всех графиков"""
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Обновление графиков...")
        
        if not self.symbols:
            print("Нет доступных символов для построения графиков")
            return
        
        for symbol in self.symbols:
            try:
                filepath = os.path.join(self.data_dir, f"{symbol}_{self.interval}.csv")
                if not os.path.exists(filepath):
                    print(f"Файл данных для {symbol} не найден: {filepath}")
                    continue
                
                df = pd.read_csv(filepath, index_col="open_time", parse_dates=True)
                if df.empty:
                    print(f"Нет данных для {symbol}")
                    continue
                    
                fig = self.create_chart(df, symbol)
                
                plot_path = os.path.join(self.plot_dir, f"{symbol}_interactive.html")
                fig.write_html(
                    plot_path,
                    full_html=True,
                    include_plotlyjs='cdn',
                    auto_open=False
                )
                
                print(f"График для {symbol} успешно обновлен: {plot_path}")
                
            except Exception as e:
                print(f"Ошибка при обновлении графика для {symbol}: {str(e)}")
        
        self._plots_initialized = True

    def get_update_interval(self):
        """Определение интервала обновления на основе интервала данных"""
        if self.interval == "1s":
            return 600
        elif self.interval == "1m":
            return 600  
        elif self.interval == "1h":
            return 3600 

    def run(self):
        """Запуск автоматического обновления графиков"""
        
        self.update_plots()
        
        update_interval = self.get_update_interval()
        schedule.every(update_interval).seconds.do(self.update_plots)

        print(f"Автоматическое обновление графиков запущено с интервалом {update_interval} секунд")

        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    visualizer = CryptoDataVisualizer()
    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("\nРабота программы завершена")
    except Exception as e:
        print(f"Произошла ошибка: {e}")