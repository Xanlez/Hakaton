"""Человекочитаемые сообщения для ошибок GigaChat и сетевого стека."""
from __future__ import annotations

import json
from typing import Any

import httpx
from django.conf import settings


def classify_chat_backend_failure(exc: BaseException) -> tuple[str, str]:
    """
    Возвращает (текст для пользователя в чате, короткий machine-readable code).
    """
    from gigachat.exceptions import (
        AuthenticationError,
        BadRequestError,
        ForbiddenError,
        LengthFinishReasonError,
        NotFoundError,
        RateLimitError,
        RequestEntityTooLargeError,
        ResponseError,
        ServerError,
        UnprocessableEntityError,
    )

    exc_type_name = type(exc).__name__

    if isinstance(exc, LengthFinishReasonError):
        return (
            "Ответ модели был обрезан по лимиту длины. Сократите вопрос или начните новый чат.",
            "length_finish",
        )

    if isinstance(exc, httpx.TimeoutException):
        return (
            "Превышено время ожидания ответа от GigaChat. Проверьте сеть или повторите запрос через минуту.",
            "upstream_timeout",
        )
    if isinstance(exc, httpx.ConnectError):
        return (
            "Не удалось подключиться к серверам GigaChat (сеть или блокировка). Проверьте интернет, VPN или корпоративный файрвол.",
            "upstream_connect",
        )
    if isinstance(exc, httpx.RemoteProtocolError):
        return (
            "Соединение с GigaChat неожиданно оборвалось. Отправьте сообщение ещё раз.",
            "upstream_disconnect",
        )
    if isinstance(exc, httpx.RequestError):
        return (
            "Сетевая ошибка при обращении к GigaChat: "
            + (str(exc).strip() or "проверьте соединение."),
            "upstream_request",
        )

    if isinstance(exc, AuthenticationError):
        return (
            "Не удалось авторизоваться в GigaChat (401). Проверьте GIGACHAT_CREDENTIALS и scope модели.",
            "gigachat_auth",
        )
    if isinstance(exc, ForbiddenError):
        return (
            "Доступ к ресурсу GigaChat запрещён (403): проверьте scope тариф и права ключей.",
            "gigachat_forbidden",
        )
    if isinstance(exc, NotFoundError):
        return (
            "GigaChat вернул «не найдено» (404): модель или эндпоинт временно недоступны.",
            "gigachat_not_found",
        )
    if isinstance(exc, BadRequestError):
        return (
            "Неверный запрос к GigaChat (400). Попробуйте переформулировать сообщение или сменить режим модели.",
            "gigachat_bad_request",
        )
    if isinstance(exc, RequestEntityTooLargeError):
        return (
            "Сообщение слишком длинное для GigaChat (413). Сократите текст или разбейте на части.",
            "gigachat_too_large",
        )
    if isinstance(exc, UnprocessableEntityError):
        return (
            "Запрос к GigaChat не принят как корректный (422). Попробуйте упростить формулировку.",
            "gigachat_unprocessable",
        )
    if isinstance(exc, RateLimitError):
        return (
            "Слишком много запросов к GigaChat (429). Подождите минуту и повторите попытку.",
            "rate_limit",
        )
    if isinstance(exc, ServerError):
        sc = getattr(exc, "status_code", None)
        suffix = " ({0})".format(sc) if isinstance(sc, int) else ""
        return (
            "На стороне GigaChat временные неполадки (сервер{0}). Повторите запрос позже.".format(suffix),
            "gigachat_server",
        )
    if isinstance(exc, ResponseError):
        status = int(getattr(exc, "status_code", 0) or 0)
        api_code = "http_{0}".format(status) if status else "gigachat_http"

        by_status: dict[int, tuple[str, str]] = {
            401: ("Авторизация в GigaChat не удалась (401).", "http_401"),
            402: ("Недостаточно средств или квоты по тарифу GigaChat (402).", "http_402"),
            403: ("Отказ доступа со стороны GigaChat (403). Проверьте scope модели.", "http_403"),
            404: (
                "Ресурс или метод GigaChat недоступен (404): проверьте имя модели и параметры доступа.",
                "http_404",
            ),
            413: (
                "Сообщение слишком длинное для GigaChat (413). Укоротите текст.",
                "http_413",
            ),
            429: ("Сервис временно ограничил частоту запросов (429). Попробуйте позже.", "http_429"),
            503: ("GigaChat перегружен или на обслуживании (503). Повторите позже.", "http_503"),
        }
        if status in by_status:
            return by_status[status]

        generic_no_status = (
            "Сервис GigaChat вернул ошибку. Попробуйте позже."
            if not status
            else "Сервис GigaChat вернул ошибку HTTP {0}. Попробуйте позже.".format(status)
        )

        if settings.DEBUG:
            snippet = ""
            raw = getattr(exc, "content", None)
            if isinstance(raw, (bytes, bytearray)):
                snippet = raw[:400].decode("utf-8", errors="replace").strip()
            parts = ["{0} ({1})".format(generic_no_status.rstrip("."), exc_type_name)]
            if snippet:
                parts.append(snippet)
            return ("\n".join(parts), api_code)

        return generic_no_status, api_code

    if isinstance(exc, ValueError):
        raw = str(exc).strip()
        if raw:
            return raw, "value_error"

    if isinstance(exc, RuntimeError):
        raw = str(exc).strip()
        low = raw.lower()
        if "credential" in low or ("задайте" in low and "gigachat" in low):
            return (raw or "Не заданы учётные данные GigaChat.", "credentials_missing")
        if "пустой" in low and ("ответ" in low or "модел" in low):
            return (
                "GigaChat не вернул текста ответа. Попробуйте отправить сообщение ещё раз или сменить модель.",
                "empty_model_reply",
            )
        if raw:
            return (raw, "runtime_error")

    if settings.DEBUG:
        return ("{0}: {1}".format(exc_type_name, str(exc)), "debug_exception")

    return (
        "Произошла ошибка помощника ({0}). Попробуйте ещё раз позже.".format(exc_type_name),
        "unknown",
    )


def json_error_chat_payload(exc: BaseException) -> dict[str, Any]:
    """Поля для NDJSON ошибки или JSON ответа API чата."""
    message, code = classify_chat_backend_failure(exc)
    return {"type": "error", "message": message, "code": code}


def ndjson_chat_error_line_bytes(exc: BaseException) -> bytes:
    """Одна NDJSON-строка ошибки потока / API с готовым HTML для пузырька."""
    from assistant.formatting import assistant_reply_html, clean_assistant_visible

    friendly, code = classify_chat_backend_failure(exc)
    clean_f = clean_assistant_visible(friendly)
    blob = {
        "type": "error",
        "message": clean_f,
        "code": code,
        "reply_html": str(assistant_reply_html(clean_f)),
    }
    return (json.dumps(blob, ensure_ascii=False) + "\n").encode("utf-8")
