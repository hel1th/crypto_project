import os
from dotenv import load_dotenv
import datetime

load_dotenv()


DB_CONFIG: dict[str, str | None] = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

API_KEY_LLM = os.getenv("API_KEY_LLM")
