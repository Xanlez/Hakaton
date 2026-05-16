# Документация проекта «Афиша Sirius + помощник»

Веб-приложение на Django с каталогом мероприятий и чатом на базе GigaChat. Данные афиши подтягиваются с API «Сириус» и хранятся в локальной SQLite (`afisha.db`). Отдельная база Django (`hakaton/db.sqlite3`) — пользователи, сохранённые чаты и заявки на регистрацию.

Печатные версии: **`docs/DOCUMENTATION.docx`**, **`docs/HOW_IT_WORKS.docx`** (собираются скриптом `scripts/build_docs_docx.py`).

## Требования

- Python 3.11+.
- Зависимости: `requirements.txt` — Django 6.x, `gigachat`, `python-dotenv`, `cryptography` (шифрование пароля в заявке на регистрацию).

## Установка

```bash
cd путь/к/Hakaton
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Файл **`.env`** в корне репозитория (рядом с `config.py`).

### GigaChat (обязательно для чата)

```env
GIGACHAT_CREDENTIALS=...
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_BUNDLE_FILE=
GIGACHAT_VERIFY_SSL_CERTS=true
```

### Логи Django

В каждой строке лога — идентификатор пользователя (`user_repr`). Ротация файла:

```env
DJANGO_LOG_LEVEL=INFO
DJANGO_LOG_FILE=logs/django.log
DJANGO_LOG_MAX_BYTES=5242880
DJANGO_LOG_BACKUP_COUNT=5
```

Путь относительно каталога `hakaton/` (`manage.py`). По умолчанию: `hakaton/logs/django.log`.

### Афиша

В `config.py`: `API_URL`, `DB_PATH`, `SYNC_INTERVAL_SEC`. По умолчанию БД — `afisha.db` в корне.

### Локальный доступ (опционально)

При обращении с loopback (127.0.0.1 и т.п.) можно включить упрощённый промпт и выбор модели в чате:

```env
ASSISTANT_LOCAL_LL_SIMPLE=true
ASSISTANT_LOCAL_RELAX_CHAT_LIMITS=true
ASSISTANT_LOCAL_GIGACHAT_BANNER=true
CHAT_LOCAL_MESSAGES_PER_THREAD_MAX=240
CHAT_LOCAL_THREADS_MAX=60
```

## Запуск веб-приложения

```bash
cd hakaton
python manage.py migrate
python manage.py runserver
```

Браузер: обычно `http://127.0.0.1:8000/`.

### Почта и регистрация

1. Пользователь заполняет форму на `/accounts/register/`.
2. На почту уходит ссылка вида `/accounts/confirm/<токен>/`. В БД хранится только **отпечаток** токена (HMAC), не сама ссылка.
3. При повторной регистрации на ту же почту или при **«Выслать письмо снова»** (`POST /accounts/register/resend/`) выдается **новый** токен — старые ссылки из писем **недействительны** (ротация).
4. Повторная отправка письма — не чаще одного раза в ~60 секунд на адрес.
5. После перехода по ссылке создаётся активный пользователь, заявка удаляется.

В разработке письма часто только в консоли (`console.EmailBackend`). Для SMTP — переменные в `hakaton/hakaton/settings.py`: `DJANGO_EMAIL_*` или `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` в `.env`.

Срок жизни ссылки подтверждения: **72 часа** (см. `PENDING_LINK_MAX_AGE` в `auth_views.py`).

## Обновление афиши (CLI)

```bash
python main.py --once
python main.py
python main.py --interval 1800
python main.py --db путь\к\afisha.db --once
```

Если `afisha.db` пуста, сайт при первом обращении к афише или чату вызовет `sync_afisha.ensure_db`.

## Консольный чат

```bash
python chat.py
python chat.py "что посмотреть на выходных?"
python chat.py --sync "вечерние события"
```

## Файлы данных

| Файл | Назначение |
|------|------------|
| `afisha.db` | События афиши (CLI + Django). |
| `hakaton/db.sqlite3` | Пользователи, потоки и сообщения чата. |
| `hakaton/logs/django.log` | Журнал приложения (ротация по размеру). |

Не коммитьте `.env` и секреты.

## URL приложения `assistant`

| URL | Описание |
|-----|----------|
| `/` | Афиша |
| `/event/<id>/` | Карточка мероприятия |
| `/chat/` | Чат-помощник |
| `/chat/?event=<id>` | Новый чат по событию |
| `/api/chat/` | API чата (POST, поток NDJSON) |
| `/cabinet/` | Личный кабинет |
| `/accounts/register/` | Регистрация |
| `/accounts/register/done/` | «Письмо отправлено» + повторная отправка |
| `/accounts/register/resend/` | POST: повторное письмо (ротация токена) |
| `/accounts/confirm/<token>/` | Подтверждение регистрации |
| `/accounts/login/`, `/logout/` | Вход / выход |
| `/admin/` | Админка Django |

### API чата (кратко)

`POST /api/chat/` с JSON: `message`, `chat_id`. Ответ — поток **`application/x-ndjson`**: строки `delta` (фрагмент текста), `done` (итог + `reply_html`) или `error` (`message`, `code`). Подробности — в **`HOW_IT_WORKS.md`** и **`docs/HOW_IT_WORKS.docx`**.

## Сборка DOCX

```bash
pip install python-docx
python scripts/build_docs_docx.py
```

Результат: каталог **`docs/`**.

## См. также

- **`HOW_IT_WORKS.md`** / **`docs/HOW_IT_WORKS.docx`** — архитектура, потоки, модули, ошибки GigaChat.
