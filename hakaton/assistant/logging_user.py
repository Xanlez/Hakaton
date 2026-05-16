"""Контекст пользователя в логах: middleware + фильтр для Formatter."""
from __future__ import annotations

import logging
from contextvars import ContextVar

_user_logging_repr: ContextVar[str | None] = ContextVar("user_logging_repr", default=None)


def bind_user_logging_context(user_repr: str | None):
    """Возвращает token для последующего reset_user_logging_context (try/finally)."""
    return _user_logging_repr.set(user_repr)


def reset_user_logging_context(token) -> None:
    _user_logging_repr.reset(token)


def current_user_logging_repr() -> str | None:
    return _user_logging_repr.get()


def format_user_for_logs(user) -> str:
    if user is None:
        return "anon"
    if getattr(user, "is_authenticated", False) is not True:
        return "anon"
    pk = getattr(user, "pk", None)
    email = (getattr(user, "email", None) or "").strip()
    name = (getattr(user, "username", "") or "").strip()
    bits: list[str] = []
    if pk is not None:
        bits.append(f"id={pk}")
    if email:
        bits.append(f"email={email}")
    if name:
        bits.append(f"name={name!r}")
    return " ".join(bits) if bits else "authenticated"


class UserLoggingFilter(logging.Filter):
    """Добавляет в запись атрибут user_repr для форматтера вида [... {user_repr} ...]."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "user_repr"):
            record.user_repr = current_user_logging_repr() or "-"
        return True


class AttachUserLoggingContextMiddleware:
    """Сразу после AuthenticationMiddleware задаёт строку пользователя для всех последующих логов."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = getattr(request, "user", None)
        token = bind_user_logging_context(format_user_for_logs(u))
        try:
            return self.get_response(request)
        finally:
            reset_user_logging_context(token)
