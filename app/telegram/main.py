import asyncio
import psycopg2
import os
import logging
from datetime import datetime
from auth_check import check_auth
from config import (
    TZ,
    LIMIT,
    DB_CONFIG,
    TG_SESSION_PATH,
)
from telethon.errors import ChannelInvalidError, ChannelPrivateError
from telethon import events
from telethon.tl.types import User, Channel

# Define table names
TABLE = "messages"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("telegram.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Ensure telethon logs are captured
logging.getLogger("telethon").setLevel(logging.INFO)


def get_or_create_channel(conn, username, title=None):
    """Get or create a channel in the channels table."""
    try:
        cur = conn.cursor()
        # Check if channel exists
        cur.execute("SELECT id, title FROM channels WHERE username = %s", (username,))
        result = cur.fetchone()
        if result:
            channel_id, existing_title = result
            # Update title if different and not None
            if title and title != existing_title:
                cur.execute(
                    "UPDATE channels SET title = %s WHERE id = %s", (title, channel_id)
                )
                conn.commit()
            return channel_id
        else:
            # Insert new channel, ensure title is not None
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
    finally:
        cur.close()


async def fetch_messages(
    client, channel_username: str, channel_id: int, limit: int = LIMIT
) -> list:
    try:
        entity = await client.get_entity(channel_username)
        messages = []
        async for msg in client.iter_messages(entity, limit=limit):
            if not msg.message:
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
                    "channel_id": channel_id,  # Use database-assigned channel_id
                    "text": msg.message,
                    "date": msg.date.astimezone(tz=TZ),  # Keep as datetime object
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
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = f"""
            INSERT INTO {TABLE} (channel_id, text, date, author, message_id)
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
            print(f"⚠️ Часть сообщений из канала {channel} не сохранена (дубликаты?).")
        else:
            print(f"✅ Сохранено {cur.rowcount} сообщений из канала {channel}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении в БД (канал {channel}): {e}")
    finally:
        cur.close()
        conn.close()


def save_single_to_db(msg, channel):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = f"""
            INSERT INTO {TABLE} (channel_id, text, date, author, message_id)
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
        print(f"❌ Ошибка при сохранении нового сообщения из канала {channel}: {e}")
    finally:
        cur.close()
        conn.close()


async def main():
    session_file = f"{TG_SESSION_PATH}.session"
    if not os.path.exists(session_file):
        print(
            f"⚠️ Файл сессии {session_file} не найден. Запустите session_saver.py для создания новой сессии."
        )
        return

    client = await check_auth()

    async with client:
        me = await client.get_me()
        print(f"👤 Ваш Telegram: {me.username or me.first_name}")

        # Get channels from user input
        channels_input = input(
            "Введите список каналов через запятую (e.g. @binance,joe_speen_youtube): "
        )
        input_channels = [
            channel.strip() for channel in channels_input.split(",") if channel.strip()
        ]
        if not input_channels:
            print("❌ Не указаны каналы для обработки.")
            return

        # Connect to database to manage channels
        conn = psycopg2.connect(**DB_CONFIG)
        channels_to_parse = []
        try:
            # Insert or update channels from input
            for channel in input_channels:
                try:
                    entity = await client.get_entity(channel)
                    channel_id = get_or_create_channel(conn, channel, entity.title)
                    channels_to_parse.append((channel, channel_id))
                except Exception as e:
                    print(f"❌ Не удалось добавить канал {channel}: {e}")

            # Fetch existing channels to parse
            cur = conn.cursor()
            cur.execute("SELECT username, id FROM channels")
            db_channels = cur.fetchall()
            if not db_channels:
                print("❌ Нет каналов в базе данных для парсинга.")
                return
            channels_to_parse = [
                (username, channel_id) for username, channel_id in db_channels
            ]
        except Exception as e:
            print(f"❌ Ошибка при обработке каналов: {e}")
            conn.rollback()
            return
        finally:
            cur.close()

        limit = input(
            f"Количество сообщений для начального парсинга на канал ({LIMIT} по умолчанию): "
        )
        limit = int(limit) if limit else LIMIT

        # Парсинг прошлых сообщений для всех каналов
        for channel, channel_id in channels_to_parse:
            print(f"⏳ Парсим {limit} прошлых сообщений из канала {channel}...")
            messages = await fetch_messages(client, channel, channel_id, limit)
            if messages:
                save_batch_to_db(messages, channel)
            print(
                f"✅ Спарсено и сохранено {len(messages)} прошлых сообщений из канала {channel}"
            )

        # Подписка на новые сообщения для всех каналов
        try:
            entities = []
            for channel, channel_id in channels_to_parse:
                try:
                    entity = await client.get_entity(channel)
                    entities.append((channel, entity, channel_id))
                except ChannelPrivateError:
                    print(
                        f"❌ Не могу подписаться на канал {channel}: он приватный, и вы не являетесь участником."
                    )
                except ChannelInvalidError:
                    print(f"❌ Канал {channel} не найден.")
                except Exception as e:
                    print(f"❌ Ошибка при получении сущности канала {channel}: {e}")

            for channel, entity, channel_id in entities:

                @client.on(events.NewMessage(chats=entity))
                async def handle_new_message(event, ch=channel, ch_id=channel_id):
                    if not event.message.message:
                        return
                    if not isinstance(event.chat, Channel):
                        return

                    author = None
                    if event.message.sender:
                        if isinstance(event.message.sender, User):
                            author = (
                                event.message.sender.username
                                or event.message.sender.first_name
                                or str(event.message.sender.id)
                            )
                        elif isinstance(event.message.sender, Channel):
                            author = event.message.sender.title or str(
                                event.message.sender.id
                            )
                        else:
                            author = str(event.message.sender.id)
                    else:
                        logger.info(
                            f"Sender is None for message {event.message.id} in channel {ch}"
                        )
                        author = "Unknown"

                    new_message = {
                        "author": author,
                        "text": event.message.message,
                        "date": event.message.date.astimezone(
                            tz=TZ
                        ),  # Keep as datetime object
                        "channel_id": ch_id,
                        "message_id": event.message.id,
                    }
                    save_single_to_db(new_message, ch)

            print(
                f"🔔 Ожидание новых сообщений в каналах: {', '.join(c[0] for c in channels_to_parse)}..."
            )
            await client.run_until_disconnected()
        except Exception as e:
            print(f"❌ Ошибка при подписке на каналы: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
