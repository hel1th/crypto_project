import os
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import pytz
import requests
import schedule
import seaborn as sns
from matplotlib import rcParams

plt.style.use("seaborn-v0_8")
rcParams["figure.figsize"] = 12, 6
sns.set_theme(style="whitegrid")


class CryptoDataVisualizer:
    def __init__(
        self,
        symbols=None,
        interval=None,
        data_dir="app/binance/crypto_data",
    ):
        self.symbols = self._select_symbols() if symbols is None else symbols
        self.data_dir = data_dir
        self.plot_dir = os.path.join(data_dir, "plots")

        self.valid_intervals = ("1s", "1m", "1h")
        if interval is None:
            print(f"Доступные интервалы: {', '.join(self.valid_intervals)}")
            while True:
                interval = input("Введите интервал (по умолчанию '1m'): ").strip()
                if not interval:
                    interval = "1m"
                    break
                if interval in self.valid_intervals:
                    break
                print(f"Неверный интервал. Доступные варианты: {', '.join(self.valid_intervals)}")

        self.interval = interval
        past_period = input("Укажите период, за который нажно отобразить статистику, в днях (только число): ")
        if past_period.isdigit:
                self.initial_period = timedelta(days=int(past_period))
        else:
            print("Неверный период, автоматически установлен период в 1 год")
            self.initial_period = timedelta(days=365)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.plot_dir, exist_ok=True)

    def _select_symbols(self):
        """Интерактивный выбор криптовалютных пар"""
        popular_symbols =( 
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "DOTUSDT",
            "MATICUSDT",
            )

        print("\nПопулярные криптовалютные пары:")
        for i, symbol in enumerate(popular_symbols, 1):
            print(f"{i}. {symbol}")

        print("\nВведите номера пар через пробел (например '1 2 3' или BTC ETH BNB)")

        while True:
            user_input = input("Ваш выбор: ").strip()

            if all(c.isdigit() for c in user_input.split()):
                selected = set()
                for num in user_input.split():
                    idx = int(num) - 1
                    if 0 <= idx < len(popular_symbols):
                        selected.add(popular_symbols[idx])
                if selected:
                    return tuple(selected)
            elif all(c.isalpha() for c in user_input.split()):
                selected = set()
                for coin in user_input.split():
                    coin += "USDT"
                    selected.add(coin)
                if selected:
                    return tuple(selected)

            print("Неверный ввод. Попробуйте снова.")

    def fetch_crypto_data(self, symbol, start_date=None, end_date=None, limit=1000):
        """Получение данных с Binance API с пагинацией (в московском времени)"""
        msk_tz = pytz.timezone('Europe/Moscow')
        utc_tz = pytz.utc
        
        if start_date is None:
            start_date = datetime.now(msk_tz) - self.initial_period
        else:
            # Конвертируем в московское время
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if start_date.tzinfo is None:
                start_date = msk_tz.localize(start_date)
            else:
                start_date = start_date.astimezone(msk_tz)
        
        if end_date is None:
            end_date = datetime.now(msk_tz)
        else:
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            if end_date.tzinfo is None:
                end_date = msk_tz.localize(end_date)
            else:
                end_date = end_date.astimezone(msk_tz)

        all_data = []
        current_start = start_date

        while current_start < end_date:
            # Конвертируем в UTC для запроса к Binance
            utc_start = current_start.astimezone(utc_tz)
            utc_end = end_date.astimezone(utc_tz)
            
            params = {
                "symbol": symbol.upper(),
                "interval": self.interval,
                "startTime": int(utc_start.timestamp() * 1000),
                "limit": limit,
            }
            
            if end_date:
                params["endTime"] = int(utc_end.timestamp() * 1000)
            
            try:
                response = requests.get(
                    "https://api.binance.com/api/v3/klines", 
                    params={k: v for k, v in params.items() if v is not None}
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                df = pd.DataFrame(
                    data,
                    columns=[
                        "open_time", "open", "high", "low", "close", "volume",
                        "close_time", "quote_volume", "count",
                        "taker_buy_volume", "taker_buy_quote_volume", "ignore",
                    ],
                )
                
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df["open_time"] = df["open_time"].dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')
                
                all_data.append(df)

                if len(df) > 0:
                    last_time = df["open_time"].iloc[-1]
                    current_start = last_time.to_pydatetime() + timedelta(milliseconds=1)
                else:
                    break

                # Пауза между запросами
                if self.interval in ("1s", "15s", "1m", "3m", "5m"):
                    time.sleep(0.2)

            except requests.exceptions.HTTPError as e:
                print(f"HTTP ошибка при получении данных для {symbol}: {e}")
                if response.status_code == 429:
                    time.sleep(10)
                    continue
                break
            except Exception as e:
                print(f"Ошибка при получении данных для {symbol}: {e}")
                break

        if all_data:
            final_df = pd.concat(all_data)
            final_df.set_index("open_time", inplace=True)
            
            numeric_cols = ["open", "high", "low", "close", "volume", 
                        "quote_volume", "count", 
                        "taker_buy_volume", "taker_buy_quote_volume"]
            final_df[numeric_cols] = final_df[numeric_cols].apply(pd.to_numeric, axis=1)
            
            return final_df[["open", "high", "low", "close", "volume"]]

        return None

    def update_data(self):
        """Обновление данных и графиков"""
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Обновление данных...")

        for symbol in self.symbols:
            filepath = os.path.join(self.data_dir, f"{symbol}_{self.interval}.csv")

            if os.path.exists(filepath):
                # Читаем существующие данные
                df = pd.read_csv(filepath, index_col="open_time", parse_dates=True)
                last_date = df.index[-1]

                update_start = last_date
                update_end = update_start + self.initial_period

                # Получаем только новые данные за прошедший интервал
                new_data = self.fetch_crypto_data(
                    symbol, start_date=update_start, end_date=update_end, limit=1000
                )

                if new_data is not None and not new_data.empty:
                    # Фильтруем только действительно новые данные (после last_date)
                    new_data = new_data[new_data.index > last_date]

                    if not new_data.empty:
                        combined = pd.concat([df, new_data])
                        combined.to_csv(filepath)
                        print(f"Добавлено {len(new_data)} новых записей для {symbol}")
                        self.generate_plots(combined, symbol)
                    else:
                        print(
                            f"Нет новых данных для {symbol} (ожидался интервал {self.interval})"
                        )
                else:
                    print(f"Не удалось получить новые данные для {symbol}")
            else:
                df = self.fetch_crypto_data(symbol)
                if df is not None:
                    df.to_csv(filepath)
                    print(
                        f"Создан новый файл данных для {symbol} (интервал: {self.interval})"
                    )
                    self.generate_plots(df, symbol)

    def generate_plots(self, df, symbol):
        """Генерация графиков"""
        print(f"Генерация графиков для {symbol}...")

        # Основной график цен
        plt.figure(figsize=(14, 7))
        plt.plot(df["close"], label="Цена закрытия", linewidth=2, color="royalblue")
        plt.title(f"История цен {symbol}", fontsize=16, pad=20)
        plt.xlabel("Дата", fontsize=12)
        plt.ylabel("Цена (USDT)", fontsize=12)
        plt.legend(frameon=True, facecolor="white")
        plt.grid(True, alpha=0.3)
        plt.savefig(
            os.path.join(self.plot_dir, f"{symbol}_price.png"),
            bbox_inches="tight",
            dpi=100,
        )
        plt.close()

        # График объема торгов
        plt.figure(figsize=(14, 5))
        plt.plot(df["volume"], linewidth=2, color="royalblue")
        plt.title(f"Объем торгов {symbol}", fontsize=16, pad=20)
        plt.xlabel("Дата", fontsize=12)
        plt.ylabel("Объем", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(
            os.path.join(self.plot_dir, f"{symbol}_volume.png"),
            bbox_inches="tight",
            dpi=100,
        )
        plt.close()

    def interval_update(self):
        """Обновление данных в соответствии с выбранным интервалом"""
        self.update_data()
        print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Обновление завершено\n"
        )

    def run(self):
        """Запуск автоматического обновления"""
        self.update_data()

        if self.interval == "1s":
            update_interval = "10m"
            schedule.every(10).minutes.do(self.update_data)
        elif self.interval == "1m":
            update_interval = "10m"
            schedule.every(10).minutes.do(self.update_data)
        elif self.interval == "1h":
            update_interval = "1h"
            schedule.every(1).hours.do(self.update_data)

        print(f"Автоматическое обновление запущено с интервалом {update_interval}")

        while True:
            schedule.run_pending()
            time.sleep(0.1)


if __name__ == "__main__":
    visualizer = (
        CryptoDataVisualizer()
    )  # (менять параметры объекта класса) выбираем в init

    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("\nРабота программы завершена")
    except Exception as e:
        print(f"Произошла ошибка: {e}")