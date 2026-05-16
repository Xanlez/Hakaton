"""Кастомные страницы HTTP-ошибок в стиле интерфейса сайта."""

from django.shortcuts import render


def page_not_found(request, exception=None):
    return render(
        request,
        "assistant/404.html",
        {"nav_section": "afisha", "path": request.path},
        status=404,
    )


def server_error(request):
    return render(
        request,
        "assistant/500.html",
        {"nav_section": "afisha"},
        status=500,
    )
