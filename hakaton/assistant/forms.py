"""Формы входа и регистрации с подтверждением почты."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError


class AuthLoginForm(AuthenticationForm):
    """Электронная почта как логин (см. assistant.User.USERNAME_FIELD)."""

    username = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Аккаунт отключён. Обратитесь к администратору сайта.",
                code="inactive",
            )


class RegisterForm(UserCreationForm):
    """Уникальна только почта; отображаемое имя (username) может совпадать у разных аккаунтов."""

    username = forms.CharField(
        label="Имя или никнейм (может совпадать с другими)",
        max_length=150,
        required=False,
        strip=True,
        widget=forms.TextInput(attrs={"autocomplete": "nickname"}),
    )
    email = forms.EmailField(
        label="Электронная почта",
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        return (username or "").strip()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Укажите почту.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Этот адрес почты уже зарегистрирован.")
        return email
