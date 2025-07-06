from .logging_config import setup_logging
from app.config import TG_SESSION_PATH, TG_API_ID, TG_API_HASH
from telethon import TelegramClient
import asyncio
import logging
import os

setup_logging()
logger = logging.getLogger(__name__)

custom_suffix = input(
    "Введите суффикс сессии (оставьте пустым для использования из .env, например _vlad): "
) or os.getenv("TG_SESSION_SUFFIX", "")
if custom_suffix:
    session_name = os.path.basename(TG_SESSION_PATH).replace(
        os.getenv("TG_SESSION_SUFFIX", ""), custom_suffix
    )
    TG_SESSION_PATH = os.path.join(os.path.dirname(TG_SESSION_PATH), session_name)

client = TelegramClient(TG_SESSION_PATH, TG_API_ID, TG_API_HASH)


async def main():
    print(f"Авторизация в Telegram с сессией: {TG_SESSION_PATH}.session...")
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Успешно авторизован как {me.username or me.first_name}")
        print(f"Сессия сохранена: {TG_SESSION_PATH}.session")
        await client.disconnect()
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено пользователем.")
    except Exception as e:
        print(f"Ошибка: {e}")
