import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _backend_db_path() -> str:
    from config import DB_PATH

    p = Path(DB_PATH)
    return str(p if p.is_absolute() else _REPO_ROOT / DB_PATH)


class ChatView(TemplateView):
    """Чат на сайте: ответы приходят через /api/chat/ (GigaChat + SQLite афиша)."""

    template_name = "assistant/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chats = [
            {
                "id": "live",
                "title": "Афиша «Сириус»",
                "preview": "Рекомендации из вашей локальной базы событий",
                "updated": "",
            },
        ]
        context["chats"] = chats
        context["active_chat"] = chats[0]
        context["active_chat_id"] = "live"
        context["messages"] = []
        context["chat_api_url"] = reverse("assistant:api_chat")
        return context


@require_POST
def chat_api(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Неверный JSON"}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Введите вопрос"}, status=400)

    db_path = _backend_db_path()
    try:
        from chat import ensure_db

        ensure_db(db_path, force=False)
    except (RuntimeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)

    try:
        from gigachat_advisor import recommend_events

        reply = recommend_events(message, db_path)
    except Exception as e:
        logger.exception("chat_api")
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"reply": reply})
