from django.urls import path

from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.ChatView.as_view(), name='chat'),
    path('api/chat/', views.chat_api, name='api_chat'),
]
