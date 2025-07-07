from typing import List
from app.binance.candles import process_signal_row
from app.binance.plotter import plot_candles_html
from app.config import INTERVALS_TO_DELTA, PASSWORD_SALT, DB_CONFIG
from app.frontend.exceptions import *
from decimal import Decimal
from psycopg import OperationalError
from streamlit import runtime
from streamlit_extras.stylable_container import stylable_container
from streamlit.web import cli as stcli
import asyncio
import hashlib
import os
import pandas as pd
import psycopg
import streamlit as st
import streamlit.components.v1 as components
import string
import sys

from app.types import Candle, Signal

COLUMN_NAMES = [
    "ID",
    "Symbol",
    "Action",
    "Stop-loss",
    "Leverage",
    "Margin mode",
    "Signal time",
    "Entry price",
    "Take profit",
    "Close time",
]


POSSIBLE_PASSWORD_CHARS = string.ascii_letters + string.digits + string.punctuation
POSSIBLE_USERNAME_CHARS = string.ascii_letters + string.digits + "'-_."
MIN_PASSWORD_LENGTH = 8


st.set_page_config(page_title="Cryptanalysis", page_icon="🐹", layout="wide")


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    salted_password = salt + password + PASSWORD_SALT
    hashed_password = hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
    return salt, hashed_password


def verify_password(password, stored_salt, stored_hash):
    salted_password = stored_salt + password + PASSWORD_SALT
    hashed_password = hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
    return hashed_password == stored_hash


def register_user(username, password):
    try:
        if not isinstance(username, str):
            raise TypeError("Username must be a string.")
        for char in username:
            if char not in POSSIBLE_USERNAME_CHARS:
                raise PossibleCharError(f"Invalid character in username: {char}")
        if username[0].isdigit():
            raise StartsWithDigitError("Username cannot start with a digit.")
        if is_user_exists(username):
            st.error("Username already exists.")
            return False

        if not isinstance(password, str):
            raise TypeError("Password must be a string.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise MinLengthError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        for char in password:
            if char not in POSSIBLE_PASSWORD_CHARS:
                raise PossibleCharError(f"Invalid character in password: {char}")
        if not any(char.isdigit() for char in password):
            raise NeedCharError("Password must contain at least one digit.")

        salt, password_hash = hash_password(password)

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (email, hashed_password, salt) VALUES (%s, %s, %s)",
                    (username, password_hash, salt),
                )
        st.success("User registered successfully!")
        return True

    except TypeError as e:
        st.error(f"Registration Error: {e}")
        return False
    except BadCharacterError as e:
        st.error(f"Registration Error: {e}")
        return False
    except StartsWithDigitError as e:
        st.error(f"Registration Error: {e}")
        return False
    except MinLengthError as e:
        st.error(f"Registration Error: {e}")
        return False
    except PossibleCharError as e:
        st.error(f"Registration Error: {e}")
        return False
    except NeedCharError as e:
        st.error(f"Registration Error: {e}")
        return False
    except Exception as e:
        st.error(f"Registration Error: An unexpected error occurred: {e}")
        return False


def login_user(username, password):
    user_data = get_user_data(username)
    if user_data:
        stored_username, stored_hash, stored_salt = user_data
        if verify_password(password, stored_salt, stored_hash):
            st.success("Login successful.")
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        else:
            st.error("Incorrect password.")
            return False
    else:
        st.error("User is not found.")
        return False


def is_user_exists(username) -> bool:
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email FROM users WHERE email = %s",
                    (username,),
                )
                user = cur.fetchone()

                if user is not None:
                    return True
                else:
                    return False
    except OperationalError as e:
        return False


def get_user_data(username):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, hashed_password, salt FROM users WHERE email = %s",
                    (username,),
                )
                user = cur.fetchone()

                if user is None:
                    raise ValueError(f"User with email '{username}' is not found")

                return user
    except ValueError:
        return None
    except OperationalError as e:
        raise RuntimeError(f"An error with connection to database: {e}")


def authentication_page():

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)

    with col1:
        with stylable_container(
            key="register_button_container",
            css_styles="""
            button {
                background-color: #533B77; 
                border: 2px solid #6A48D7;
                color: #181538;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 5px;
                width: 100%;
            }
            """,
        ):
            if st.button("Register"):
                if username and password:
                    register_user(username, password)
                else:
                    st.warning("Please enter both username and password.")
    with col2:
        with stylable_container(
            key="login_button_container",
            css_styles="""
            button {
                background-color: #0d0d0d;
                border: 2px solid #6A48D7;
                color: #6A48D7;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 5px;
                width: 100%;
                float: right; /* Align to the right */
            }
            """,
        ):
            if st.button("Login"):
                if username and password:
                    login_user(username, password)
                    if st.session_state.logged_in:
                        st.rerun()
                else:
                    st.warning("Please enter both username and password.")


def get_channel_list():
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, rate FROM channels ORDER BY id DESC;")
                rows = cur.fetchall()
                return rows
    except Exception as e:
        st.error(f"An error with getting the list of channels occurred: {e}")
        return []


def get_signals_by_channel(channel_id, limit: int = 5) -> list:
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, symbol, action, stop_loss, leverage, margin_mode, signal_time, entry_prices, take_profits, close_time \
                        FROM trading_signals WHERE channel_id = %s \
                        ORDER BY id DESC LIMIT %s;",
                    (channel_id, limit),
                )
                return cur.fetchall()
    except Exception as e:
        st.error(f"An error with getting signals: {e}")
        return []


def grep_signal_row(signal_id: int | str) -> Signal | None:
    graphs_sqlq = "SELECT * FROM trading_signals WHERE id = %s"
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(graphs_sqlq, (signal_id,))
                row = cur.fetchone()
                return Signal.from_row(row) if row else None
    except Exception as e:
        st.error(f"An error with getting data from signal: {e}")
        return None


def update_channel_rates() -> None:
    update_sql = """
    UPDATE channels
    SET rate = COALESCE((
        SELECT 
            ROUND(
                ((COUNT(*) FILTER (WHERE a.result = 'success')::NUMERIC / 
                  NULLIF(COUNT(*), 0)) * 100)::NUMERIC,
                2
            )
        FROM trading_signals ts
        JOIN analytics a ON a.trade_id = ts.id
        WHERE ts.channel_id = channels.id
    ), 0)
    WHERE EXISTS (
        SELECT 1
        FROM trading_signals ts
        JOIN analytics a ON a.trade_id = ts.id
        WHERE ts.channel_id = channels.id
    )
    OR rate IS NOT NULL;
    """
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql)
                conn.commit()
    except OperationalError as e:
        st.error(f"An error with connection to database: {e}")
    except Exception as e:
        st.error(f"An  error with rating update: {e}")


def main():
    # Стили заголовков
    with stylable_container(
        key="title",
        css_styles="""
        h1 {
            font-size: 47px;
            user-select: none;
            cursor: default;
        }
        """,
    ):
        st.markdown("# 📈 Cryptanalysis")
    with stylable_container(
        key="description",
        css_styles="""
        h1 {
            font-size: 20px;
            user-select: none;
            cursor: default;
            font-style: italic;
        }
        """,
    ):
        st.markdown("# Follow the rates of popular cryptocurrencies!")
    st.markdown(
        """
    <style>
    .spacer {
        margin-bottom: 13px;
    }
    </style>
    <div class='spacer'></div>
    """,
        unsafe_allow_html=True,
    )

    # Инициализация состояния
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None

    if st.session_state.logged_in:
        st.write(f"Welcome, {st.session_state.username}!")

        # TODO
        # update_channel_rates()
        data = get_channel_list()
        if not data:
            st.warning("Channels not found. Check the database connection.")
            return

        # TODO Temp removed
        # data_dict = {
        #     item[0]: f"{item[1]} (Процент успешности: {item[2]}%)" for item in data
        # }
        data_dict = {item[0]: f"{item[1]}" for item in data}
        choose_channel_option = list(data_dict.values())

        selected_channel = st.selectbox("Select the channel", choose_channel_option)
        selected_id = next(
            key for key, value in data_dict.items() if value == selected_channel
        )

        channel_signals = get_signals_by_channel(selected_id)
        if not channel_signals:
            st.warning("Signal for selected channel not found")
            return

        df = pd.DataFrame(channel_signals, columns=COLUMN_NAMES)
        st.dataframe(df, use_container_width=True, hide_index=True)

        index_list = [
            f"{el[1]} from channel: {selected_channel} id={el[0]}"
            for el in channel_signals
        ]
        selected_signal_str = st.selectbox("Select the signal", index_list)
        selected_signal_id = int(selected_signal_str.split("=")[-1])
        st.write(f"Selected signal: {selected_signal_id}")

        selected_signal_data = grep_signal_row(selected_signal_id)

        selected_candle_interval = st.selectbox(
            "Select the interval", INTERVALS_TO_DELTA.keys()
        )
        st.write(f"Selected interval: {selected_candle_interval}")
        if selected_signal_data:
            with st.spinner("Loading candles from Binance..."):
                try:
                    asyncio.run(
                        process_signal_row(
                            selected_signal_data, interval=selected_candle_interval
                        )
                    )
                    st.success("Candles successfully loaded!")
                    show_plot(
                        signal_data=selected_signal_data,
                        signal_id=selected_signal_id,
                        interval=selected_candle_interval,
                    )
                except Exception as e:
                    st.error(f"Error while loading candles: {e}")
        else:
            st.error("Could not receive signal data")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    else:
        authentication_page()


def show_plot(signal_data: Signal, signal_id: int, interval: str):
    try:
        candles = list()
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT * FROM candles c
                    JOIN 
                        trading_signals ts ON c.symbol = ts.symbol
                    WHERE 
                        ts.id = %s AND c.interval = %s AND c.time >= ts.signal_time
                    ORDER BY 
                        c.time""",
                    (signal_id, interval),
                )
                rows = cur.fetchall()
        candles: List[Candle] = [Candle.from_row(row) for row in rows]
        st.write(len(candles))

        plot_data = plot_candles_html(
            raw_candles=candles,
            symbol=signal_data.symbol,
            signal_time=signal_data.signal_time,
            entry_prices=signal_data.entry_prices,
            stop_loss=signal_data.stop_loss,
            take_profits=signal_data.take_profits,
            signal_id=signal_data.id,
        )
        if plot_data:
            components.html(
                plot_data,
                height=800,
            )
        else:
            st.error("Failed to draw chart")
    except TypeError as e:
        st.error(
            f"Error in visualization: wrong number of arguments or data type ({e})."
        )
    except Exception as e:
        st.error(f"Error while drawing a graphic: {e}")


if __name__ == "__main__":
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
