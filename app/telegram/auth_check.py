import logging
from telethon import TelegramClient
from .config import TG_SESSION_PATH, TG_API_ID, TG_API_HASH
from .logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def check_auth():
    client = TelegramClient(TG_SESSION_PATH, TG_API_ID, TG_API_HASH)

    await client.connect()
    if not await client.is_user_authorized():
        print("📲 Требуется авторизация. Введите номер и код.")
        await client.start()
        me = await client.get_me()
        print(f"✅ Успешно авторизован как {me.username or me.first_name}")
    else:
        print("🔐 Уже авторизован.")
    await client.disconnect()
    return client
