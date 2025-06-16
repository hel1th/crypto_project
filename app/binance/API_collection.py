import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pytz
import requests
import schedule


class CryptoDataCollector:
    def __init__(
        self,
        symbols=(
            "BTCUSDT",
            "ETHUSDT",
            "ZILUSDT",
            "DOTUSDT",
            "COMPUSDT",
            "BCHUSDT",
            "NEOUSDT",
            "APEUSDT",
        ),
        interval="1s",
        data_dir="app/binance/crypto_data",
    ):
        self.symbols = symbols
        self.data_dir = data_dir
        self.interval = interval
        self.initial_period = timedelta(days=1)

        os.makedirs(self.data_dir, exist_ok=True)

    def fetch_crypto_data(self, symbol, start_date=None, end_date=None, limit=1000):
        """Получение данных с Binance API с пагинацией (в московском времени)"""
        msk_tz = pytz.timezone("Europe/Moscow")
        utc_tz = pytz.utc

        start_date = (
            self._ensure_datetime(start_date, msk_tz)
            if start_date
            else datetime.now(msk_tz) - self.initial_period
        )
        end_date = (
            self._ensure_datetime(end_date, msk_tz)
            if end_date
            else datetime.now(msk_tz)
        )

        all_data = []
        current_start = start_date

        while current_start < end_date:
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
                    params={k: v for k, v in params.items() if v is not None},
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
                df["open_time"] = (
                    df["open_time"].dt.tz_localize("UTC").dt.tz_convert("Europe/Moscow")
                )

                all_data.append(df)

                if len(df) > 0:
                    last_time = df["open_time"].iloc[-1]
                    current_start = last_time.to_pydatetime() + timedelta(
                        milliseconds=1
                    )
                else:
                    break

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

            numeric_cols = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "count",
                "taker_buy_volume",
                "taker_buy_quote_volume",
            ]
            final_df[numeric_cols] = final_df[numeric_cols].apply(pd.to_numeric, axis=1)

            return final_df[["open", "high", "low", "close", "volume"]]

        return None

    def update_data(self):
        """Обновление данных"""
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Обновление данных...")

        for symbol in self.symbols:
            filepath = os.path.join(self.data_dir, f"{symbol}_{self.interval}.csv")

            if os.path.exists(filepath):
                df = pd.read_csv(filepath, index_col="open_time", parse_dates=True)
                last_date = df.index[-1]

                update_start = last_date
                update_end = update_start + self.initial_period

                new_data = self.fetch_crypto_data(
                    symbol, start_date=update_start, end_date=update_end, limit=1000
                )

                if new_data is not None and not new_data.empty:
                    new_data = new_data[new_data.index > last_date]

                    if not new_data.empty:
                        combined = pd.concat([df, new_data])
                        combined.to_csv(filepath)
                        print(f"Добавлено {len(new_data)} новых записей для {symbol}")
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

    def get_update_interval(self):
        """Определение интервала обновления на основе выбранного таймфрейма"""
        if self.interval == "1s":
            return 10
        elif self.interval == "1m":
            return 10
        elif self.interval == "1h":
            return 60
        return 10

    def _ensure_datetime(self, dt, tz):
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        if not isinstance(dt, datetime):
            raise ValueError(f"Unsupported time type: {type(dt)}")
        if dt.tzinfo is None:
            return tz.localize(dt)
        return dt.astimezone(tz)

    def run(self):
        """Запуск автоматического обновления"""
        self.update_data()

        update_interval = self.get_update_interval()
        schedule.every(update_interval).minutes.do(self.update_data)

        print(
            f"Автоматическое обновление запущено с интервалом {update_interval} минут"
        )

        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    collector = CryptoDataCollector()
    try:
        collector.run()
    except KeyboardInterrupt:
        print("\nРабота программы завершена")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
