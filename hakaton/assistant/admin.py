from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from assistant.models import ChatMessage, ChatThread, PendingRegistration, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "username", "gigachat_plan_slug", "is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Профиль",
            {"fields": ("username", "first_name", "last_name")},
        ),
        (
            "GigaChat (режим в ЛК)",
            {"fields": ("gigachat_plan_slug",)},
        ),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Даты",
            {"fields": ("last_login", "date_joined")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    ordering = ("sort_order", "pk")


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "created_at")
    search_fields = ("username", "email")
    ordering = ("-created_at",)
    readonly_fields = ("token_digest", "created_at")


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("thread_id", "title", "user", "focus_event_id", "sort_rank", "updated_at")
    list_filter = ("user",)
    search_fields = ("thread_id", "title")
    ordering = ("user", "sort_rank")
    inlines = (ChatMessageInline,)
