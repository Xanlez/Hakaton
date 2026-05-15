# Generated manually for secure pending registration storage

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import migrations, models


def _token_digest(token: str, pepper_raw) -> str:
    pepper = pepper_raw.encode("utf-8") if isinstance(pepper_raw, str) else bytes(pepper_raw)
    return hmac.new(pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()


def forwards_digest(apps, schema_editor):
    Pending = apps.get_model("assistant", "PendingRegistration")
    pepper = getattr(settings, "REGISTRATION_TOKEN_PEPPER", None) or settings.SECRET_KEY
    for p in Pending.objects.all():
        p.token_digest = _token_digest(p.token, pepper)
        p.save(update_fields=["token_digest"])


def forwards_encrypt_passwords(apps, schema_editor):
    Pending = apps.get_model("assistant", "PendingRegistration")
    PW = "e1:"
    explicit = getattr(settings, "REGISTRATION_PENDING_PASSWORD_FERNET_KEY", None)
    if explicit:
        key = str(explicit).strip().encode("ascii")
    else:
        key = base64.urlsafe_b64encode(
            hashlib.sha256((settings.SECRET_KEY + "|assistant|pending-reg-pw|v1").encode("utf-8")).digest(),
        )
    f = Fernet(key)
    for p in Pending.objects.exclude(password_hash__startswith=PW):
        p.password_hash = PW + f.encrypt(p.password_hash.encode("utf-8")).decode("ascii")
        p.save(update_fields=["password_hash"])


def backwards_decrypt_passwords(apps, schema_editor):
    Pending = apps.get_model("assistant", "PendingRegistration")
    PW = "e1:"
    explicit = getattr(settings, "REGISTRATION_PENDING_PASSWORD_FERNET_KEY", None)
    if explicit:
        key = str(explicit).strip().encode("ascii")
    else:
        key = base64.urlsafe_b64encode(
            hashlib.sha256((settings.SECRET_KEY + "|assistant|pending-reg-pw|v1").encode("utf-8")).digest(),
        )
    f = Fernet(key)
    for p in Pending.objects.filter(password_hash__startswith=PW):
        ciphertext = p.password_hash[len(PW) :]
        p.password_hash = f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        p.save(update_fields=["password_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pendingregistration",
            name="password_hash",
            field=models.CharField(
                max_length=512,
                help_text="Django-хэш пароля; в БД может храниться в виде Fernet (префикс e1:).",
            ),
        ),
        migrations.AddField(
            model_name="pendingregistration",
            name="token_digest",
            field=models.CharField(db_index=True, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(forwards_digest, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pendingregistration",
            name="token",
        ),
        migrations.AlterField(
            model_name="pendingregistration",
            name="token_digest",
            field=models.CharField(
                db_index=True,
                help_text="HMAC-SHA256 секрета ссылки (сама ссылка в БД не хранится).",
                max_length=64,
                unique=True,
            ),
        ),
        migrations.RunPython(forwards_encrypt_passwords, backwards_decrypt_passwords),
    ]
