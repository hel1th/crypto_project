from .parse_messages import llm_parse_and_insert
from app.config import DB_CONFIG
import logging
import psycopg

logger = logging.getLogger(__name__)


def get_all_msg():
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, channel_id, text, date FROM messages")
                msg_entities = cur.fetchall()
                return msg_entities
    except Exception as e:
        logger.error(f"Ошибка в get_all_msg: {e}")
        return ()  # Возвращаем пустой кортеж в случае ошибки


def get_not_proccesed_msgs():
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT msg.id, msg.channel_id, msg.text, msg.date
                    FROM messages msg
                    LEFT JOIN trading_signals ts ON ts.id = msg.id WHERE ts.id is NULL;"""
                )
                msg_entities = cur.fetchall()
                return msg_entities
    except Exception as e:
        logger.error(f"Ошибка в get_all_msg: {e}")
        return ()


def get_last_msg() -> tuple | None:
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, channel_id, text, date FROM messages ORDER BY id DESC LIMIT 1"""
                )
                msg_entity = cur.fetchone()
                return msg_entity
    except Exception as e:
        logger.error(f"Ошибка в get_last_msg: {e}")
        return None


def analyze_all_db_msg(msg_entities):
    if not msg_entities:
        logger.warning("Нет сообщений для анализа")
        return
    for msg in msg_entities:
        if not msg or any(x is None for x in msg):
            logger.warning(f"Пропущено сообщение из-за некорректных данных: {msg}")
            continue
        try:
            llm_parse_and_insert(*msg)
        except Exception as e:
            logger.error(f"Ошибка при анализе сообщения {msg}: {e}")


if __name__ == "__main__":
    analyze_all_db_msg(get_all_msg())
