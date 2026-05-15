"""Формы входа и регистрации с подтверждением почты."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError


class AuthLoginForm(AuthenticationForm):
    """Сообщение для неактивного аккаунта (до подтверждения почты)."""

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Подтвердите адрес электронной почты — перейдите по ссылке из письма.",
                code="inactive",
            )


class RegisterForm(UserCreationForm):
    """Регистрация с обязательной почтой (уникальной)."""

    email = forms.EmailField(
        label="Электронная почта",
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Укажите почту.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Этот адрес почты уже зарегистрирован.")
        return email

