from __future__ import annotations
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
from database import fetch_events_catalog, format_events_catalog, init_db

SYSTEM_PROMPT = """Ты помощник по афише федеральной территории «Сириус».

Правила:
- Рекомендуй ТОЛЬКО мероприятия из переданного списка.
- В каждой рекомендации укажи id, дату, время и название.
- Кратко объясни, почему мероприятие подходит запросу.
- Если подходящих нет — так и скажи, предложи уточнить запрос.
- Не выдумывай мероприятия и не меняй даты/время из списка.
- Отвечай по-русски, до 5 пунктов."""


def _create_client() -> GigaChat:
    if not GIGACHAT_CREDENTIALS:
        raise RuntimeError(
            "Не задан GIGACHAT_CREDENTIALS. Скопируйте .env.example в .env "
            "и вставьте ключ из https://developers.sber.ru/studio/"
        )

    kwargs: dict = {
        "credentials": GIGACHAT_CREDENTIALS,
        "scope": GIGACHAT_SCOPE,
        "model": GIGACHAT_MODEL,
        "verify_ssl_certs": GIGACHAT_VERIFY_SSL_CERTS,
    }
    if GIGACHAT_CA_BUNDLE_FILE:
        kwargs["ca_bundle_file"] = GIGACHAT_CA_BUNDLE_FILE

    return GigaChat(**kwargs)


def recommend_events(user_query: str, db_path: str = DB_PATH) -> str:
    conn = init_db(db_path)
    rows = fetch_events_catalog(conn)
    conn.close()

    if not rows:
        raise RuntimeError(
            "База пустая. Сначала загрузите афишу: python main.py --once"
        )

    catalog = format_events_catalog(rows)
    user_message = (
        f"Список мероприятий ({len(rows)} шт.):\n{catalog}\n\n"
        f"Запрос пользователя: {user_query}"
    )

    chat = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
            Messages(role=MessagesRole.USER, content=user_message),
        ]
    )

    with _create_client() as client:
        response = client.chat(chat)

    return response.choices[0].message.content
