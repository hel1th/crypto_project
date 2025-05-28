import os
import logging
import asyncio
from telethon import TelegramClient
from config import TG_SESSION_PATH, TG_API_ID, TG_API_HASH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("telegram.log"), logging.StreamHandler()],
)
logging.getLogger("telethon").setLevel(logging.INFO)

# Разрешаем переопределить суффикс при запуске
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
    print(f"🔐 Авторизация в Telegram с сессией: {TG_SESSION_PATH}.session...")
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Успешно авторизован как {me.username or me.first_name}")
        print(f"📁 Сессия сохранена: {TG_SESSION_PATH}.session")
        await client.disconnect()
    except Exception as e:
        print(f"❌ Ошибка при авторизации: {e}")
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
