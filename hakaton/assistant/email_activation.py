# Отправка письма с подтверждением регистрации (до создания пользователя)
from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse


def confirm_registration_url_abs(request: HttpRequest, token: str) -> str:
    path = reverse(
        "assistant:confirm_registration",
        kwargs={"token": token},
    )
    return request.build_absolute_uri(path)


def send_pending_registration_email(request: HttpRequest, *, username: str, email: str, token: str) -> None:
    em = (email or "").strip()
    if not em:
        return
    confirm_url = confirm_registration_url_abs(request, token)
    ctx = {"username": username, "confirm_url": confirm_url}
    subject = render_to_string(
        "assistant/email/registration_confirm_subject.txt",
        ctx,
    ).strip()
    body_text = render_to_string(
        "assistant/email/registration_confirm_body.txt",
        ctx,
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    send_mail(
        subject=subject,
        message=body_text,
        from_email=from_email,
        recipient_list=[em],
        fail_silently=False,
    )
