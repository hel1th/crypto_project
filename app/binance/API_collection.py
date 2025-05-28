import os
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
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
        data_dir="crypto_data",  # директория тоже не меняется
    ):
        self.symbols = self._select_symbols() if symbols is None else symbols
        self.data_dir = data_dir
        self.plot_dir = os.path.join(data_dir, "plots")

        self.valid_intervals = ["1s", "10s", "1m", "1h"]  # лучше делать через tuple
        if interval is None:
            print(f"Доступные интервалы: {', '.join(self.valid_intervals)}")
            while True:
                interval = input("Введите интервал (по умолчанию '1m'): ").strip()
                if not interval:
                    interval = "1m"
                    break
                if interval in self.valid_intervals:
                    break
                print(
                    f"Неверный интервал. Доступные варианты: {', '.join(self.valid_intervals)}"
                )

        self.interval = interval
        self.initial_period = timedelta(days=365)  # опять нельзя поменять этот период
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.plot_dir, exist_ok=True)

    def _select_symbols(self):
        """Интерактивный выбор криптовалютных пар"""
        popular_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "DOTUSDT",
            "MATICUSDT",
        ]  # тоже tuple

        print("\nПопулярные криптовалютные пары:")
        for i, symbol in enumerate(popular_symbols, 1):
            print(f"{i}. {symbol}")

        print("\nВведите номера пар через пробел (например '1 2 3' для BTC, ETH, BNB)")

        while True:
            user_input = input("Ваш выбор: ").strip()

            # Обработка выбора из списка
            if all(c.isdigit() for c in user_input.split()):
                selected = (
                    []
                )  # непонятно зачем создавать лист и переводить потому в тупл, если можно сразу
                for num in user_input.split():
                    idx = int(num) - 1
                    if 0 <= idx < len(popular_symbols):
                        selected.append(popular_symbols[idx])
                if selected:
                    return tuple(selected)

            print("Неверный ввод. Попробуйте снова.")

    def fetch_crypto_data(self, symbol, start_date=None, end_date=None):
        """Получение данных с Binance API с пагинацией"""
        if start_date is None:
            start_date = datetime.now() - self.initial_period

        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date) if end_date else datetime.now()

        all_data = []
        current_start = start_date

        while current_start < end_date:
            params = {
                "symbol": symbol,
                "interval": self.interval,
                "startTime": int(current_start.timestamp() * 1000),
                "limit": 1000,
            }

            if end_date:
                params["endTime"] = int(end_date.timestamp() * 1000)

            try:
                response = requests.get(
                    "https://api.binance.com/api/v3/klines", params=params
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                df = pd.DataFrame(
                    data,
                    columns=[
                        "open_time",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "close_time",
                        "quote_volume",
                        "count",
                        "taker_buy_volume",
                        "taker_buy_quote_volume",
                        "ignore",
                    ],
                )

                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                all_data.append(df)

                last_time = pd.to_datetime(df.iloc[-1]["open_time"], unit="ms")
                current_start = last_time + timedelta(milliseconds=1)

                # Для маленьких интервалов делаем паузу между запросами
                if self.interval in ["1s", "15s", "1m"]:  # снова тупл
                    time.sleep(0.1)

            except Exception as e:
                print(f"Ошибка при получении данных для {symbol}: {e}")
                break

        if all_data:
            final_df = pd.concat(all_data)
            final_df.set_index("open_time", inplace=True)
            numeric_cols = ["open", "high", "low", "close", "volume"]
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
                update_end = update_start + self.interval_timedelta * 2

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
        plt.bar(df.index, df["volume"], color="skyblue", alpha=0.7)
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

        # Устанавливаем расписание в соответствии с интервалом
        if self.interval == "1s":
            schedule.every(1).seconds.do(self.update_data)
        elif self.interval == "10s":
            schedule.every(10).seconds.do(self.update_data)
        elif self.interval == "1m":
            schedule.every(1).minutes.do(self.update_data)
        elif self.interval == "1h":
            schedule.every(1).hours.do(self.update_data)

        print(f"Автоматическое обновление запущено с интервалом {self.interval}")

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
