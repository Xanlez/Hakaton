from django.urls import path

from . import auth_views, views

app_name = 'assistant'

urlpatterns = [
    path('', views.AfishaView.as_view(), name='afisha'),
    path(
        'local/gigachat-model/',
        views.local_gigachat_plan,
        name='local_gigachat_plan',
    ),
    path('event/<int:event_id>/', views.EventDetailView.as_view(), name='event_detail'),
    path('chat/thread/<str:thread_id>/delete/', views.chat_delete_thread, name='chat_delete'),
    path('chat/clear/', views.chat_clear, name='chat_clear'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('api/chat/', views.chat_api, name='api_chat'),
    path('cabinet/', auth_views.CabinetView.as_view(), name='cabinet'),
    path('accounts/register/done/', auth_views.AuthRegisterDoneView.as_view(), name='register_done'),
    path(
        'accounts/register/resend/',
        auth_views.resend_registration_email,
        name='register_resend',
    ),
    path('accounts/confirm/<str:token>/', auth_views.confirm_registration, name='confirm_registration'),
    path('accounts/login/', auth_views.AuthLoginView.as_view(), name='login'),
    path('accounts/register/', auth_views.AuthRegisterView.as_view(), name='register'),
    path('accounts/logout/', auth_views.AuthLogoutView.as_view(), name='logout'),
]
