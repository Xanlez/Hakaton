# Отправка письма с подтверждением email
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """Токен привязан к пользователю, почте и паролю."""

    def _make_hash_value(self, user, timestamp):
        login_ts = "" if user.last_login is None else str(user.last_login.timestamp())
        return f"{user.pk}:{user.email}:{timestamp}:{user.is_active}:{user.password}:{login_ts}"


activation_token_generator = AccountActivationTokenGenerator()


def activation_uid_token(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = activation_token_generator.make_token(user)
    return uid, token


def activate_url_abs(request: HttpRequest, uid_b64: str, token: str) -> str:
    path = reverse(
        "assistant:activate",
        kwargs={"uidb64": uid_b64, "token": token},
    )
    return request.build_absolute_uri(path)


def send_activation_email(request: HttpRequest, user) -> None:
    uid_b64, token = activation_uid_token(user)
    email = (user.email or "").strip()
    if not email:
        return
    activate_url = activate_url_abs(request, uid_b64, token)
    ctx = {"username": user.username, "activate_url": activate_url}
    subject = render_to_string(
        "assistant/email/activation_subject.txt",
        ctx,
        autoescape=False,
    ).strip()
    body_text = render_to_string(
        "assistant/email/activation_body.txt",
        ctx,
        autoescape=False,
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    send_mail(
        subject=subject,
        message=body_text,
        from_email=from_email,
        recipient_list=[email],
        fail_silently=False,
    )


def check_activation_token(user, token: str) -> bool:
    return activation_token_generator.check_token(user, token)
