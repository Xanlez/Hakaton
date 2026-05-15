# Рекомендации мероприятий через GigaChat
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from config import (
    DB_PATH,
    GIGACHAT_CA_BUNDLE_FILE,
    GIGACHAT_CREDENTIALS,
    GIGACHAT_MODEL,
    GIGACHAT_SCOPE,
    GIGACHAT_VERIFY_SSL_CERTS,
)
from database import catalog_text, init_db, load_catalog

SYSTEM_PROMPT = (
    "Ты помощник по афише «Сириус». Рекомендуй только события из списка. "
    "Указывай id, дату, время, название. До 5 пунктов. Не выдумывай события."
)


def recommend_events(query: str, db_path: str = DB_PATH) -> str:
    conn = init_db(db_path)
    rows = load_catalog(conn)
    conn.close()

    if not rows:
        raise RuntimeError("База пуста. Запустите: python main.py --once")
    if not GIGACHAT_CREDENTIALS:
        raise RuntimeError("Задайте GIGACHAT_CREDENTIALS в .env")

    text = f"Список ({len(rows)}):\n{catalog_text(rows)}\n\nЗапрос: {query}"
    chat = Chat(messages=[
        Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
        Messages(role=MessagesRole.USER, content=text),
    ])

    opts = dict(
        credentials=GIGACHAT_CREDENTIALS,
        scope=GIGACHAT_SCOPE,
        model=GIGACHAT_MODEL,
        verify_ssl_certs=GIGACHAT_VERIFY_SSL_CERTS,
    )
    if GIGACHAT_CA_BUNDLE_FILE:
        opts["ca_bundle_file"] = GIGACHAT_CA_BUNDLE_FILE

    with GigaChat(**opts) as client:
        return client.chat(chat).choices[0].message.content
