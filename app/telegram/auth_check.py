import logging
from telethon import TelegramClient
from tg_config import TG_SESSION_PATH, TG_API_ID, TG_API_HASH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("telegram.log"), logging.StreamHandler()],
)
logging.getLogger("telethon").setLevel(logging.INFO)


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
