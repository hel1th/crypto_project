import asyncio
import psycopg2
import os
import logging
from datetime import datetime
from .auth_check import check_auth
from .config import TZ, LIMIT, DB_CONFIG, TG_SESSION_PATH
from .tg_utils import (
    get_or_create_channel,
    fetch_messages,
    save_batch_to_db,
    save_single_to_db,
)
from telethon import events
from telethon.tl.types import User, Channel
from .analyze.msg_process import get_last_msg, get_all_msg, analyze_all_db_msg
from .logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def setup_channels(client, conn, channels_input):
    """Setup channels for parsing and return a list of (channel, channel_id) tuples."""
    channels_to_parse = []
    for channel in [c.strip() for c in channels_input.split(",") if c.strip()]:
        try:
            entity = await client.get_entity(channel)
            channel_id = get_or_create_channel(conn, channel, entity.title)
            channels_to_parse.append((channel, channel_id))
        except Exception as e:
            logger.error(f"Не удалось добавить канал {channel}: {e}")
            print(f"❌ Не удалось добавить канал {channel}: {e}")
    return channels_to_parse


<<<<<<< app/telegram/main.py
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
            if not msg.message or "% profit" in msg.message.lower():
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
=======
async def run_parser(client, channels_to_parse, limit):
    """Run the parser for historical messages."""
    for channel, channel_id in channels_to_parse:
        print(f"⏳ Парсим {limit} прошлых сообщений из канала {channel}...")
        messages = await fetch_messages(client, channel, channel_id, limit)
        if messages:
            save_batch_to_db(messages, channel)
        print(
            f"✅ Спарсено и сохранено {len(messages)} прошлых сообщений из канала {channel}"
>>>>>>> app/telegram/main.py
        )


async def subscribe_to_channels(client, channels_to_parse):
    """Subscribe to new messages from channels."""
    entities = []
    for channel, channel_id in channels_to_parse:
        try:
            entity = await client.get_entity(channel)
            entities.append((channel, entity, channel_id))
        except Exception as e:
            logger.error(f"Ошибка при получении сущности канала {channel}: {e}")
            print(f"❌ Ошибка при получении сущности канала {channel}: {e}")

    for channel, entity, channel_id in entities:
        client.add_event_handler(
            lambda event: handle_new_message(event, channel, channel_id),
            events.NewMessage(chats=entity),
        )


async def handle_new_message(event, channel, channel_id):
    """Handle a new message event and save it to the database."""
    if not event.message.message or not isinstance(event.chat, Channel):
        return

    author = "Unknown"
    if event.message.sender:
        if isinstance(event.message.sender, User):
            author = (
                event.message.sender.username
                or event.message.sender.first_name
                or str(event.message.sender.id)
            )
        elif isinstance(event.message.sender, Channel):
            author = event.message.sender.title or str(event.message.sender.id)
        else:
            author = str(event.message.sender.id)

    new_message = {
        "author": author,
        "text": event.message.message,
        "date": event.message.date.astimezone(tz=TZ),
        "channel_id": channel_id,
        "message_id": event.message.id,
    }
    save_single_to_db(new_message, channel)
    last_msg = get_last_msg()
    if last_msg and isinstance(last_msg, (tuple, list)):  # Проверка на корректный тип
        analyze_all_db_msg([last_msg])  # Передаём как список с одним элементом
    else:
        logger.warning(f"Не удалось проанализировать последнее сообщение: {last_msg}")


async def main():
    """Main entry point for the Telegram parser."""
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

        channels_input = input(
            "Введите список каналов через запятую (e.g. @binance,joe_speen_youtube): "
        )
        input_channels = [
            channel.strip() for channel in channels_input.split(",") if channel.strip()
        ]
        if not input_channels:
            print("❌ Не указаны каналы для обработки.")
            return

        with psycopg2.connect(**DB_CONFIG) as conn:
            try:
                channels_to_parse = await setup_channels(client, conn, channels_input)
                if not channels_to_parse:
                    print("❌ Нет каналов для парсинга.")
                    return

                limit = (
                    input(
                        f"Количество сообщений для начального парсинга на канал ({LIMIT} по умолчанию): "
                    )
                    or LIMIT
                )
                limit = int(limit)

                await run_parser(client, channels_to_parse, limit)
                messages = get_all_msg()
                if messages:  # Проверка на None
                    analyze_all_db_msg(messages)
                else:
                    print("⚠️ Нет данных для анализа после парсинга.")

                await subscribe_to_channels(client, channels_to_parse)
                print(
                    f"🔔 Ожидание новых сообщений в каналах: {', '.join(c[0] for c in channels_to_parse)}..."
                )
                await client.run_until_disconnected()
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        print(f"❌ Ошибка: {e}")
