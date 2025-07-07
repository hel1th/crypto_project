from .logging_config import setup_logging
from app.config import TG_SESSION_PATH, TG_API_ID, TG_API_HASH
from telethon import TelegramClient
import logging

setup_logging()
logger = logging.getLogger(__name__)


async def check_auth() -> TelegramClient:
    print((TG_SESSION_PATH, TG_API_ID, TG_API_HASH))
    client = TelegramClient(TG_SESSION_PATH, TG_API_ID, TG_API_HASH)

    await client.connect()
    if not await client.is_user_authorized():
        print("📲 Need authorization. Enter the number and the code.")
        await client.start()
        me = await client.get_me()
        print(f"✅ Successfully authorized as {me.username or me.first_name}")
    else:
        print("🔐 Already authorized.")
    await client.disconnect()
    return client
