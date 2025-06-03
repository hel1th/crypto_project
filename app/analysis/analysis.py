import json
import pandas as pd
from decimal import Decimal
import datetime
import os
from dateutil import parser


def analysis(trade_signals: list):

    interval = "1s"
    res_signals = []

    for signal in trade_signals:

        (
            trade_id,
            symbol,
            signal,
            stop_loss,
            _,
            _,
            signal_time,
            entry_price,
            take_profit,
        ) = signal

        stop_loss = float(stop_loss)
        entry_price = float(entry_price)
        take_profit = float(take_profit)

        formatted_signal_time = signal_time.strftime("%d.%m.%y %H.%M.%S")

        file_path = os.path.join(os.path.dirname(__file__), f"{symbol}_{interval}.csv")
        data_binance = pd.read_csv(file_path)

        is_success = "unknown"

        if len(signal.split()) == 2:
            signal = str(signal.split()[0])

        filtered_data = data_binance.loc[
            data_binance["open_time"]
            > formatted_signal_time,
            ["open", "close", "open_time"],
        ]

        for row in filtered_data.itertuples():

            close = row[1]
            open_time = row[3]

            time = parser.parse(open_time)
            time = time.replace()
            time = time.replace(tzinfo=None) + datetime.timedelta(hours=3)

            open_time = time.strftime("%Y-%m-%d %H:%M:%S")

            if signal == "Long":

                if close <= stop_loss:
                    is_success = "fail"
                    break

                if close >= take_profit:
                    is_success = "success"
                    break

            if signal == "Short":
                if close >= stop_loss:
                    is_success = "fail"
                    break

                if close <= take_profit:
                    is_success = "success"
                    break

        res_signals.append(
            (trade_id, is_success)
        )
    print(res_signals)



trade_signals = [
    (
        1,
        "BTCUSDT",
        "Short",
        Decimal("0.8438094"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 20, 5, 58),
        Decimal("0.7938"),
        Decimal("0.7388811"),
    ),
    (
        2,
        "BTCUSDT",
        "Short",
        Decimal("0.0706788"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 19, 46, 54),
        Decimal("0.06649"),
        Decimal("0.0618899"),
    ),
    (
        3,
        "BTCUSDT",
        "Long Signal",
        Decimal("0.0462"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 20, 22, 17),
        Decimal("0.0479"),
        Decimal("0.0496"),
    ),
]
analysis(trade_signals)
