from django.conf import settings
from django.db import models


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
