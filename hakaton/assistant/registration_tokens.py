"""
Токены подтверждения регистрации: только в письме в открытом виде, в БД — отпечаток (HMAC).
Пароль в pending — Fernet (at-rest), ключ выводится из SECRET_KEY / отдельной env.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from django.conf import settings

PW_CIPHER_PREFIX = "e1:"


def _pepper_bytes() -> bytes:
    pepper = getattr(settings, "REGISTRATION_TOKEN_PEPPER", None) or settings.SECRET_KEY
    if isinstance(pepper, str):
        return pepper.encode("utf-8")
    return bytes(pepper)


def registration_token_digest(raw_token: str) -> str:
    return hmac.new(
        _pepper_bytes(),
        (raw_token or "").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def new_registration_token_pair() -> tuple[str, str]:
    """Возвращает (секрет для ссылки, отпечаток для БД)."""
    raw = secrets.token_urlsafe(32)
    return raw, registration_token_digest(raw)


def _fernet_for_pending_password():
    from cryptography.fernet import Fernet

    explicit = getattr(settings, "REGISTRATION_PENDING_PASSWORD_FERNET_KEY", None)
    if explicit:
        key = (explicit if isinstance(explicit, str) else explicit.decode()).strip().encode("ascii")
    else:
        material = hashlib.sha256(
            (settings.SECRET_KEY + "|assistant|pending-reg-pw|v1").encode("utf-8"),
        ).digest()
        key = base64.urlsafe_b64encode(material)
    return Fernet(key)


def encrypt_pending_password_hash(password_hash: str) -> str:
    if not password_hash or password_hash.startswith(PW_CIPHER_PREFIX):
        return password_hash
    f = _fernet_for_pending_password()
    token = f.encrypt(password_hash.encode("utf-8")).decode("ascii")
    return PW_CIPHER_PREFIX + token


def decrypt_pending_password_hash(stored: str) -> str:
    if not stored or not stored.startswith(PW_CIPHER_PREFIX):
        return stored
    f = _fernet_for_pending_password()
    return f.decrypt(stored[len(PW_CIPHER_PREFIX) :].encode("ascii")).decode("utf-8")


def rotate_pending_registration_token(
    pending,
    *,
    username: str | None = None,
    password_hash: str | None = None,
) -> str:
    """
    Новый секрет для ссылки; все ранее выданные ссылки перестают работать.
    При повторной регистрации можно обновить username и Django-хэш пароля.
    """
    raw, digest = new_registration_token_pair()
    pending.token_digest = digest
    if username is not None:
        pending.username = username
    if password_hash is not None:
        pending.password_hash = encrypt_pending_password_hash(password_hash)
    else:
        pending.password_hash = encrypt_pending_password_hash(
            decrypt_pending_password_hash(pending.password_hash),
        )
    update_fields = ["token_digest", "password_hash"]
    if username is not None:
        update_fields.append("username")
    pending.save(update_fields=update_fields)
    return raw
