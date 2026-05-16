# Хранение состояния чатов: анонимно в сессии, для залогиненных — в Django ORM.
from __future__ import annotations

import logging
import secrets
from typing import Any

from django.db import transaction
from django.db.models import Prefetch

from assistant.models import ChatMessage, ChatThread

logger = logging.getLogger(__name__)

CHAT_SESSION_KEY_LEGACY = "assistant_chat_history"
CHAT_STATE_KEY = "assistant_chat_state_v2"
CHAT_DB_ACTIVE_KEY = "assistant_db_active_tid"

CHAT_MESSAGES_PER_THREAD_MAX = 50
CHAT_THREADS_MAX = 25


def new_thread_uid() -> str:
    return secrets.token_hex(8)


def default_chat_state() -> dict[str, Any]:
    tid = new_thread_uid()
    return {
        "version": 2,
        "order": [tid],
        "active_id": tid,
        "threads": {
            tid: {"title": "Новый чат", "messages": []},
        },
    }


def normalize_state(state: dict) -> dict:
    threads = state.get("threads") or {}
    order = [x for x in (state.get("order") or []) if x in threads]
    for tid in list(threads.keys()):
        if tid not in order:
            order.append(tid)
    if not order and threads:
        order = list(threads.keys())
    if not order:
        return default_chat_state()
    active = state.get("active_id")
    if active not in threads:
        active = order[0]
    return {"version": 2, "order": order, "active_id": active, "threads": threads}


def _save_session_state(request, state: dict) -> None:
    request.session[CHAT_STATE_KEY] = state
    request.session.modified = True


def _migrate_legacy_session_if_needed(request) -> None:
    if CHAT_STATE_KEY in request.session:
        return
    legacy = request.session.get(CHAT_SESSION_KEY_LEGACY)
    if not legacy or not isinstance(legacy, list):
        return

    from assistant.chat_threads import finalize_thread_title

    tid = new_thread_uid()
    thread = {"title": "Переписка", "messages": list(legacy)}
    finalize_thread_title(thread, thread["messages"])
    state = {
        "version": 2,
        "order": [tid],
        "active_id": tid,
        "threads": {tid: thread},
    }
    request.session.pop(CHAT_SESSION_KEY_LEGACY, None)
    _save_session_state(request, state)


def trim_thread_list(state: dict, *, threads_max: int | None = None) -> None:
    order = state["order"]
    threads = state["threads"]
    cap = CHAT_THREADS_MAX if threads_max is None else threads_max
    while len(order) > cap:
        old = order.pop()
        threads.pop(old, None)
    if state["active_id"] not in threads:
        state["active_id"] = order[0] if order else new_thread_uid()
        if state["active_id"] not in threads:
            threads[state["active_id"]] = {"title": "Новый чат", "messages": []}
            order.insert(0, state["active_id"])


@transaction.atomic
def sync_state_to_database(
    user,
    state: dict,
    *,
    messages_per_thread_max: int | None = None,
    threads_max: int | None = None,
) -> None:
    """Полная синхронизация dict-состояния в БД для пользователя."""
    msgs_cap = CHAT_MESSAGES_PER_THREAD_MAX if messages_per_thread_max is None else messages_per_thread_max
    state = normalize_state({**state, "threads": {**state.get("threads", {})}})
    trim_thread_list(state, threads_max=threads_max)
    thread_ids = list(state["threads"].keys())
    ChatThread.objects.filter(user=user).exclude(thread_id__in=thread_ids).delete()

    for rank, tid in enumerate(state["order"]):
        tdata = state["threads"][tid]
        focus = tdata.get("focus_event_id")
        hint = ((tdata.get("event_title_hint") or "")[:256]).strip()
        title = (tdata.get("title") or "Новый чат")[:200]

        ct, _created = ChatThread.objects.update_or_create(
            user=user,
            thread_id=tid,
            defaults={
                "title": title,
                "sort_rank": rank,
                "focus_event_id": int(focus) if focus is not None else None,
                "event_title_hint": hint,
            },
        )

        ct.messages_rows.all().delete()
        msgs = tdata.get("messages") or []
        if len(msgs) > msgs_cap:
            msgs = msgs[-msgs_cap:]
        bulk: list[ChatMessage] = []
        for i, m in enumerate(msgs):
            bulk.append(
                ChatMessage(
                    thread=ct,
                    role=m.get("role") or "user",
                    text=m.get("text") or "",
                    time_label=(m.get("time") or "")[:16],
                    sort_order=i,
                )
            )
        ChatMessage.objects.bulk_create(bulk)


def load_state_from_database(user) -> dict | None:
    qs = (
        ChatThread.objects.filter(user=user)
        .prefetch_related(
            Prefetch(
                "messages_rows",
                queryset=ChatMessage.objects.order_by("sort_order", "pk"),
            )
        )
        .order_by("sort_rank", "updated_at")
    )
    rows = list(qs)
    if not rows:
        return None

    threads: dict[str, dict] = {}
    order: list[str] = []

    for ct in rows:
        order.append(ct.thread_id)
        msgs = [
            {"role": mr.role, "text": mr.text, "time": mr.time_label or ""}
            for mr in ct.messages_rows.all()
        ]
        threads[ct.thread_id] = {
            "title": ct.title,
            "messages": msgs,
            "focus_event_id": ct.focus_event_id,
            "event_title_hint": ct.event_title_hint or "",
        }

    return normalize_state({"version": 2, "order": order, "active_id": order[0], "threads": threads})


def _apply_session_active_tid(request, state: dict) -> dict:
    tid = (request.session.get(CHAT_DB_ACTIVE_KEY) or "").strip()
    if tid and tid in state["threads"]:
        state["active_id"] = tid
    elif tid:
        request.session.pop(CHAT_DB_ACTIVE_KEY, None)
    return normalize_state(state)


def get_chat_state(request) -> dict:
    if request.user.is_authenticated:
        state = load_state_from_database(request.user)
        if state is None:
            state = default_chat_state()
            from assistant.local_request import get_chat_limits_for_request

            mmax, tc = get_chat_limits_for_request(request)
            sync_state_to_database(request.user, state, messages_per_thread_max=mmax, threads_max=tc)
        state = _apply_session_active_tid(request, state)
        return normalize_state(state)

    _migrate_legacy_session_if_needed(request)
    raw = request.session.get(CHAT_STATE_KEY)
    if not raw or not isinstance(raw, dict):
        state = default_chat_state()
        _save_session_state(request, state)
        return state
    state = normalize_state(raw)
    _save_session_state(request, state)
    return state


def save_chat_state(request, state: dict) -> None:
    from assistant.local_request import get_chat_limits_for_request

    state = normalize_state(state)
    msg_max, thr_max = get_chat_limits_for_request(request)
    if request.user.is_authenticated:
        sync_state_to_database(
            request.user,
            state,
            messages_per_thread_max=msg_max,
            threads_max=thr_max,
        )
        request.session[CHAT_DB_ACTIVE_KEY] = state["active_id"]
        request.session.modified = True
        return
    trim_thread_list(state, threads_max=thr_max)
    _save_session_state(request, state)


def merge_guest_session_into_user(request, user) -> None:
    """
    Перед login(): переносит гостевое состояние из сессии в аккаунт.
    Если в сессии только пустой новый чат — не трогаем БД.
    """
    from assistant.local_request import get_chat_limits_for_request

    mmax, tc = get_chat_limits_for_request(request)

    _migrate_legacy_session_if_needed(request)
    raw_sess = request.session.pop(CHAT_STATE_KEY, None)

    have_guest = False
    guest: dict | None = None
    if raw_sess and isinstance(raw_sess, dict):
        guest = normalize_state(raw_sess)
        threads = guest.get("threads") or {}
        if len(threads) > 1 or any((t.get("messages") or []) for t in threads.values()):
            have_guest = True
        elif threads:
            lone = next(iter(threads.values()))
            if (lone.get("title") or "").strip() not in ("", "Новый чат"):
                have_guest = True
            if lone.get("focus_event_id") is not None:
                have_guest = True

    db_state = load_state_from_database(user)

    if db_state is None and not have_guest:
        return

    if db_state is None:
        final = guest
    elif not have_guest:
        return
    else:
        sess = guest
        new_threads = {**db_state["threads"]}
        new_order = list(db_state["order"])

        def _unique_id(preferred: str) -> str:
            nid = preferred
            while nid in new_threads:
                nid = new_thread_uid()
            return nid

        prefix: list[str] = []
        for oid in sess["order"]:
            st = sess["threads"].get(oid)
            if not st:
                continue
            nid = _unique_id(oid)
            new_threads[nid] = {
                "title": st.get("title") or "Новый чат",
                "messages": list(st.get("messages") or []),
                "focus_event_id": st.get("focus_event_id"),
                "event_title_hint": st.get("event_title_hint") or "",
            }
            prefix.append(nid)

        seen = set(prefix)
        tail = [x for x in new_order if x not in seen]
        merged_order = prefix + tail
        while len(merged_order) > tc:
            dropped = merged_order.pop()
            new_threads.pop(dropped, None)

        active = prefix[0] if prefix else db_state["active_id"]
        final = normalize_state({
            "version": 2,
            "order": merged_order,
            "active_id": active,
            "threads": new_threads,
        })

    sync_state_to_database(user, final, messages_per_thread_max=mmax, threads_max=tc)
    request.session[CHAT_DB_ACTIVE_KEY] = final["active_id"]
    request.session.modified = True
