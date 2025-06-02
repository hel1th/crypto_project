import psycopg2
from telethon.errors import ChannelInvalidError, ChannelPrivateError
from telethon.tl.types import User, Channel
from .config import DB_CONFIG, TZ, LIMIT
from .logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)


def get_or_create_channel(conn, username, title=None):
    """Get or create a channel in the channels table."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT id, title FROM channels WHERE username = %s", (username,)
            )
            result = cur.fetchone()
            if result:
                channel_id, existing_title = result
                if title and title != existing_title:
                    cur.execute(
                        "UPDATE channels SET title = %s WHERE id = %s",
                        (title, channel_id),
                    )
                    conn.commit()
                return channel_id
            else:
                cur.execute(
                    "INSERT INTO channels (username, title) VALUES (%s, %s) RETURNING id",
                    (username, title if title is not None else username),
                )
                channel_id = cur.fetchone()[0]
                conn.commit()
                return channel_id
        except Exception as e:
            logger.error(f"Error in get_or_create_channel for {username}: {e}")
            conn.rollback()
            raise


async def fetch_messages(
    client, channel_username: str, channel_id: int, limit: int = LIMIT
) -> list:
    """Fetch messages from a Telegram channel."""
    try:
        entity = await client.get_entity(channel_username)
        messages = []
        async for msg in client.iter_messages(entity, limit=limit):
            if (
                not msg.message
                or "% profit" in msg.message.lower()
                or "PREMIUM" in msg.message.lower()
            ):
                continue
            author = None
            if msg.sender:
                if isinstance(msg.sender, User):
                    author = (
                        msg.sender.username
                        or msg.sender.first_name
                        or str(msg.sender.id)
                    )
                elif isinstance(msg.sender, Channel):
                    author = msg.sender.title or str(msg.sender.id)
                else:
                    author = str(msg.sender.id)
            else:
                author = "Unknown"
            messages.append(
                {
                    "channel_id": channel_id,
                    "text": msg.message,
                    "date": msg.date.astimezone(tz=TZ),
                    "author": author,
                    "message_id": msg.id,
                }
            )
        return messages
    except ChannelPrivateError:
        print(f"❌ Канал {channel_username} является приватным.")
        return []
    except ChannelInvalidError:
        print(f"❌ Канал {channel_username} не найден.")
        return []
    except Exception as e:
        print(f"❌ Ошибка при получении сообщений из {channel_username}: {e}")
        return []


def save_batch_to_db(messages, channel):
    """Save a batch of messages to the database."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            try:
                query = """
                    INSERT INTO messages (channel_id, text, date, author, message_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (channel_id, message_id) DO NOTHING
                """
                data = [
                    (
                        msg["channel_id"],
                        msg["text"],
                        msg["date"],
                        msg["author"],
                        msg["message_id"],
                    )
                    for msg in messages
                ]
                cur.executemany(query, data)
                conn.commit()
                if cur.rowcount < len(messages):
                    print(
                        f"⚠️ Часть сообщений из канала {channel} не сохранена (дубликаты?)."
                    )
                else:
                    print(f"✅ Сохранено {cur.rowcount} сообщений из канала {channel}")
            except Exception as e:
                print(f"❌ Ошибка при сохранении в БД (канал {channel}): {e}")


def save_single_to_db(msg, channel):
    """Save a single message to the database."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            try:
                query = """
                    INSERT INTO messages (channel_id, text, date, author, message_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (channel_id, message_id) DO NOTHING
                """
                data = (
                    msg["channel_id"],
                    msg["text"],
                    msg["date"],
                    msg["author"],
                    msg["message_id"],
                )
                cur.execute(query, data)
                conn.commit()
                if cur.rowcount > 0:
                    print(f"📩 Новое сообщение сохранено (канал: {channel})")
            except Exception as e:
                print(
                    f"❌ Ошибка при сохранении нового сообщения из канала {channel}: {e}"
                )
