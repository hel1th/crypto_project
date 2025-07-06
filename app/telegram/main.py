from .analyze.msg_process import (
    get_last_msg,
    get_not_proccesed_msgs,
    analyze_all_db_msg,
)
from .auth_check import check_auth
from .logging_config import setup_logging
from .tg_utils import (
    get_or_create_channel,
    fetch_messages,
    save_batch_to_db,
    save_single_to_db,
)
from app.config import TZ, LIMIT, DB_CONFIG, TG_SESSION_PATH
from telethon import events
from telethon.errors import ChannelPrivateError
from telethon.tl.types import Channel, PeerChannel
import asyncio
import logging
import os
import psycopg

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
            print(f"Не удалось добавить канал {channel}: {e}")
    return channels_to_parse


async def run_parser(client, conn, channels_to_parse, limit):
    """Run the parser for historical messages."""
    for channel, channel_id in channels_to_parse:
        print(f"⏳ Парсим {limit} прошлых сообщений из канала {channel}...")
        messages = await fetch_messages(client, conn, channel, channel_id, limit)
        if messages:
            save_batch_to_db(messages, channel)
        print(f"✅ Cохранено {len(messages)} прошлых сообщений из канала {channel}")


async def subscribe_to_channels(client, channels_to_parse):
    """Subscribe to new messages from channels."""
    entities = []
    for channel, channel_id in channels_to_parse:
        try:
            entity = await client.get_entity(channel)
            entities.append((channel, entity, channel_id))
        except Exception as e:
            logger.error(f"Ошибка при получении сущности канала {channel}: {e}")
            print(f"Ошибка при получении сущности канала {channel}: {e}")

    for channel, entity, channel_id in entities:
        client.add_event_handler(
            lambda event, ch=channel, ch_id=channel_id: handle_new_message(
                event, ch, ch_id
            ),
            events.NewMessage(chats=entity),
        )


async def handle_new_message(event, channel, channel_id):
    """Handle a new message event, processing only forwarded messages from other channels."""
    if not event.message.message or not isinstance(event.chat, Channel):
        logger.debug(
            f"Пропущено сообщение {event.message.id}: отсутствует текст или не из канала"
        )
        return

    if not event.message.fwd_from or not isinstance(
        event.message.fwd_from.from_id, PeerChannel
    ):
        logger.debug(f"Пропущено сообщение {event.message.id}: не пересылка из канала")
        return

    author = None
    original_channel_id = channel_id
    message_id = (
        event.message.fwd_from.channel_post
        if event.message.fwd_from.channel_post
        else event.message.id
    )
    date = (
        event.message.fwd_from.date.astimezone(tz=TZ)
        if event.message.fwd_from.date
        else event.message.date.astimezone(tz=TZ)
    )

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            original_channel = await event.client.get_entity(
                event.message.fwd_from.from_id
            )
            original_channel_id = get_or_create_channel(
                conn,
                original_channel.username or str(original_channel.id),
                original_channel.title,
            )
            author = original_channel.title or str(original_channel.id)
    except ChannelPrivateError:
        with psycopg.connect(**DB_CONFIG) as conn:
            original_channel_id = get_or_create_channel(
                conn,
                f"channel_{event.message.fwd_from.from_id.channel_id}",
                f"Private Channel {event.message.fwd_from.from_id.channel_id}",
            )
            author = (
                event.message.fwd_from.from_name
                or event.message.post_author
                or "Unknown"
            )
    except Exception as e:
        logger.error(
            f"Ошибка при получении оригинального канала для сообщения {event.message.id}: {e}"
        )
        author = (
            event.message.fwd_from.from_name or event.message.post_author or "Unknown"
        )
        return

    new_message = {
        "channel_id": original_channel_id,
        "text": event.message.message,
        "date": date,
        "author": author,
        "message_id": message_id,
    }
    save_single_to_db(new_message, channel)
    last_msg = get_last_msg()
    if last_msg and isinstance(last_msg, (tuple, list)):
        analyze_all_db_msg([last_msg])
    else:
        logger.warning(f"Не удалось проанализировать последнее сообщение: {last_msg}")


async def main():
    """Main entry point for the Telegram parser."""
    session_file = f"{TG_SESSION_PATH}.session"
    if not os.path.exists(session_file):
        print(
            f"Файл сессии {session_file} не найден. Запустите session_saver.py для создания новой сессии."
        )
        return

    client = await check_auth()

    async with client:
        me = await client.get_me()
        print(f"Ваш Telegram: {me.username or me.first_name}")

        channels_input = input(
            "Введите список каналов через запятую (e.g. @fr33_btc): "
        )
        input_channels = [
            channel.strip() for channel in channels_input.split(",") if channel.strip()
        ]
        if not input_channels:
            print("Не указаны каналы для обработки.")
            return

        with psycopg.connect(**DB_CONFIG) as conn:
            try:
                channels_to_parse = await setup_channels(client, conn, channels_input)
                if not channels_to_parse:
                    print("Нет каналов для парсинга.")
                    return

                limit = int(
                    input(
                        f"Количество сообщений для начального парсинга на канал ({LIMIT} по умолчанию): "
                    )
                    or LIMIT
                )

                await run_parser(client, conn, channels_to_parse, limit)
                messages = get_not_proccesed_msgs()
                if messages:
                    analyze_all_db_msg(messages)
                else:
                    print("Нет данных для анализа после парсинга.")

                await subscribe_to_channels(client, channels_to_parse)
                print(
                    f"Ожидание новых сообщений в каналах: {', '.join(c[0] for c in channels_to_parse)}..."
                )
                await client.run_until_disconnected()
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                print(f"Ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено пользователем.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        print(f"Ошибка: {e}")
