# Рекомендации и диалоги по афише через GigaChat
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
from database import catalog_text, event_time, fetch_event_by_id, init_db, load_catalog

SYSTEM_PROMPT = (
    "Ты помощник по афише «Сириус». Рекомендуй только события из списка. "
    "Для каждого пункта укажи дату, время, название и место. До 5 пунктов. "
    "Не выдумывай события. Не используй внутренние номера и служебные id — говори по-человечески. "
    "Можно оформить ответ с заголовком ## и подписями **Когда:** / **Где:** для удобства чтения."
)

SYSTEM_EVENT_CHAT = (
    "Ты помощник по афише «Сириус». Пользователь обсуждает одно мероприятие — "
    "данные только из блока «КАРТОЧКА» ниже. Отвечай по-русски, вежливо. "
    "Не придумывай цены, ссылки на регистрацию, состав спикеров и прочие детали, "
    "если их нет в карточке. Если информации мало — честно скажи. "
    "Не упоминай внутренние id и прочие служебные коды событий. "
    "Оформляй ответ для чата: первая строка — заголовок с ## (название события без служебных номеров), "
    "далее короткие абзацы; для даты/времени и места используй строки, начинающиеся с **Когда:** и **Где:** "
    "(жирные подписи), затем текст в той же строке или следующем абзаце; описание — отдельным абзацем."
)

SYSTEM_EVENT_INTRO = (
    "Ты дружелюбный гид афиши «Сириус». Рассказываешь только на основе переданной карточки."
)

SYSTEM_TITLE = (
    "Придумай короткое название чата на русском (2–6 слов) для боковой панели. "
    "Только само название: без кавычек, без двоеточия в начале, без «Чат о»."
)


def _giga_options() -> dict:
    opts = dict(
        credentials=GIGACHAT_CREDENTIALS,
        scope=GIGACHAT_SCOPE,
        model=GIGACHAT_MODEL,
        verify_ssl_certs=GIGACHAT_VERIFY_SSL_CERTS,
    )
    if GIGACHAT_CA_BUNDLE_FILE:
        opts["ca_bundle_file"] = GIGACHAT_CA_BUNDLE_FILE
    return opts


def _require_credentials() -> None:
    if not GIGACHAT_CREDENTIALS:
        raise RuntimeError("Задайте GIGACHAT_CREDENTIALS в .env")


def _one_shot(system: str, user: str) -> str:
    _require_credentials()
    chat = Chat(messages=[
        Messages(role=MessagesRole.SYSTEM, content=system),
        Messages(role=MessagesRole.USER, content=user),
    ])
    with GigaChat(**_giga_options()) as client:
        return client.chat(chat).choices[0].message.content


def format_event_card(row) -> str:
    slot = event_time(row)
    when = "весь день" if row["is_all_day"] or slot == "all-day" else slot
    desc = ""
    try:
        if "event_description" in row.keys():
            desc = (row["event_description"] or "").strip()
    except (AttributeError, KeyError):
        desc = ""
    lines = [
        f"«{row['event_name']}»",
        f"Тип: {row['afisha_type_name'] or 'не указан'}",
        f"Дата: {row['event_start_date'] or '—'}",
        f"Время: {when}",
        f"Место: {row['event_place'] or '—'}",
    ]
    if desc:
        lines.append("Описание (из афиши):\n" + desc)
    return "\n".join(lines)


def fallback_event_intro(row) -> str:
    card = format_event_card(row)
    return (
        "Кратко по карточке из афиши:\n\n"
        f"{card}\n\n"
        "Задайте вопрос — подскажу по этим данным или похожим событиям из общей афиши."
    )


def introduce_event(db_path: str, event_id: int) -> str:
    row = fetch_event_by_id(db_path, event_id)
    if row is None:
        raise RuntimeError("Событие не найдено")
    _require_credentials()
    card = format_event_card(row)
    user = (
        f"Карточка мероприятия:\n{card}\n\n"
        "Сформируй живое приветствие по-русски (5–8 предложений): о чём событие, "
        "когда и где, кому может зайти. Опирайся на блок «Описание», если он есть; "
        "если описания нет — честно скажи, что подробности только в названии и типе. "
        "Не упоминай id, технические коды и «служебные» поля. "
        "Оформление: первая строка — заголовок с ## (только название из карточки), "
        "затем абзацы **Когда:** … и **Где:** … (подписи жирным), потом абзац с сутью события. "
        "В конце пригласи задать вопрос. Не выдумывай цены, ссылки и регистрацию."
    )
    return _one_shot(SYSTEM_EVENT_INTRO, user).strip()


def chat_about_event(
    user_message: str,
    db_path: str,
    event_id: int,
    history: list[dict],
) -> str:
    row = fetch_event_by_id(db_path, event_id)
    if row is None:
        raise RuntimeError("Событие не найдено")
    _require_credentials()
    card = format_event_card(row)
    system = f"{SYSTEM_EVENT_CHAT}\n\nКАРТОЧКА:\n{card}"

    built: list[Messages] = [Messages(role=MessagesRole.SYSTEM, content=system)]
    for m in history:
        role = m.get("role")
        text = (m.get("text") or "").strip()
        if not text:
            continue
        if role == "user":
            built.append(Messages(role=MessagesRole.USER, content=text))
        elif role == "assistant":
            built.append(Messages(role=MessagesRole.ASSISTANT, content=text))

    built.append(Messages(role=MessagesRole.USER, content=user_message))

    with GigaChat(**_giga_options()) as client:
        return client.chat(Chat(messages=built)).choices[0].message.content


def suggest_chat_title(conversation_excerpt: str, event_name_hint: str | None) -> str:
    _require_credentials()
    parts = []
    if event_name_hint:
        parts.append(f"Связь с мероприятием из афиши: «{event_name_hint.strip()}».")
    parts.append("Фрагмент диалога:")
    parts.append(conversation_excerpt.strip()[:3800])
    parts.append("\nНазвание чата (2–6 слов):")
    user = "\n".join(parts)
    raw = _one_shot(SYSTEM_TITLE, user).strip()
    line = raw.replace('"', "").replace("«", "").replace("»", "").split("\n")[0].strip()
    return (line[:56] + "…") if len(line) > 56 else line


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

    opts = _giga_options()

    with GigaChat(**opts) as client:
        return client.chat(chat).choices[0].message.content
