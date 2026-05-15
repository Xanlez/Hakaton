import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from assistant.chat_storage import merge_guest_session_into_user
from assistant.email_activation import check_activation_token, send_activation_email
from assistant.forms import AuthLoginForm, RegisterForm

logger = logging.getLogger(__name__)


class AuthLoginView(DjangoLoginView):
    template_name = "assistant/auth_login.html"
    redirect_authenticated_user = True
    authentication_form = AuthLoginForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "login"
        return ctx

    def form_valid(self, form):
        merge_guest_session_into_user(self.request, form.get_user())
        return super().form_valid(form)


class AuthRegisterView(FormView):
    template_name = "assistant/auth_register.html"
    form_class = RegisterForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "register"
        return ctx

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        merge_guest_session_into_user(self.request, user)

        try:
            send_activation_email(self.request, user)
            messages.success(
                self.request,
                "На указанную почту отправлено письмо со ссылкой для подтверждения.",
            )
        except Exception:
            logger.exception("send_activation_email failed for %s", user.pk)
            messages.warning(
                self.request,
                "Аккаунт создан, но письмо не отправилось. Настройте SMTP (переменные DJANGO_EMAIL_*) "
                "или обратитесь к администратору.",
            )

        return redirect("assistant:register_done")


class AuthRegisterDoneView(TemplateView):
    template_name = "assistant/auth_register_done.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "register"
        return ctx


def activate_account(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=int(uid))
    except (ValueError, TypeError, OverflowError, User.DoesNotExist):
        user = None

    if user is None:
        return render(
            request,
            "assistant/auth_activation_invalid.html",
            {"nav_section": "login"},
            status=400,
        )

    if user.is_active:
        messages.info(request, "Этот аккаунт уже подтверждён — можно войти.")
        return redirect("assistant:login")

    if check_activation_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(
            request,
            "Почта подтверждена. Теперь войдите с именем пользователя и паролем.",
        )
        return redirect("assistant:login")

    return render(
        request,
        "assistant/auth_activation_invalid.html",
        {"nav_section": "login"},
        status=400,
    )


class CabinetView(LoginRequiredMixin, TemplateView):
    template_name = "assistant/cabinet.html"

    login_url = reverse_lazy("assistant:login")

    def get_context_data(self, **kwargs):
        from assistant.models import ChatThread

        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "cabinet"
        ctx["saved_thread_count"] = ChatThread.objects.filter(user=self.request.user).count()
        return ctx


class AuthLogoutView(DjangoLogoutView):
    next_page = reverse_lazy("assistant:afisha")
