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
        symbols=[
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
        ],  # Переделать логику, нельзя ставить деф значением список (None, tuple ONLY)
        interval="1m",
        data_dir="app/binance/crypto_data",
    ):
        self.symbols = symbols
        self.interval = interval
        self.data_dir = data_dir
        self.plot_dir = os.path.join(data_dir, "plots")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.plot_dir, exist_ok=True)

    def fetch_crypto_data(self, symbol, start_date=None):  # вот тут хорошо с None
        """Получение данных с Binance API"""
        if start_date is None:
            # По умолчанию - последние 365 дней
            start_date = (datetime.now() - timedelta(days=365)).strftime(
                "%Y-%m-%d"
            )  # Добавить возможность изменения в том числе не в днях, а в других единицах через юзер инпут
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": self.interval,
            "startTime": int(pd.to_datetime(start_date).timestamp() * 1000),
            "limit": 1000,
        }

        try:
            response = requests.get(
                url, params=params
            )  # Назначить timeout здесь или в params
            response.raise_for_status()
            data = response.json()

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
            df.set_index("open_time", inplace=True)
            numeric_cols = ["open", "high", "low", "close", "volume"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)

            return df[["open", "high", "low", "close", "volume"]]

        except Exception as e:
            print(f"Ошибка при получении данных для {symbol}: {e}")
            return None

    def update_data(self):
        """Обновление данных и графиков"""
        print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Начало обновления данных..."
        )

        for symbol in self.symbols:
            filepath = os.path.join(self.data_dir, f"{symbol}.csv")
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, index_col="open_time", parse_dates=True)
                last_date = df.index[-1].strftime("%Y-%m-%d")
                new_data = self.fetch_crypto_data(symbol, last_date)  # опять вызов без возможности менять start_date

                if new_data is not None and not new_data.empty:
                    combined = pd.concat([df, new_data]).loc[
                        ~df.index.duplicated(keep="last")
                    ]
                    combined.to_csv(filepath)
                    print(
                        f"Данные для {symbol} обновлены. Добавлено {len(new_data)} записей"
                    )
                    self.generate_plots(combined, symbol)
                else:
                    print(f"Нет новых данных для {symbol}")
            else:
                df = self.fetch_crypto_data(symbol)  # опять вызов без возможности менять start_date
                if df is not None:
                    df.to_csv(filepath)
                    print(f"Создан новый файл данных для {symbol}")
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

    def daily_update(self):  # хотелось бы иметь периодическое обновление, период которого тоже задает пользователь, или, хотя бы, через код
        """Ежедневное обновление"""
        self.update_data()
        print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Данные и графики обновлены"
        )  

    def run(self):
        """Запуск автоматического обновления"""
        self.daily_update()
        schedule.every().day.at("00:00").do(self.daily_update)  # опять хардкод, как и в принте ниже, изменить для любого промежутка времени

        print(
            "Система мониторинга запущена. Графики будут обновляться ежедневно в 00:00" 
        )  # тут менять формулировку типа обновление графиков каждые {offset} [секунд/минут/часов/дней]

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    visualizer = CryptoDataVisualizer()  # вот сюда добавить возможность через инпут менять параметры объекта класса

    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("\nРабота программы завершена")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
