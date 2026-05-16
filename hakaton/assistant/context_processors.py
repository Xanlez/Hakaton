from django.urls import reverse

from assistant.gigachat_plan_prefs import local_banner_selected_slug, plan_options_ordered
from assistant.local_request import request_is_loopback


def local_gigachat_banner(request):
    """Данные для выпадающего списка модели в чате при локальном доступе (loopback)."""
    from django.conf import settings

    show = getattr(settings, "ASSISTANT_LOCAL_GIGACHAT_BANNER", True) and request_is_loopback(
        request
    )
    if not show:
        return {
            "show_local_gigachat_banner": False,
            "local_gigachat_banner_options": [],
            "local_gigachat_banner_slug": "",
            "local_gigachat_plan_url": "",
        }
    slug = local_banner_selected_slug(request)
    opts = [
        {"slug": p["slug"], "label": (p.get("label") or p["slug"]).strip()}
        for p in plan_options_ordered()
    ]
    return {
        "show_local_gigachat_banner": True,
        "local_gigachat_banner_options": opts,
        "local_gigachat_banner_slug": slug,
        "local_gigachat_plan_url": reverse("assistant:local_gigachat_plan"),
    }
