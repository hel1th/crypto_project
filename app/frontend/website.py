import hashlib
import os
import sys
from streamlit.web import cli as stcli
from streamlit import runtime
import streamlit.components.v1 as components
import psycopg2
from psycopg2 import sql, OperationalError
import streamlit as st
from dotenv import load_dotenv
from app.frontend.exceptions import *
from decimal import Decimal
import datetime
import string
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
from app.binance.visualization import CryptoSignalVisualizer

load_dotenv()

data = [(1, "Free bitcoin", 50), (2, "Crypto Humster", 80)]
visualizer = CryptoSignalVisualizer()

selected_signals = [
    (
        1,
        "SPELLUSDT",
        "Short",
        Decimal("0.0006813"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 19, 43, 43),
        Decimal("0.000641"),
        Decimal("0.0006372"),
    ),
    (
        2,
        "DEXEUSDT",
        "Long",
        Decimal("13.429084"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 19, 43, 34),
        Decimal("14.332"),
        Decimal("14.414305"),
    ),
    (
        3,
        "ATAUSDT",
        "Long",
        Decimal("0.0462"),
        10,
        "Isolated",
        datetime.datetime(2025, 6, 2, 19, 43, 34),
        Decimal("0.0494"),
        Decimal("0.0496"),
    ),
]

column_names = [
    "ID",
    "Symbol",
    "Action",
    "Stop-loss",
    "Leverage",
    "Margin mode",
    "Signal time",
    "Entry price",
    "Take profit",
]


PASSWORD_SALT = os.getenv("PASSWORD_SALT")
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}
POSSIBLE_PASSWORD_CHARS = string.ascii_letters + string.digits + string.punctuation
POSSIBLE_USERNAME_CHARS = string.ascii_letters + string.digits + "'-_."
MIN_PASSWORD_LENGTH = 8


st.set_page_config(page_title="Крипто-аналитика", page_icon="💰", layout="centered")


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

        with psycopg2.connect(**DB_CONFIG) as conn:
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
        st.error("User not found.")
        return False


def is_user_exists(username) -> bool:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
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
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, hashed_password, salt FROM users WHERE email = %s",
                    (username,),
                )
                user = cur.fetchone()

                if user is None:
                    raise ValueError(f"Пользователь с email '{username}' не найден")

                return user
    except ValueError:
        return None
    except OperationalError as e:
        raise RuntimeError(f"Ошибка подключения к базе данных {e}")


def authentication_page():

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)

    with col1:
        with stylable_container(
            key="register_button_container",
            css_styles="""
            button {
                background-color: #9966cc; 
                border: 2px solid #c247ff;
                color: white;
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
                background-color: #f8f4ff;
                border: 2px solid #c247ff;
                color: #b114ff;
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


def get_channel_list() -> list:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, rate FROM channels ORDER BY id;")
                return cur.fetchall()
    except Exception as e:
        st.error(f"Ошибка при получении списка каналов: {e}")
        return []


def get_signals_by_channel(channel_id) -> list:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, symbol, action, stop_loss, leverage, margin_mode, signal_time, entry_prices, take_profits FROM trading_signals WHERE channel_id = %s ORDER BY signal_time DESC LIMIT 5;",
                    (channel_id,),
                )
                return cur.fetchall()
    except Exception as e:
        st.error(f"Ошибка при получении сигналов: {e}")
        return []


def grep_signal(signal_id):
    graphs_sqlq = """SELECT
        ts.symbol,
        ts.signal_time,
        ts.action,
        ts.stop_loss,
        (ts.take_profits->0)::float AS take_profit
    FROM trading_signals ts
    WHERE ts.id = %s;"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(graphs_sqlq, (signal_id,))
                return cur.fetchone()
    except Exception as e:
        st.error(f"Ошибка при получении данных сигнала: {e}")
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
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql)
                conn.commit()
        st.success("Успешно обновлены рейтинги каналов!")
    except OperationalError as e:
        st.error(f"Ошибка подключения к базе данных: {e}")
    except Exception as e:
        st.error(f"Ошибка при обновлении рейтингов: {e}")


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
        st.markdown("# 📈 Аналитика криптовалют")
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
        st.markdown("# Следи за курсом самых популярных криптовалют")
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

        update_channel_rates()
        data = get_channel_list()
        if not data:
            st.warning("Каналы не найдены. Проверьте подключение к базе данных.")
            return

        data_dict = {
            item[0]: f"{item[1]} (Процент успешности: {item[2]}%)" for item in data
        }
        choose_channel_option = list(data_dict.values())

        selected_channel = st.selectbox("Выберите канал:", choose_channel_option)
        selected_id = next(
            key for key, value in data_dict.items() if value == selected_channel
        )

        selected_signals = get_signals_by_channel(selected_id)
        if not selected_signals:
            st.warning("Сигналы для выбранного канала не найдены.")
            return

        df = pd.DataFrame(selected_signals, columns=column_names)
        st.dataframe(df, use_container_width=True, hide_index=True)

        index_list = [el[0] for el in selected_signals]
        selected_signal_id = st.selectbox("Выберите сигнал", index_list)
        st.write(f"Выбранный сигнал: {selected_signal_id}")

        data_for_graphic = grep_signal(selected_signal_id)
        if data_for_graphic:
            try:
                (
                    symbol,
                    signal_time,
                    signal_type,
                    stop_loss,
                    take_profit,
                ) = data_for_graphic
                path = visualizer.save_signal_chart(
                    symbol,
                    signal_time,
                    signal_type,
                    stop_loss,
                    take_profit,
                )
                if path:
                    components.html(path, height=4000)
                else:
                    st.error("Не удалось сгенерировать график.")
            except TypeError as e:
                st.error(
                    f"Ошибка в визуализации: неверное количество аргументов или тип данных ({e})."
                )
            except Exception as e:
                st.error(f"Ошибка при генерации графика: {e}")
        else:
            st.error("Данные для выбранного сигнала не найдены.")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    else:
        authentication_page()


if __name__ == "__main__":
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
