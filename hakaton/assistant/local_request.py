"""Запросы с локальной машины (loopback): упрощаем поведение GigaChat и лимиты чата."""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def request_is_loopback(request: HttpRequest) -> bool:
    ip = (request.META.get("REMOTE_ADDR") or "").strip()
    ip_l = ip.lower()
    if ip_l.startswith("::ffff:"):
        ip_l = ip_l[7:].strip()
    if not ip_l:
        return False
    if ip_l in ("127.0.0.1", "::1", "localhost"):
        return True
    if ip_l.startswith("127.") and ip_l.count(".") == 3:
        return True
    return False


def local_llm_simple_enabled(request: HttpRequest) -> bool:
    """Свободный режим промпта GigaChat (как универсальный диалог)."""
    if not getattr(settings, "ASSISTANT_LOCAL_LL_SIMPLE", True):
        return False
    if getattr(settings, "ASSISTANT_LOCAL_LL_SIMPLE_REQUIRE_DEBUG", False) and not settings.DEBUG:
        return False
    return request_is_loopback(request)


def get_chat_limits_for_request(request: HttpRequest) -> tuple[int, int]:
    """Число сообщений в потоке и число потоков; для локального клиента выше порог из settings."""
    from assistant.chat_storage import CHAT_MESSAGES_PER_THREAD_MAX, CHAT_THREADS_MAX

    msg_max = CHAT_MESSAGES_PER_THREAD_MAX
    thr_max = CHAT_THREADS_MAX
    if getattr(settings, "ASSISTANT_LOCAL_RELAX_CHAT_LIMITS", True) and local_llm_simple_enabled(request):
        msg_max = int(getattr(settings, "CHAT_LOCAL_MESSAGES_PER_THREAD_MAX", msg_max))
        thr_max = int(getattr(settings, "CHAT_LOCAL_THREADS_MAX", thr_max))
    return msg_max, thr_max


def trim_chat_threads_for_request(request: HttpRequest, state: dict) -> None:
    from assistant.chat_storage import trim_thread_list

    _, thr_max = get_chat_limits_for_request(request)
    trim_thread_list(state, threads_max=thr_max)
