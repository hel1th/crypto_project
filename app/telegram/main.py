import asyncio
import psycopg2
import os
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("telegram.log"),  # Log to a file
        logging.StreamHandler(),  # Also log to console
    ],
)
logger = logging.getLogger(__name__)

# Ensure telethon logs are captured
logging.getLogger("telethon").setLevel(logging.INFO)


async def fetch_messages(client, channel_username: str, limit: int = LIMIT) -> list:
    try:
        entity = await client.get_entity(channel_username)
        messages = []
        async for msg in client.iter_messages(entity, limit=limit):
            if not msg.message:
                continue
            author = None
            if msg.sender:
                if isinstance(msg.sender, User):
                    author = msg.sender.username or msg.sender.first_name or None
                elif isinstance(msg.sender, Channel):
                    author = msg.sender.title or None
            messages.append(
                {
                    "id": msg.id,
                    "text": msg.message,
                    "channel": channel_username,
                    "date": msg.date.astimezone(tz=TZ).strftime("%Y-%m-%d %H:%M:%S"),
                    "author": author,
                }
            )
        return messages
    except ChannelPrivateError:
        print(
            f"❌ Канал {channel_username} является приватным, и вы не являетесь участником."
        )
        return []
    except ChannelInvalidError:
        print(f"❌ Канал {channel_username} не найден.")
        return []
    except Exception as e:
        print(f"❌ Ошибка при получении сообщений из канала {channel_username}: {e}")
        return []


def save_batch_to_db(messages, channel):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = """
            INSERT INTO telegram_messages (message_id, text, channel, date, author)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING
        """
        data = [
            (msg["id"], msg["text"], msg["channel"], msg["date"], msg["author"])
            for msg in messages
        ]
        cur.executemany(query, data)
        conn.commit()
        if cur.rowcount < len(messages):
            print(
                f"⚠️ Некоторые сообщения из канала {channel} не сохранены (возможно, дубликаты message_id). Сохранено: {cur.rowcount}/{len(messages)}"
            )
        else:
            print(
                f"✅ Сохранено {cur.rowcount} сообщений из канала {channel} в PostgreSQL"
            )
    except Exception as e:
        print(f"❌ Ошибка при сохранении в PostgreSQL для канала {channel}: {e}")
    finally:
        cur.close()
        conn.close()


def save_single_to_db(message, channel):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = """
            INSERT INTO telegram_messages (message_id, text, channel, date, author)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING
        """
        data = (
            message["id"],
            message["text"],
            channel,
            message["date"],
            message["author"],
        )
        cur.execute(query, data)
        conn.commit()
        if cur.rowcount > 0:
            print(
                f"📩 Новое сообщение из канала {channel} сохранено в PostgreSQL: {message['id']}"
            )
    except Exception as e:
        print(f"❌ Ошибка при сохранении нового сообщения из канала {channel}: {e}")
    finally:
        cur.close()
        conn.close()


async def main():
    # Проверка существования файла сессии
    session_file = f"{TG_SESSION_PATH}.session"
    if not os.path.exists(session_file):
        print(
            f"⚠️ Файл сессии {session_file} не найден. Запустите session_saver.py для создания новой сессии."
        )
        return

    client = await check_auth()

    async with client:  # Keep the client connected for the entire operation
        me = await client.get_me()
        print(f"👤 Ваш Telegram: {me.username or me.first_name}")

        # Список каналов (можно также загружать из файла или переменной окружения)
        channels_input = input(
            "Введите список каналов через запятую (e.g. @binance,joe_speen_youtube): "
        )
        channels = [
            channel.strip() for channel in channels_input.split(",") if channel.strip()
        ]
        if not channels:
            print("❌ Не указаны каналы для обработки.")
            return

        limit = input(
            f"Количество сообщений для начального парсинга на канал ({LIMIT} по умолчанию): "
        )
        limit = int(limit) if limit else LIMIT

        # Парсинг прошлых сообщений для всех каналов
        for channel in channels:
            print(f"⏳ Парсим {limit} прошлых сообщений из канала {channel}...")
            messages = await fetch_messages(client, channel, limit)
            if messages:
                save_batch_to_db(messages, channel)
            print(
                f"✅ Спарсено и сохранено {len(messages)} прошлых сообщений из канала {channel}"
            )

        # Подписка на новые сообщения для всех каналов
        try:
            entities = []
            for channel in channels:
                try:
                    entity = await client.get_entity(channel)
                    entities.append((channel, entity))
                except ChannelPrivateError:
                    print(
                        f"❌ Не могу подписаться на канал {channel}: он приватный, и вы не являетесь участником."
                    )
                except ChannelInvalidError:
                    print(f"❌ Канал {channel} не найден.")
                except Exception as e:
                    print(f"❌ Ошибка при получении сущности канала {channel}: {e}")

            for channel, entity in entities:

                @client.on(events.NewMessage(chats=entity))
                async def handle_new_message(
                    event, ch=channel
                ):  # Передаем channel через замыкание
                    if not event.message.message:
                        return
                    author = None
                    if event.message.sender:
                        if isinstance(event.message.sender, User):
                            author = (
                                event.message.sender.username
                                or event.message.sender.first_name
                                or None
                            )
                        elif isinstance(event.message.sender, Channel):
                            author = event.message.sender.title or None
                    new_message = {
                        "id": event.message.id,
                        "text": event.message.message,
                        "date": event.message.date.astimezone(tz=TZ).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "author": author,
                    }
                    save_single_to_db(new_message, ch)

            print(f"🔔 Ожидание новых сообщений в каналах: {', '.join(channels)}...")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"❌ Ошибка при подписке на каналы: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
