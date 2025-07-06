from app.config import DB_CONFIG, TZ, LIMIT
from telethon.errors import ChannelInvalidError, ChannelPrivateError
from telethon.tl.types import PeerChannel
import logging
import psycopg

logger = logging.getLogger(__name__)


def get_or_create_channel(conn, username, title=None):
    """Get or create a channel in the channels table."""
    with conn.cursor() as cur:
        try:
            username = username if username.startswith("@") else f"@{username}"
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
    client, conn, channel_username: str, channel_id: int, limit: int = LIMIT
) -> list:
    """Fetch messages from a Telegram channel, processing only forwarded messages from other channels."""
    try:
        entity = await client.get_entity(channel_username)
        messages = []
        async for msg in client.iter_messages(entity, limit=limit):
            if (
                not msg.message
                or "% profit" in msg.message.lower()
                or "premium" in msg.message.lower()
            ):
                logger.debug(
                    f"Пропущено сообщение {msg.id}: отсутствует текст или содержит '% profit'/'premium'"
                )
                continue

            # Пропускаем сообщения, которые не являются пересылками из каналов
            if not msg.fwd_from or not isinstance(msg.fwd_from.from_id, PeerChannel):
                logger.debug(f"Пропущено сообщение {msg.id}: не пересылка из канала")
                continue

            author = None
            original_channel_id = channel_id
            message_id = (
                msg.fwd_from.channel_post if msg.fwd_from.channel_post else msg.id
            )
            date = (
                msg.fwd_from.date.astimezone(tz=TZ)
                if msg.fwd_from.date
                else msg.date.astimezone(tz=TZ)
            )

            # Извлекаем данные оригинального канала
            try:
                original_channel = await client.get_entity(msg.fwd_from.from_id)
                original_channel_id = get_or_create_channel(
                    conn,
                    original_channel.username or str(original_channel.id),
                    original_channel.title,
                )
                author = original_channel.title or str(original_channel.id)
            except ChannelPrivateError:
                original_channel_id = get_or_create_channel(
                    conn,
                    f"channel_{msg.fwd_from.from_id.channel_id}",
                    f"Private Channel {msg.fwd_from.from_id.channel_id}",
                )
                author = msg.fwd_from.from_name or msg.post_author or "Unknown"
            except Exception as e:
                logger.error(
                    f"Ошибка при получении оригинального канала для сообщения {msg.id}: {e}"
                )
                author = msg.fwd_from.from_name or msg.post_author or "Unknown"
                continue  # Пропускаем сообщение, если канал недоступен

            messages.append(
                {
                    "channel_id": original_channel_id,
                    "text": msg.message,
                    "date": date,
                    "author": author,
                    "message_id": message_id,
                }
            )
            logger.debug(
                f"Добавлено сообщение: channel_id={original_channel_id}, message_id={message_id}, author={author}"
            )
        return messages
    except ChannelPrivateError:
        logger.error(f"Канал {channel_username} является приватным.")
        print(f"Канал {channel_username} является приватным.")
        return []
    except ChannelInvalidError:
        logger.error(f"Канал {channel_username} не найден.")
        print(f"Канал {channel_username} не найден.")
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений из {channel_username}: {e}")
        print(f"Ошибка при получении сообщений из {channel_username}: {e}")
        return []


def save_batch_to_db(messages, channel):
    """Save a batch of messages to the database."""
    with psycopg.connect(**DB_CONFIG) as conn:
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
                        f"Часть сообщений из канала {channel} не сохранена (дубликаты?)."
                    )
                else:
                    print(f"Сохранено {cur.rowcount} сообщений из канала {channel}")
            except Exception as e:
                print(f"Ошибка при сохранении в БД (канал {channel}): {e}")


def save_single_to_db(msg, channel):
    """Save a single message to the database."""
    with psycopg.connect(**DB_CONFIG) as conn:
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
                    print(f"Новое сообщение сохранено (канал: {channel})")
            except Exception as e:
                print(
                    f"Ошибка при сохранении нового сообщения из канала {channel}: {e}"
                )
