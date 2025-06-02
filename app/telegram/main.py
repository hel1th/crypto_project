# app/telegram/main.py
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
            print(f"❌ Не удалось добавить канал {channel}: {e}")
    return channels_to_parse


async def run_parser(client, channels_to_parse, limit):
    """Run the parser for historical messages."""
    for channel, channel_id in channels_to_parse:
        print(f"⏳ Парсим {limit} прошлых сообщений из канала {channel}...")
        messages = await fetch_messages(client, channel, channel_id, limit)
        if messages:
            save_batch_to_db(messages, channel)
        print(
            f"✅ Спарсено и сохранено {len(messages)} прошлых сообщений из канала {channel}"
        )


async def subscribe_to_channels(client, channels_to_parse):
    """Subscribe to new messages from channels."""
    entities = []
    for channel, channel_id in channels_to_parse:
        try:
            entity = await client.get_entity(channel)
            entities.append((channel, entity, channel_id))
        except Exception as e:
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
    analyze_all_db_msg(get_last_msg())


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
                print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
