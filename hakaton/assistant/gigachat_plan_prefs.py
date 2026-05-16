"""Профиль GigaChat (scope/model) для залогиненного пользователя."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest

LOCAL_GIGACHAT_SESSION_SLUG_KEY = "assistant_local_gigachat_plan_slug"


def plan_options_ordered() -> tuple[dict[str, Any], ...]:
    opts = getattr(settings, "GIGACHAT_PLAN_OPTIONS", ()) or ()
    tup = tuple(opts)
    if not tup:
        return (
            {"slug": "gigachat", "label": "GigaChat", "scope": "", "model": "GigaChat"},
            {"slug": "gigachat-pro", "label": "GigaChat-Pro", "scope": "", "model": "GigaChat-Pro"},
            {"slug": "gigachat-max", "label": "GigaChat-Max", "scope": "", "model": "GigaChat-Max"},
        )
    return tup


def allowed_plan_slugs() -> frozenset[str]:
    return frozenset(p["slug"] for p in plan_options_ordered())


def plan_default_slug() -> str:
    return (getattr(settings, "GIGACHAT_PLAN_DEFAULT_SLUG", None) or "gigachat").strip()


def slug_to_plan(slug: str | None) -> dict[str, Any]:
    opts = plan_options_ordered()
    slug_clean = ((slug or "").strip() or plan_default_slug())
    for p in opts:
        if p.get("slug") == slug_clean:
            return dict(p)
    for p in opts:
        if p.get("slug") == plan_default_slug():
            return dict(p)
    return dict(opts[0])


def local_banner_selected_slug(request: HttpRequest) -> str:
    """Slug выпадающего списка в чате при локальном доступе: сессия → профиль в БД → default."""
    allowed = allowed_plan_slugs()
    sess = (request.session.get(LOCAL_GIGACHAT_SESSION_SLUG_KEY) or "").strip()
    if sess in allowed:
        return sess
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        db_slug = (getattr(user, "gigachat_plan_slug", None) or "").strip()
        if db_slug in allowed:
            return db_slug
    return plan_default_slug()


def enrich_plans_with_balance(
    plan_opts: tuple[dict[str, Any], ...],
    balance_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Сопоставляет строки ответа get_balance (поле usage) с model пресета."""
    bal: dict[str, float] = {}
    bal_lower: dict[str, float] = {}
    for r in balance_rows or []:
        u = (r.get("usage") or "").strip()
        if not u or u == "—":
            continue
        v = float(r.get("value") or 0)
        bal[u] = v
        bal_lower[u.lower()] = v

    out: list[dict[str, Any]] = []
    for p in plan_opts:
        d = dict(p)
        busage = (d.pop("balance_usage", None) or "").strip()
        model = (d.get("model") or "").strip()
        key = busage or model
        remain: float | None = None
        if key:
            remain = bal.get(key)
            if remain is None:
                remain = bal_lower.get(key.lower())
        d["balance_remain"] = remain
        out.append(d)
    return out


def gigachat_client_kw_for_request(request: HttpRequest) -> dict[str, Any]:
    """
    С внешнего IP — всегда model/scope из .env («обычный» один режим).
    С локального loopback — модель как в выпадающем списке в блоке чата (сессия / профиль) + опционально свободный промпт.
    """
    from config import GIGACHAT_MODEL, GIGACHAT_SCOPE

    from assistant.local_request import local_llm_simple_enabled, request_is_loopback

    if not request_is_loopback(request):
        return {"scope": GIGACHAT_SCOPE, "model": GIGACHAT_MODEL}

    p = slug_to_plan(local_banner_selected_slug(request))
    scope = ((p.get("scope") or "") or "").strip() or GIGACHAT_SCOPE
    model = ((p.get("model") or "") or "").strip() or GIGACHAT_MODEL
    kw: dict[str, Any] = {"scope": scope, "model": model}
    if local_llm_simple_enabled(request):
        kw["_local_llm_simple"] = True
    return kw
