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

sql2 = """
SELECT
    ts.id AS signal_id,
    ts.symbol,
    ts.action,
    ts.stop_loss,
    ts.leverage,
    ts.margin_mode,
    ts.signal_time,
    ts.created_at,
    c.title AS channel_title,
    ARRAY_AGG(DISTINCT sep.price) FILTER (WHERE sep.price IS NOT NULL) AS entry_prices,
    ARRAY_AGG(DISTINCT stp.price) FILTER (WHERE stp.price IS NOT NULL) AS take_profit_targets
FROM trading_signals ts
         JOIN channels c ON ts.channel_id = c.id
         LEFT JOIN signal_entry_prices sep ON ts.id = sep.signal_id
         LEFT JOIN signal_take_profits stp ON ts.id = stp.signal_id
WHERE ts.channel_id = 1
GROUP BY
    ts.id, ts.symbol, ts.action, ts.stop_loss, ts.leverage,
    ts.margin_mode, ts.signal_time, ts.created_at, c.title;"""
try:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql2)
            msg_entities = cur.fetchall()
            print(msg_entities)
except Exception as e:
    print(f"⚠️ Unluck u have an error: {e}")


# [('ETHBTC', 'Free Bitcoin'), (2, 'crypto_hamster')]
