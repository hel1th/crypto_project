from typing import Any, Dict
from app.types import Db_config

import os
from dotenv import load_dotenv
from datetime import timedelta, timezone

load_dotenv(override=True)


DB_CONFIG: dict[str, Any] = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
}
print(DB_CONFIG["dbname"])
PASSWORD_SALT = os.getenv("PASSWORD_SALT")
API_KEY_LLM = os.getenv("API_KEY_LLM")

# Telegram settings
TZ = timezone(timedelta(hours=0))
print(TZ)
LIMIT = 50

TG_API_ID: str = os.getenv("TG_API_ID")  # type: ignore
TG_API_HASH: str = os.getenv("TG_API_HASH")  # type: ignore
TG_BASE_SESSION_NAME = os.getenv(
    "TG_SESSION_NAME", "my_app_session"
)  # Базовое имя сессии

TG_SESSION_SUFFIX = os.getenv("TG_SESSION_SUFFIX", "")
TG_SESSION_NAME = f"{TG_BASE_SESSION_NAME}{TG_SESSION_SUFFIX}"

# Путь к папке сессий
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "telegram/sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)
TG_SESSION_PATH = os.path.join(SESSIONS_DIR, TG_SESSION_NAME)

INTERVALS_TO_DELTA: Dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "30m": timedelta(minutes=30),
    "5m": timedelta(minutes=5),
    "1m": timedelta(minutes=1),
}
