import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import make_password
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone as dj_tz
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from assistant.chat_storage import merge_guest_session_into_user
from assistant.email_activation import send_pending_registration_email

from assistant.registration_tokens import (
    decrypt_pending_password_hash,
    encrypt_pending_password_hash,
    new_registration_token_pair,
    registration_token_digest,
    rotate_pending_registration_token,
)
from assistant.forms import AuthLoginForm, RegisterForm, ResendRegistrationForm
from assistant.models import PendingRegistration

logger = logging.getLogger(__name__)

PENDING_LINK_MAX_AGE = timedelta(hours=72)
PENDING_REGISTRATION_EMAIL_SESSION_KEY = "pending_registration_email"
RESEND_REGISTRATION_COOLDOWN_SEC = 60


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
        username = form.cleaned_data["username"]
        email = (form.cleaned_data["email"] or "").strip().lower()
        raw_password = form.cleaned_data["password1"]

        password_hash = make_password(raw_password)
        pending = PendingRegistration.objects.filter(email__iexact=email).first()
        if pending is not None:
            plain_token = rotate_pending_registration_token(
                pending,
                username=username,
                password_hash=password_hash,
            )
        else:
            plain_token, token_digest = new_registration_token_pair()
            pending = PendingRegistration.objects.create(
                username=username,
                email=email,
                password_hash=encrypt_pending_password_hash(password_hash),
                token_digest=token_digest,
            )

        try:
            send_pending_registration_email(
                self.request,
                username=pending.username,
                email=pending.email,
                token=plain_token,
            )
            self.request.session[PENDING_REGISTRATION_EMAIL_SESSION_KEY] = email
            messages.success(
                self.request,
                "На почту отправлена ссылка. Аккаунт появится только после перехода по ней. "
                "Ранее выданные ссылки для этой почты больше не действуют.",
            )
        except Exception as exc:
            logger.exception("send_pending_registration_email failed for pending %s", pending.pk)
            pending.delete()
            hint = (
                "Настройте отправку в файле .env (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM) "
                "или переменные DJANGO_EMAIL_*."
            )
            tail = f" Техническая причина ({type(exc).__name__}): {exc}" if settings.DEBUG else ""
            messages.error(
                self.request,
                "Письмо не отправилось — запись о регистрации не сохранена. " + hint + tail,
            )

        return redirect("assistant:register_done")


class AuthRegisterDoneView(TemplateView):
    template_name = "assistant/auth_register_done.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "register"
        initial_email = self.request.session.get(PENDING_REGISTRATION_EMAIL_SESSION_KEY, "")
        ctx["resend_form"] = ResendRegistrationForm(initial={"email": initial_email})
        return ctx


@require_POST
def resend_registration_email(request: HttpRequest) -> HttpResponse:
    form = ResendRegistrationForm(request.POST)
    if not form.is_valid():
        for err in form.errors.get("email", form.non_field_errors()):
            messages.error(request, err)
        return redirect("assistant:register_done")

    email = form.cleaned_data["email"]
    throttle_key = f"assistant:resend_reg:{email}"
    if cache.get(throttle_key):
        messages.info(
            request,
            "Письмо уже отправляли недавно. Подождите около минуты или проверьте папку «Спам».",
        )
        return redirect("assistant:register_done")

    pending = PendingRegistration.objects.filter(email__iexact=email).first()
    if pending is not None:
        plain_token = rotate_pending_registration_token(pending)
        try:
            send_pending_registration_email(
                request,
                username=pending.username,
                email=pending.email,
                token=plain_token,
            )
            cache.set(throttle_key, 1, RESEND_REGISTRATION_COOLDOWN_SEC)
            request.session[PENDING_REGISTRATION_EMAIL_SESSION_KEY] = email
            logger.info("registration email resent (token rotated) for pending pk=%s", pending.pk)
        except Exception as exc:
            logger.exception("resend_pending_registration_email failed for pending %s", pending.pk)
            tail = f" ({type(exc).__name__}: {exc})" if settings.DEBUG else ""
            messages.error(
                request,
                "Не удалось отправить письмо. Проверьте SMTP или настройки DJANGO_EMAIL_*." + tail,
            )
            return redirect("assistant:register_done")

    messages.success(
        request,
        "Если на этот адрес есть незавершённая регистрация, отправлена новая ссылка. "
        "Старые ссылки из писем больше не действуют.",
    )
    return redirect("assistant:register_done")


def confirm_registration(request: HttpRequest, token: str) -> HttpResponse:
    digest = registration_token_digest((token or "").strip())
    pending = PendingRegistration.objects.filter(token_digest=digest).first()

    if pending is None:
        return render(
            request,
            "assistant/auth_activation_invalid.html",
            {"nav_section": "login"},
            status=400,
        )

    now = dj_tz.now()
    if pending.created_at + PENDING_LINK_MAX_AGE < now:
        pending.delete()
        messages.error(
            request,
            "Ссылка устарела. Зарегистрируйтесь снова — новое письмо придёт на почту.",
        )
        return redirect("assistant:register")

    User = get_user_model()
    if User.objects.filter(email__iexact=pending.email).exists():
        pending.delete()
        messages.info(request, "Аккаунт с этой почтой уже есть — войдите.")
        return redirect("assistant:login")

    try:
        with transaction.atomic():
            user = User(
                username=pending.username,
                email=pending.email,
                is_active=True,
            )
            user.password = decrypt_pending_password_hash(pending.password_hash)
            user.save()
            pending.delete()
    except IntegrityError:
        pending.delete()
        messages.error(request, "Не удалось создать аккаунт (конфликт данных). Попробуйте снова.")
        return redirect("assistant:register")

    merge_guest_session_into_user(request, user)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Регистрация подтверждена — вы вошли в аккаунт.")
    return redirect("assistant:cabinet")


class CabinetView(LoginRequiredMixin, TemplateView):
    template_name = "assistant/cabinet.html"

    login_url = reverse_lazy("assistant:login")

    def get_context_data(self, **kwargs):
        from assistant.models import ChatThread

        ctx = super().get_context_data(**kwargs)
        ctx["nav_section"] = "cabinet"
        ctx["saved_thread_count"] = ChatThread.objects.filter(user=self.request.user).count()

        from assistant.gigachat_plan_prefs import (
            enrich_plans_with_balance,
            gigachat_client_kw_for_request,
            plan_options_ordered,
        )
        from gigachat_advisor import gigachat_api_balance_entries

        gkw = gigachat_client_kw_for_request(self.request)
        api_rows, api_err = gigachat_api_balance_entries(giga_kw=gkw)
        ctx["gigachat_plan_options"] = enrich_plans_with_balance(plan_options_ordered(), api_rows)
        ctx["gigachat_balance_error"] = api_err
        ctx["gigachat_effective_scope"] = gkw.get("scope", "")
        ctx["gigachat_effective_model"] = gkw.get("model", "")

        return ctx


class AuthLogoutView(DjangoLogoutView):
    next_page = reverse_lazy("assistant:afisha")
