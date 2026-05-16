# Рекомендации и диалоги по афише через GigaChat
from __future__ import annotations

from typing import Any

from gigachat import GigaChat
from gigachat.exceptions import AuthenticationError, ForbiddenError, ResponseError
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

# Режим loopback-доступа: общий промпт без жёсткой привязки «только к афише»
SYSTEM_LOCAL_SIMPLE_LLM = (
    "Ты нейросетевая языковая модель. Отвечай по-русски по сути вопроса, как универсальный чат‑бот без "
    "искусственного ограничения «обсуждать только переданную афишу». Если к запросу прилагаются данные из афиши "
    "(список событий или карточка) — используй их как источник, когда вопрос о мероприятиях; иначе отвечай на "
    "общую тему. Не придумывай конкретные факты о событиях, которых нет во входных данных."
)


def _local_llm_simple(giga_kw: dict[str, Any] | None) -> bool:
    return bool(giga_kw and giga_kw.get("_local_llm_simple"))


def _giga_options(giga_kw: dict[str, Any] | None = None) -> dict:
    scope = GIGACHAT_SCOPE
    model = GIGACHAT_MODEL
    if giga_kw:
        s = str(giga_kw.get("scope") or "").strip()
        m = str(giga_kw.get("model") or "").strip()
        if s:
            scope = s
        if m:
            model = m
    opts = dict(
        credentials=GIGACHAT_CREDENTIALS,
        scope=scope,
        model=model,
        verify_ssl_certs=GIGACHAT_VERIFY_SSL_CERTS,
    )
    if GIGACHAT_CA_BUNDLE_FILE:
        opts["ca_bundle_file"] = GIGACHAT_CA_BUNDLE_FILE
    return opts


def _require_credentials() -> None:
    if not GIGACHAT_CREDENTIALS:
        raise RuntimeError("Задайте GIGACHAT_CREDENTIALS в .env")


def _chat_execute(chat_obj: Chat, *, giga_kw: dict[str, Any] | None = None) -> tuple[str, int]:
    """Вызывает GigaChat по готовому Chat; текст и usage.total_tokens (0 если не пришло)."""
    _require_credentials()
    with GigaChat(**_giga_options(giga_kw)) as client:
        completion = client.chat(chat_obj)
    choices = getattr(completion, "choices", None) or ()
    if not choices:
        raise RuntimeError("Пустой ответ модели")
    msg = getattr(choices[0], "message", None)
    text = getattr(msg, "content", None) if msg is not None else None
    if text is None:
        text = ""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    usage = getattr(completion, "usage", None)
    total = int(getattr(usage, "total_tokens", None) or 0) if usage is not None else 0
    return text, total


def _one_shot(system: str, user: str, *, giga_kw: dict[str, Any] | None = None) -> tuple[str, int]:
    chat = Chat(messages=[
        Messages(role=MessagesRole.SYSTEM, content=system),
        Messages(role=MessagesRole.USER, content=user),
    ])
    return _chat_execute(chat, giga_kw=giga_kw)


def gigachat_api_balance_entries(
    *,
    giga_kw: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Запрос остатка через GigaChat API (метод клиента get_balance → /balance).
    По документации SDK ответ есть у предоплатных клиентов; иначе обычно HTTP 403.
    Возвращает (список {usage, value}, None) или ([], текст_ошибки).
    """
    if not GIGACHAT_CREDENTIALS:
        return [], "Задайте GIGACHAT_CREDENTIALS в .env — остаток с API не запросить."

    try:
        with GigaChat(**_giga_options(giga_kw)) as client:
            bal = client.get_balance()
        rows: list[dict[str, Any]] = []
        for item in bal.balance or []:
            rows.append({
                "usage": ((item.usage or "").strip()) or "—",
                "value": float(item.value),
            })
        return rows, None
    except ForbiddenError:
        return [], (
            "Остаток по API недоступен (403 Forbidden): метод /balance не включён для этого типа доступа к GigaChat."
        )
    except AuthenticationError:
        return [], "Не удалось авторизоваться в GigaChat (401). Проверьте GIGACHAT_CREDENTIALS и scope."
    except ResponseError as exc:
        return [], f"GigaChat вернул HTTP {exc.status_code} при запросе остатка."
    except Exception as exc:
        return [], f"Не удалось запросить остаток токенов: {type(exc).__name__}: {exc}"


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


def introduce_event(
    db_path: str,
    event_id: int,
    *,
    giga_kw: dict[str, Any] | None = None,
) -> tuple[str, int]:
    row = fetch_event_by_id(db_path, event_id)
    if row is None:
        raise RuntimeError("Событие не найдено")
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
    system = SYSTEM_LOCAL_SIMPLE_LLM if _local_llm_simple(giga_kw) else SYSTEM_EVENT_INTRO
    return _one_shot(system, user, giga_kw=giga_kw)


def chat_about_event(
    user_message: str,
    db_path: str,
    event_id: int,
    history: list[dict],
    *,
    giga_kw: dict[str, Any] | None = None,
) -> tuple[str, int]:
    row = fetch_event_by_id(db_path, event_id)
    if row is None:
        raise RuntimeError("Событие не найдено")
    card = format_event_card(row)
    if _local_llm_simple(giga_kw):
        system = (
            SYSTEM_LOCAL_SIMPLE_LLM
            + "\n\nНиже карточка мероприятия для справки (полагайся на неё только если вопрос об этом событии):\n"
            + card
        )
    else:
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

    return _chat_execute(Chat(messages=built), giga_kw=giga_kw)


def suggest_chat_title(conversation_excerpt: str, event_name_hint: str | None) -> str:
    parts = []
    if event_name_hint:
        parts.append(f"Связь с мероприятием из афиши: «{event_name_hint.strip()}».")
    parts.append("Фрагмент диалога:")
    parts.append(conversation_excerpt.strip()[:3800])
    parts.append("\nНазвание чата (2–6 слов):")
    user = "\n".join(parts)
    raw, _tokens = _one_shot(SYSTEM_TITLE, user)
    raw = raw.strip()
    line = raw.replace('"', "").replace("«", "").replace("»", "").split("\n")[0].strip()
    return (line[:56] + "…") if len(line) > 56 else line


def recommend_events_with_usage(
    query: str,
    db_path: str = DB_PATH,
    *,
    giga_kw: dict[str, Any] | None = None,
) -> tuple[str, int]:
    conn = init_db(db_path)
    rows = load_catalog(conn)
    conn.close()

    if not rows:
        raise RuntimeError("База пуста. Запустите: python main.py --once")
    if not GIGACHAT_CREDENTIALS:
        raise RuntimeError("Задайте GIGACHAT_CREDENTIALS в .env")

    text = f"Список ({len(rows)}):\n{catalog_text(rows)}\n\nЗапрос: {query}"
    system = SYSTEM_LOCAL_SIMPLE_LLM if _local_llm_simple(giga_kw) else SYSTEM_PROMPT
    chat = Chat(messages=[
        Messages(role=MessagesRole.SYSTEM, content=system),
        Messages(role=MessagesRole.USER, content=text),
    ])

    return _chat_execute(chat, giga_kw=giga_kw)


def recommend_events(query: str, db_path: str = DB_PATH) -> str:
    text, _tokens = recommend_events_with_usage(query, db_path)
    return text
