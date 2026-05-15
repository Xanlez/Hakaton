from django.contrib import admin

from assistant.models import ChatMessage, ChatThread


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    ordering = ("sort_order", "pk")


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("thread_id", "title", "user", "focus_event_id", "sort_rank", "updated_at")
    list_filter = ("user",)
    search_fields = ("thread_id", "title")
    ordering = ("user", "sort_rank")
    inlines = (ChatMessageInline,)
