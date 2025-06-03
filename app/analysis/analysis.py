import json
import pandas as pd
from app.parse_llm.parse_messages import llm_parse
from decimal import Decimal
import datetime
import os
from dateutil import parser


def analysis(trade_signals: list):

    interval = "1s"
    res_signals_dict = []

    for signal in trade_signals:

        take_profits, entry_prices = list(), list()

        (
            trade_id,
            symbol,
            signal,
            stop_loss,
            _,
            _,
            signal_time,
            entry_prices,
            take_profits,
        ) = signal

        stop_loss = float(stop_loss)
        entry_prices = [float(price_i) for price_i in entry_prices]
        take_profits = [float(profit_i) for profit_i in take_profits]

        formatted_signal_time = signal_time.strftime("%d.%m.%y %H.%M.%S")

        # создаем файл с данными по монете за 1 секунду и читаем его

        # fetch_crypto_data(symbol[:len(symbol) - 3], formatted_signal_time, interval) # need to add 5-10 mins to time

        file_path = os.path.join(os.path.dirname(__file__), f"{symbol}_{interval}.csv")
        data_binance = pd.read_csv(file_path)

        is_success = "unknown"
        parameter_achieved = "none"
        time_achieved = None

        if len(signal.split()) == 2:
            signal = str(signal.split()[0])

        filtered_data = data_binance.loc[
            data_binance["open_time"].strftime("%d.%m.%y %H.%M.%S")
            > formatted_signal_time,
            ["open", "close", "open_time"],
        ]
        print(filtered_data)

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
                    time_achieved = open_time
                    parameter_achieved = "stop_loss"
                    break

                if any([close >= profit for profit in take_profits]):
                    is_success = "success"
                    time_achieved = open_time
                    parameter_achieved = "take_profit"
                    break

            if signal == "Short":
                if close >= stop_loss:
                    is_success = "fail"
                    parameter_achieved = "stop_loss"
                    time_achieved = open_time
                    break

                if any([close <= profit for profit in take_profits]):
                    is_success = "success"
                    parameter_achieved = "take_profit"
                    time_achieved = open_time
                    break

        text_to_show = f"{signal} signal, {parameter_achieved} achieved first. Signal is {is_success}"
        res_signals_dict.append(
            (trade_id, is_success, time_achieved, text_to_show, symbol)
        )
        # время выхода сигнала, две цены, тип сигнала
        print(res_signals_dict)

    with open("signals_analitics.json", "w", encoding="UTF-8") as json_file:
        json.dump(res_signals_dict, json_file, ensure_ascii=True, indent=4)


trade_signals = [
    (
        1,
        "BTCUSDT",
        "Short",
        Decimal("0.8438094"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 20, 5, 58),
        [Decimal("0.7938"), Decimal("0.817614")],
        [
            Decimal("0.7388811"),
            Decimal("0.7556375"),
            Decimal("0.772394"),
            Decimal("0.7891505"),
        ],
    ),
    (
        2,
        "BTCUSDT",
        "Short",
        Decimal("0.0706788"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 19, 46, 54),
        [Decimal("0.06649"), Decimal("0.0684847")],
        [
            Decimal("0.0618899"),
            Decimal("0.0632934"),
            Decimal("0.064697"),
            Decimal("0.0661005"),
        ],
    ),
    (
        3,
        "BTCUSDT",
        "Long Signal",
        Decimal("0.0462"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 20, 22, 17),
        [Decimal("0.0479"), Decimal("0.0494")],
        [Decimal("0.0496"), Decimal("0.0507"), Decimal("0.0517"), Decimal("0.0527")],
    ),
]
analysis(trade_signals)
