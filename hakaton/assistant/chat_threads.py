# Заголовки и превью чат-потоков (без Django request / без ORM).
import logging

logger = logging.getLogger(__name__)


def derive_thread_title(thread: dict) -> None:
    msgs = thread.get("messages") or []
    for m in msgs:
        if m.get("role") == "user" and (m.get("text") or "").strip():
            t = (m["text"] or "").strip().replace("\n", " ")
            thread["title"] = (t[:48] + "…") if len(t) > 48 else t
            return
    thread["title"] = "Новый чат"


def messages_excerpt_for_title(msgs: list, max_items: int = 12, chunk: int = 500) -> str:
    lines = []
    tail = msgs[-max_items:] if len(msgs) > max_items else msgs
    for m in tail:
        role = m.get("role")
        label = "Пользователь" if role == "user" else "Помощник"
        text = ((m.get("text") or "").strip()).replace("\n", " ")
        if not text:
            continue
        if len(text) > chunk:
            text = text[:chunk] + "…"
        lines.append(f"{label}: {text}")
    return "\n".join(lines)


def finalize_thread_title(thread: dict, msgs: list) -> None:
    hints = thread.get("event_title_hint")

    if not msgs:
        if hints:
            h = hints.strip()
            thread["title"] = (h[:48] + "…") if len(h) > 48 else h
        else:
            thread["title"] = "Новый чат"
        return

    excerpt = messages_excerpt_for_title(msgs)
    if not excerpt.strip():
        if hints:
            h = hints.strip()
            thread["title"] = (h[:48] + "…") if len(h) > 48 else h
        else:
            thread["title"] = "Новый чат"
        return

    try:
        from gigachat_advisor import suggest_chat_title

        t = suggest_chat_title(excerpt, hints)
        if t and len(t.strip()) > 1:
            thread["title"] = t.strip()[:56]
            return
    except Exception:
        logger.debug("suggest_chat_title failed", exc_info=True)

    if hints:
        h = hints.strip()
        thread["title"] = (h[:48] + "…") if len(h) > 48 else h
    else:
        derive_thread_title(thread)


def thread_preview(thread: dict) -> str:
    msgs = thread.get("messages") or []
    for m in reversed(msgs):
        txt = (m.get("text") or "").strip().replace("\n", " ")
        if not txt:
            continue
        if m.get("role") == "assistant":
            return (txt[:90] + "…") if len(txt) > 90 else txt
    for m in reversed(msgs):
        if m.get("role") == "user":
            txt = (m["text"] or "").strip().replace("\n", " ")
            if txt:
                return (txt[:90] + "…") if len(txt) > 90 else txt
    return ""


def last_time_label(thread: dict) -> str:
    msgs = thread.get("messages") or []
    if not msgs:
        return ""
    return msgs[-1].get("time") or ""
