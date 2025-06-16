import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}
sql1 = """SELECT DISTINCT c.id, c.title FROM messages m JOIN channels c ON m.channel_id = c.id;"""
sql = """SELECT
    ts.id AS signal_id,
    ts.symbol,
    ts.action,
    ts.stop_loss,
    ts.leverage,
    ts.margin_mode,
    ts.signal_time,
    (
        SELECT price
        FROM signal_entry_prices sep
        WHERE sep.signal_id = ts.id
        ORDER BY sep.id ASC
        LIMIT 1
    ) AS entry_price,
    (
        SELECT price
        FROM signal_take_profits stp
        WHERE stp.signal_id = ts.id
        ORDER BY stp.id ASC
        LIMIT 1
    ) AS take_profit
FROM trading_signals ts
         JOIN channels c ON ts.channel_id = c.id
WHERE ts.channel_id = 1"""

sql2 = """SELECT
    ts.id AS signal_id,
    ts.symbol,
    ts.action,
    ts.stop_loss,
    ts.leverage,
    ts.margin_mode,
    ts.signal_time,
    c.title AS channel_title,
    jsonb_array_elements(ts.entry_prices)::float AS entry_price,
    jsonb_array_elements(ts.take_profits)::float AS take_profit_target
FROM trading_signals ts
JOIN channels c ON ts.channel_id = c.id
WHERE ts.channel_id = 1;"""
sql3 = f"""SELECT
    ts.symbol,
    ts.action,
    ts.signal_time,
    ts.stop_loss,
    jsonb_array_elements(ts.take_profits)::float AS take_profit_target
FROM trading_signals ts
JOIN channels c ON ts.channel_id = c.id
WHERE ts.id = {trade_id};"""

try:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql3)
            msg_entities = cur.fetchone()
            print(msg_entities)
except Exception as e:
    print(f"⚠️ Unluck u have an error: {e}")


# [('ETHBTC', 'Free Bitcoin'), (2, 'crypto_hamster')]
