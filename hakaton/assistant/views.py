import json
import logging
from pathlib import Path

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone as dj_tz
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from assistant.local_request import (
    get_chat_limits_for_request,
    request_is_loopback,
    trim_chat_threads_for_request,
)
from assistant.chat_storage import (
    get_chat_state,
    new_thread_uid,
    save_chat_state,
)
from assistant.chat_threads import finalize_thread_title, last_time_label, thread_preview
from assistant.formatting import assistant_reply_html, clean_assistant_visible
from assistant.gigachat_errors import (
    classify_chat_backend_failure,
    ndjson_chat_error_line_bytes,
)
from assistant.gigachat_plan_prefs import (
    LOCAL_GIGACHAT_SESSION_SLUG_KEY,
    allowed_plan_slugs,
    gigachat_client_kw_for_request,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _backend_db_path() -> str:
    from config import DB_PATH

    p = Path(DB_PATH)
    return str(p if p.is_absolute() else _REPO_ROOT / DB_PATH)


def _ensure_afisha_db(db_path: str, *, force: bool = False) -> None:
    from sync_afisha import ensure_db

    ensure_db(db_path, force)


def _events_for_template(db_path: str, *, search: str | None = None) -> list[dict]:
    from database import event_time, init_db

    conn = init_db(db_path)
    query = """SELECT event_id, event_name, event_start_date, event_start_time, event_end_time,
                      is_all_day, afisha_type_name, event_place, image_url, event_description
               FROM events"""
    params: tuple[str, ...] = ()
    term = (search or "").strip().lower()
    if term:
        esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        needle = f"%{esc}%"
        query += """
               WHERE (
                   lower(IFNULL(event_name, '')) LIKE ? ESCAPE '\\'
                   OR lower(IFNULL(event_place, '')) LIKE ? ESCAPE '\\'
                   OR lower(IFNULL(afisha_type_name, '')) LIKE ? ESCAPE '\\'
                   OR lower(IFNULL(event_description, '')) LIKE ? ESCAPE '\\'
               )
        """
        params = (needle, needle, needle, needle)
    query += " ORDER BY event_start_date, event_start_time, event_id"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    out: list[dict] = []
    for r in rows:
        slot = event_time(r)
        desc_full = ""
        preview = ""
        if "event_description" in r.keys():
            desc_full = (r["event_description"] or "").strip()
        if desc_full:
            one_line = desc_full.replace("\n", " ").replace("\r", " ")
            preview = one_line[:200] + ("…" if len(one_line) > 200 else "")
        out.append({
            "event_id": r["event_id"],
            "event_name": r["event_name"],
            "event_start_date": r["event_start_date"] or "—",
            "time_slot": slot,
            "afisha_type_name": (r["afisha_type_name"] or "").strip(),
            "event_place": (r["event_place"] or "").strip(),
            "image_url": (r["image_url"] or "").strip(),
            "event_description_preview": preview,
            "has_description": bool(desc_full),
        })
    return out


def _events_table_nonempty(db_path: str) -> bool:
    from database import init_db

    conn = init_db(db_path)
    row = conn.execute("SELECT 1 FROM events LIMIT 1").fetchone()
    conn.close()
    return row is not None


def _event_detail_dict(db_path: str, event_id: int) -> dict | None:
    from database import event_time, init_db

    conn = init_db(db_path)
    row = conn.execute(
        "SELECT * FROM events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    slot = event_time(row)
    if row["is_all_day"]:
        time_display = "Весь день"
    elif slot == "all-day":
        time_display = "Весь день"
    else:
        time_display = slot
    desc = ""
    if "event_description" in row.keys():
        desc = (row["event_description"] or "").strip()
    return {
        "event_id": row["event_id"],
        "event_name": row["event_name"],
        "afisha_type_name": (row["afisha_type_name"] or "").strip(),
        "event_start_date": row["event_start_date"] or "—",
        "event_start_time": row["event_start_time"] or "",
        "event_end_time": row["event_end_time"] or "",
        "is_all_day": bool(row["is_all_day"]),
        "time_display": time_display,
        "event_place": (row["event_place"] or "").strip(),
        "image_url": (row["image_url"] or "").strip(),
        "event_description": desc,
        "has_description": bool(desc),
    }




def _chat_time_labels() -> tuple[str, str]:
    label = dj_tz.localtime(dj_tz.now()).strftime("%H:%M")
    return label, label


def _trim_thread_tail(msgs: list, request) -> None:
    msg_cap, _ = get_chat_limits_for_request(request)
    overflow = len(msgs) - msg_cap
    if overflow > 0:
        del msgs[:overflow]


def _touch_thread_recent(state: dict, thread_id: str) -> None:
    state["order"] = [thread_id] + [x for x in state["order"] if x != thread_id]
    state["active_id"] = thread_id


def _append_user_turn(request, thread_id: str, user_text: str) -> None:
    state = get_chat_state(request)
    if thread_id not in state["threads"]:
        return
    thread = state["threads"][thread_id]
    msgs = list(thread.get("messages") or [])
    tu, _ta = _chat_time_labels()
    msgs.append({"role": "user", "text": user_text, "time": tu})
    _trim_thread_tail(msgs, request)
    thread["messages"] = msgs
    _touch_thread_recent(state, thread_id)
    trim_chat_threads_for_request(request, state)
    save_chat_state(request, state)


def _append_assistant_turn(request, thread_id: str, assistant_text: str) -> None:
    state = get_chat_state(request)
    if thread_id not in state["threads"]:
        return
    thread = state["threads"][thread_id]
    msgs = list(thread.get("messages") or [])
    _tu, ta = _chat_time_labels()
    clean_ai = (
        clean_assistant_visible(assistant_text) if (assistant_text or "").strip() else assistant_text
    )
    msgs.append({"role": "assistant", "text": clean_ai, "time": ta})
    _trim_thread_tail(msgs, request)
    thread["messages"] = msgs
    finalize_thread_title(thread, msgs)
    _touch_thread_recent(state, thread_id)
    trim_chat_threads_for_request(request, state)
    save_chat_state(request, state)


def _append_turn_to_thread(request, thread_id: str, user_text: str, assistant_text: str) -> None:
    _append_user_turn(request, thread_id, user_text)
    _append_assistant_turn(request, thread_id, assistant_text)


AFISHA_PAGE_SIZE = 12


class AfishaView(TemplateView):
    template_name = "assistant/afisha.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_section"] = "afisha"
        db_path = _backend_db_path()
        search = (self.request.GET.get("q") or "").strip()
        context["search_query"] = search

        try:
            _ensure_afisha_db(db_path)
        except (RuntimeError, ValueError) as e:
            context["events"] = []
            context["page_obj"] = None
            context["afisha_error"] = str(e)
            return context

        events = _events_for_template(db_path, search=search or None)
        paginator = Paginator(events, AFISHA_PAGE_SIZE)
        context["page_obj"] = paginator.get_page(self.request.GET.get("page"))
        context["events"] = list(context["page_obj"].object_list)

        if events:
            context["events_db_nonempty"] = True
        else:
            context["events_db_nonempty"] = _events_table_nonempty(db_path)

        return context


class EventDetailView(TemplateView):
    template_name = "assistant/event_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_section"] = "afisha"
        db_path = _backend_db_path()
        try:
            _ensure_afisha_db(db_path)
        except (RuntimeError, ValueError) as e:
            raise Http404("База афиши недоступна") from e
        event = _event_detail_dict(db_path, int(kwargs["event_id"]))
        if event is None:
            raise Http404("Мероприятие не найдено")
        context["event"] = event
        return context


class ChatView(TemplateView):
    """Несколько чатов (вкладки в боковой панели), хранение в сессии."""

    template_name = "assistant/chat.html"

    def get(self, request, *args, **kwargs):
        ev_raw = request.GET.get("event")
        if ev_raw is not None and str(ev_raw).strip() != "":
            try:
                eid = int(ev_raw)
                if eid < 1:
                    raise ValueError
            except (TypeError, ValueError):
                return redirect("assistant:chat")

            db_path = _backend_db_path()
            try:
                _ensure_afisha_db(db_path)
            except (RuntimeError, ValueError):
                return redirect("assistant:chat")

            from database import fetch_event_by_id

            row = fetch_event_by_id(db_path, eid)
            if row is None:
                return redirect("assistant:afisha")

            state = get_chat_state(request)
            tid = new_thread_uid()
            while tid in state["threads"]:
                tid = new_thread_uid()

            event_name = (row["event_name"] or "").strip() or f"Событие #{eid}"
            try:
                from gigachat_advisor import introduce_event

                gk = gigachat_client_kw_for_request(request)
                intro, _ = introduce_event(db_path, eid, giga_kw=gk)
            except Exception as ex:
                logger.warning("introduce_event failed: %s", ex)
                from gigachat_advisor import fallback_event_intro

                intro = fallback_event_intro(row)
            intro = clean_assistant_visible(intro)

            t_intro = dj_tz.localtime(dj_tz.now()).strftime("%H:%M")
            thread = {
                "title": "Новый чат",
                "messages": [{"role": "assistant", "text": intro, "time": t_intro}],
                "focus_event_id": eid,
                "event_title_hint": event_name,
            }
            finalize_thread_title(thread, thread["messages"])
            state["threads"][tid] = thread
            state["order"].insert(0, tid)
            state["active_id"] = tid
            trim_chat_threads_for_request(request, state)
            save_chat_state(request, state)
            return redirect(f"{reverse('assistant:chat')}?chat={tid}")

        if request.GET.get("new"):
            state = get_chat_state(request)
            tid = new_thread_uid()
            while tid in state["threads"]:
                tid = new_thread_uid()
            state["threads"][tid] = {"title": "Новый чат", "messages": []}
            state["order"].insert(0, tid)
            state["active_id"] = tid
            trim_chat_threads_for_request(request, state)
            save_chat_state(request, state)
            return redirect(f"{reverse('assistant:chat')}?chat={tid}")

        state = get_chat_state(request)
        chat_param = request.GET.get("chat")
        if chat_param and chat_param in state["threads"]:
            if state["active_id"] != chat_param:
                state["active_id"] = chat_param
                save_chat_state(request, state)
        if state["active_id"] not in state["threads"]:
            state["active_id"] = state["order"][0]
            save_chat_state(request, state)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_section"] = "chat"
        state = get_chat_state(self.request)
        active_id = state["active_id"]
        thread = state["threads"][active_id]

        chats_sidebar: list[dict] = []
        for tid in state["order"]:
            t = state["threads"][tid]
            chats_sidebar.append({
                "id": tid,
                "title": t.get("title") or "Новый чат",
                "preview": thread_preview(t),
                "updated": last_time_label(t),
            })

        context["chats"] = chats_sidebar
        context["active_chat_id"] = active_id
        context["chat_messages"] = list(thread.get("messages") or [])
        context["active_chat"] = {"title": thread.get("title") or "Чат"}
        context["thread_focus_event_id"] = thread.get("focus_event_id")
        context["chat_api_url"] = reverse("assistant:api_chat")
        context["chat_clear_url"] = reverse("assistant:chat_clear")
        context["chat_new_url"] = f"{reverse('assistant:chat')}?new=1"
        return context


@require_POST
def local_gigachat_plan(request):
    """Сохраняет модель для локального доступа из блока под чатом (только loopback)."""
    if not request_is_loopback(request):
        return HttpResponseForbidden("Доступно только при локальном доступе (loopback).")
    slug = (request.POST.get("plan_slug") or "").strip()
    if slug not in allowed_plan_slugs():
        messages.error(request, "Неизвестная модель GigaChat.")
    else:
        request.session[LOCAL_GIGACHAT_SESSION_SLUG_KEY] = slug
        request.session.modified = True
        if request.user.is_authenticated:
            request.user.gigachat_plan_slug = slug
            request.user.save(update_fields=["gigachat_plan_slug"])
    next_url = (request.POST.get("next") or "").strip()
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("assistant:afisha")
    return HttpResponseRedirect(next_url)


def _chat_stream_ndjson_response(
    request,
    chat_id: str,
    message: str,
    db_path: str,
    *,
    focus,
    prior: list[dict],
) -> StreamingHttpResponse:
    """NDJSON: каждая строка — объект JSON с ключом «type»: delta | done | error."""
    gk = gigachat_client_kw_for_request(request)

    try:
        if focus is not None:
            from gigachat_advisor import chat_about_event_stream

            chunks = chat_about_event_stream(
                message, db_path, int(focus), prior, giga_kw=gk
            )
        else:
            from gigachat_advisor import recommend_events_stream

            chunks = recommend_events_stream(message, db_path, giga_kw=gk)
    except Exception as e:
        logger.exception("chat_api stream init")
        friendly_msg, _code = classify_chat_backend_failure(e)
        _append_turn_to_thread(request, chat_id, message, friendly_msg)
        one = ndjson_chat_error_line_bytes(e)
        resp = StreamingHttpResponse(iter([one]), content_type="application/x-ndjson; charset=utf-8")
        resp["Cache-Control"] = "no-store"
        resp["X-Accel-Buffering"] = "no"
        return resp

    def ndjson_chunks():
        _append_user_turn(request, chat_id, message)
        acc = ""
        try:
            for frag in chunks:
                acc += frag
                yield (
                    json.dumps({"type": "delta", "text": frag}, ensure_ascii=False) + "\n"
                ).encode("utf-8")
            raw = acc.strip()
            if not raw:
                raise RuntimeError("Пустой ответ модели")
            clean = clean_assistant_visible(raw)
            _append_assistant_turn(request, chat_id, clean)
            yield (
                json.dumps(
                    {
                        "type": "done",
                        "reply": clean,
                        "reply_html": str(assistant_reply_html(clean)),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")
        except Exception as e:
            logger.exception("chat_api stream consume")
            friendly_msg, _code = classify_chat_backend_failure(e)
            _append_assistant_turn(request, chat_id, friendly_msg)
            yield ndjson_chat_error_line_bytes(e)

    resp = StreamingHttpResponse(ndjson_chunks(), content_type="application/x-ndjson; charset=utf-8")
    resp["Cache-Control"] = "no-store"
    resp["X-Accel-Buffering"] = "no"
    return resp


@require_POST
def chat_api(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Неверный JSON.", "code": "invalid_json"},
            status=400,
        )

    message = (data.get("message") or "").strip()
    chat_id = (data.get("chat_id") or "").strip()

    state = get_chat_state(request)
    if not chat_id or chat_id not in state["threads"]:
        return JsonResponse(
            {"error": "Неизвестный чат или сессия устарела. Обновите страницу или откройте чат заново.", "code": "unknown_chat"},
            status=404,
        )

    if not message:
        return JsonResponse(
            {"error": "Введите текст вопроса.", "code": "empty_message"},
            status=400,
        )

    db_path = _backend_db_path()
    try:
        _ensure_afisha_db(db_path)
    except (RuntimeError, ValueError) as e:
        friendly_msg, err_code = classify_chat_backend_failure(e)
        _append_turn_to_thread(request, chat_id, message, friendly_msg)
        clean_err = clean_assistant_visible(friendly_msg)
        return JsonResponse(
            {
                "error": clean_err,
                "reply": clean_err,
                "reply_html": str(assistant_reply_html(clean_err)),
                "code": err_code,
            },
            status=400,
        )

    focus = state["threads"][chat_id].get("focus_event_id")
    prior = [
        {"role": m["role"], "text": m["text"]}
        for m in state["threads"][chat_id].get("messages", [])
    ]

    return _chat_stream_ndjson_response(
        request,
        chat_id,
        message,
        db_path,
        focus=focus,
        prior=prior,
    )


@require_POST
def chat_clear(request):
    state = get_chat_state(request)
    tid = (request.POST.get("thread_id") or "").strip() or state["active_id"]
    if tid in state["threads"]:
        t = state["threads"][tid]
        t["messages"] = []
        finalize_thread_title(t, [])
        save_chat_state(request, state)
    return redirect(f"{reverse('assistant:chat')}?chat={tid}")


@require_POST
def chat_delete_thread(request, thread_id: str):
    state = get_chat_state(request)
    thread_id = (thread_id or "").strip()
    if thread_id not in state["threads"]:
        return redirect("assistant:chat")

    del state["threads"][thread_id]
    state["order"] = [x for x in state["order"] if x != thread_id]

    if not state["order"]:
        tid = new_thread_uid()
        state["order"] = [tid]
        state["threads"][tid] = {"title": "Новый чат", "messages": []}
        state["active_id"] = tid
    elif state["active_id"] == thread_id:
        state["active_id"] = state["order"][0]
    elif state["active_id"] not in state["threads"]:
        state["active_id"] = state["order"][0]

    save_chat_state(request, state)
    return redirect(f"{reverse('assistant:chat')}?chat={state['active_id']}")
