from django.contrib import admin
from django.urls import include, path

from assistant.error_views import page_not_found, server_error

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("assistant.urls")),
]

handler404 = page_not_found
handler500 = server_error
