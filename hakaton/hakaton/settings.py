"""Настройки Django-приложения hakaton."""

import logging
import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Родительский каталог репозитория: там же лежат chat.py, gigachat_advisor.py, afisha.db
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-30!__%on3fzapsk=t0ntkfj)%pmo@)_-corg9=9b@y$@=_ohea'

# Регистрация по ссылке: отдельный «перец» для HMAC токена (опционально; иначе используется SECRET_KEY).
REGISTRATION_TOKEN_PEPPER = os.environ.get("REGISTRATION_TOKEN_PEPPER", "").strip() or None
# Ключ Fernet для pending password (значение от Fernet.generate_key()); иначе ключ выводится из SECRET_KEY.
REGISTRATION_PENDING_PASSWORD_FERNET_KEY = os.environ.get(
    "REGISTRATION_PENDING_PASSWORD_FERNET_KEY", ""
).strip() or None

# Три тарифные линии модели в ЛК; scope всегда из config.py / .env.
GIGACHAT_PLAN_DEFAULT_SLUG = (os.environ.get("GIGACHAT_PLAN_DEFAULT_SLUG") or "gigachat").strip()
GIGACHAT_PLAN_OPTIONS = (
    {"slug": "gigachat", "label": "GigaChat", "scope": "", "model": "GigaChat"},
    {"slug": "gigachat-pro", "label": "GigaChat-Pro", "scope": "", "model": "GigaChat-Pro"},
    {"slug": "gigachat-max", "label": "GigaChat-Max", "scope": "", "model": "GigaChat-Max"},
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

_raw_hosts = (os.environ.get("DJANGO_ALLOWED_HOSTS") or os.environ.get("ALLOWED_HOSTS") or "*").strip()
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()] or ["*"]

# Django 4+: при HTTPS POST проверяется Origin; IP/домен VPS нужно явно доверить.
# Пример в .env: DJANGO_CSRF_TRUSTED_ORIGINS=https://217.144.189.67,https://my.domain.ru
_raw_csrf = (os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS") or os.environ.get("CSRF_TRUSTED_ORIGINS") or "").strip()
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _raw_csrf.split(",") if o.strip()]

# За nginx/caddy с TLS-терминацией (раскомментируйте при необходимости):
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Запросы с loopback (127.0.0.1 / ::1): GigaChat с общим промптом («как нейросеть») и более длинный чат.
# Отключение: ASSISTANT_LOCAL_LL_SIMPLE=0 или ASSISTANT_LOCAL_RELAX_CHAT_LIMITS=0 в .env
ASSISTANT_LOCAL_LL_SIMPLE = os.environ.get("ASSISTANT_LOCAL_LL_SIMPLE", "true").lower() in ("1", "true", "yes")
ASSISTANT_LOCAL_LL_SIMPLE_REQUIRE_DEBUG = (
    os.environ.get("ASSISTANT_LOCAL_LL_REQUIRE_DEBUG", "").lower() in ("1", "true", "yes")
)
ASSISTANT_LOCAL_RELAX_CHAT_LIMITS = (
    os.environ.get("ASSISTANT_LOCAL_RELAX_CHAT_LIMITS", "true").lower() in ("1", "true", "yes")
)
CHAT_LOCAL_MESSAGES_PER_THREAD_MAX = int(os.environ.get("CHAT_LOCAL_MESSAGES_PER_THREAD_MAX", "240"))
CHAT_LOCAL_THREADS_MAX = int(os.environ.get("CHAT_LOCAL_THREADS_MAX", "60"))
# Выбор модели в чате (между полем и «Отправить») только при локальном (loopback) доступе (ASSISTANT_LOCAL_GIGACHAT_BANNER=0 — скрыть)
ASSISTANT_LOCAL_GIGACHAT_BANNER = (
    os.environ.get("ASSISTANT_LOCAL_GIGACHAT_BANNER", "true").lower() in ("1", "true", "yes")
)


# Application definition

AUTH_USER_MODEL = 'assistant.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'assistant',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'assistant.logging_user.AttachUserLoggingContextMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hakaton.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'assistant.context_processors.local_gigachat_banner',
            ],
        },
    },
]

WSGI_APPLICATION = 'hakaton.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/cabinet/"
LOGOUT_REDIRECT_URL = "/"

# Почта: DJANGO_EMAIL_* или те же имена, что в fbe-cloud (SMTP_HOST, SMTP_USER, …)
_smtp_host = (os.environ.get("DJANGO_EMAIL_HOST") or os.environ.get("SMTP_HOST", "")).strip()
_smtp_user = (os.environ.get("DJANGO_EMAIL_HOST_USER") or os.environ.get("SMTP_USER", "")).strip()
_smtp_password = (os.environ.get("DJANGO_EMAIL_HOST_PASSWORD") or os.environ.get("SMTP_PASSWORD", "")).strip()
_smtp_port_raw = os.environ.get("DJANGO_EMAIL_PORT") or os.environ.get("SMTP_PORT", "587")
_smtp_from = (
    os.environ.get("DJANGO_DEFAULT_FROM_EMAIL")
    or os.environ.get("SMTP_FROM", "")
    or _smtp_user
    or "Sirius Afisha <noreply@localhost>"
)

EMAIL_HOST = _smtp_host
EMAIL_PORT = int(_smtp_port_raw)
EMAIL_HOST_USER = _smtp_user
EMAIL_HOST_PASSWORD = _smtp_password
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
EMAIL_USE_SSL = os.environ.get("DJANGO_EMAIL_USE_SSL", "").lower() in ("1", "true", "yes")
EMAIL_TIMEOUT = int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "30"))

if EMAIL_HOST and EMAIL_HOST_USER:
    EMAIL_BACKEND = os.environ.get(
        "DJANGO_EMAIL_BACKEND",
        "django.core.mail.backends.smtp.EmailBackend",
    )
    DEFAULT_FROM_EMAIL = _smtp_from
else:
    EMAIL_BACKEND = os.environ.get(
        "DJANGO_EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend",
    )
    DEFAULT_FROM_EMAIL = (
        os.environ.get("DJANGO_DEFAULT_FROM_EMAIL")
        or _smtp_from
    )

_django_log_level_name = (
    os.environ.get("DJANGO_LOG_LEVEL") or os.environ.get("LOG_LEVEL") or "INFO"
).upper()
DJANGO_ROOT_LOG_LEVEL = getattr(logging, _django_log_level_name, logging.INFO)

_raw_log_file = os.environ.get("DJANGO_LOG_FILE", "").strip()
DJANGO_LOG_PATH = Path(_raw_log_file) if _raw_log_file else (BASE_DIR / "logs" / "django.log")
if not DJANGO_LOG_PATH.is_absolute():
    DJANGO_LOG_PATH = BASE_DIR / DJANGO_LOG_PATH
DJANGO_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
DJANGO_LOG_MAX_BYTES = int(os.environ.get("DJANGO_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
DJANGO_LOG_BACKUP_COUNT = int(os.environ.get("DJANGO_LOG_BACKUP_COUNT", "5"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "user_context": {
            "()": "assistant.logging_user.UserLoggingFilter",
        },
    },
    "formatters": {
        "with_user": {
            "format": (
                "{levelname} {asctime} | {user_repr} | {name} | {message}"
            ),
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["user_context"],
            "formatter": "with_user",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(DJANGO_LOG_PATH),
            "maxBytes": DJANGO_LOG_MAX_BYTES,
            "backupCount": DJANGO_LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "filters": ["user_context"],
            "formatter": "with_user",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": DJANGO_ROOT_LOG_LEVEL,
    },
}
