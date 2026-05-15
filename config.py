# Настройки приложения
import os
from pathlib import Path

API_URL = "https://pro.sirius-ft.ru/api/afisha/event/list"
DB_PATH = "afisha.db"
SYNC_INTERVAL_SEC = 3600


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_dotenv(env_file)


_load_dotenv()

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")
GIGACHAT_CA_BUNDLE_FILE = os.getenv("GIGACHAT_CA_BUNDLE_FILE", "")
GIGACHAT_VERIFY_SSL_CERTS = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "true").lower() in (
    "1", "true", "yes",
)
