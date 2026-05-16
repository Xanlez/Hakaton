from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("The email must be set"))
        email = self.normalize_email((email or "").strip().lower())
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Идентификация только по почте (unique). Поле username — необязательное отображаемое имя, без уникальности.
    """

    username = models.CharField(_("display name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), unique=True)
    gigachat_plan_slug = models.CharField(
        _("GigaChat plan"),
        max_length=32,
        default="gigachat",
        help_text="Модель GigaChat для чата (slug из settings.GIGACHAT_PLAN_OPTIONS).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email

    def natural_key(self) -> tuple[str]:
        return (self.email.lower(),)

    @classmethod
    def get_by_natural_key(cls, email: str):
        return cls._default_manager.get(email__iexact=email.strip().lower())


class PendingRegistration(models.Model):
    """Регистрация до создания пользователя; одна активная заявка на почту."""

    username = models.CharField(max_length=150, blank=True, default="", db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    password_hash = models.CharField(
        max_length=512,
        help_text="Django-хэш пароля; в БД может храниться в виде Fernet (префикс e1:).",
    )
    token_digest = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="HMAC-SHA256 секрета ссылки (сама ссылка в БД не хранится).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class ChatThread(models.Model):
    """Чат помощника пользователя — один поток вкладки в интерфейсе."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_threads",
    )
    thread_id = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Строковый id из UI (случайный hex).",
    )
    title = models.CharField(max_length=200, default="Новый чат")
    sort_rank = models.PositiveIntegerField(default=0)
    focus_event_id = models.IntegerField(null=True, blank=True)
    event_title_hint = models.CharField(max_length=256, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "thread_id"),
                name="assistant_chatthread_user_thread_uid",
            )
        ]
        ordering = ("sort_rank", "updated_at")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.thread_id} {self.title[:40]}"


class ChatMessage(models.Model):
    """Сообщение внутри чата."""

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"

    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages_rows",
    )
    role = models.CharField(max_length=16)
    text = models.TextField()
    time_label = models.CharField(max_length=16, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
