import os
from dotenv import load_dotenv
import datetime

load_dotenv()

# Telegram settings
offset = datetime.timedelta(hours=3)
TZ = datetime.timezone(offset)
LIMIT = 50

TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_BASE_SESSION_NAME = os.getenv(
    "TG_SESSION_NAME", "my_app_session"
)  # Базовое имя сессии

TG_SESSION_SUFFIX = os.getenv("TG_SESSION_SUFFIX", "")
TG_SESSION_NAME = f"{TG_BASE_SESSION_NAME}{TG_SESSION_SUFFIX}"

# Путь к папке сессий
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)
TG_SESSION_PATH = os.path.join(SESSIONS_DIR, TG_SESSION_NAME)

DB_CONFIG: dict[str, str | None] = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

API_KEY_LLM = os.getenv("API_KEY_LLM")
