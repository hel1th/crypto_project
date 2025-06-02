import psycopg2

from ..config import DB_CONFIG
from .parse_messages import llm_parse_and_insert


def get_all_msg() -> tuple:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT id, channel_id, text, date FROM messages""")
                msg_entities = cur.fetchall()
                return msg_entities
    except Exception as e:
        print(f"⚠️ Unluck u have an error: {e}")


def get_last_msg() -> tuple:
    try:
        with psycopg2.connect(**DB_CONFIG) as con:
            with con.cursor() as cur:
                cur.execute(
                    """SELECT id, channel_id, text, date FROM messages ORDER BY id DESC LIMIT 1"""
                )
                msg_entity = cur.fetchone()
                return msg_entity
    except Exception as e:
        print(f"⚠️ Unluck u have an error: {e}")


def analyze_all_db_msg(msg_entities):
    for msg in msg_entities:
        if not msg or any(x is None for x in msg):
            continue
        llm_parse_and_insert(*msg)


if __name__ == "__main__":
    analyze_all_db_msg(get_all_msg())
