# Документация проекта «Афиша Sirius + помощник»

Веб-приложение на Django с каталогом мероприятий и чатом на базе GigaChat. Данные афиши подтягиваются с API «Сириус» и хранятся в локальной SQLite (`afisha.db`). Отдельная база Django (`hakaton/db.sqlite3`) используется для пользователей и сохранённых чатов.

## Требования

- Python 3.11+ (рекомендуется актуальный стабильный релиз).
- Зависимости из `requirements.txt`: Django 6.x, `gigachat`, `python-dotenv`.

## Установка

```bash
cd путь/к/Hakaton
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Создайте файл `.env` в **корне репозитория** (рядом с `config.py`). Минимально для чата и рекомендаций нужны учётные данные GigaChat:

```env
GIGACHAT_CREDENTIALS=...
```

Опционально:

```env
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_BUNDLE_FILE=
GIGACHAT_VERIFY_SSL_CERTS=true
```

Параметры загрузки афиши и путь к файлу БД афиши задаются в `config.py` (`API_URL`, `DB_PATH`, `SYNC_INTERVAL_SEC`). По умолчанию файл БД — `afisha.db` в корне проекта.

## Запуск веб-приложения (Django)

```bash
cd hakaton
python manage.py migrate
python manage.py runserver
```

Откройте в браузере адрес, который выведет `runserver` (обычно `http://127.0.0.1:8000/`).

### Почта и регистрация

Регистрация отправляет письмо с ссылкой активации. В режиме разработки по умолчанию письма выводятся в консоль сервера (`django.core.mail.backends.console.EmailBackend`). Для SMTP задайте переменные окружения (см. комментарии в `hakaton/hakaton/settings.py`):

- `DJANGO_EMAIL_BACKEND`
- `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, и при необходимости пользователь/пароль/TLS/SSL
- `DJANGO_DEFAULT_FROM_EMAIL`

## Обновление афиши в фоне (CLI)

Скрипт `main.py` периодически синхронизирует API → SQLite:

```bash
python main.py --once
```

Один раз загрузить данные и выйти.

```bash
python main.py
```

Цикл с интервалом по умолчанию (`SYNC_INTERVAL_SEC`, обычно 3600 секунд). Свой интервал:

```bash
python main.py --interval 1800
```

Другой файл БД:

```bash
python main.py --db путь\к\afisha.db --once
```

Если БД пуста, при первом обращении к афише или чату через сайт также выполняется синхронизация (см. `chat.ensure_db`).

## Консольный чат без браузера

```bash
python chat.py
```

Интерактивный режим. Одноразовый вопрос:

```bash
python chat.py "что посмотреть на выходных?"
```

Перед ответом принудительно обновить афишу:

```bash
python chat.py --sync "вечерние события"
```

## Где какие файлы данных

| Файл | Назначение |
|------|------------|
| `afisha.db` | События афиши (общая БД для CLI и Django). |
| `hakaton/db.sqlite3` | Пользователи Django, потоки чатов и сообщения для залогиненных. |

Не коммитьте продакшен-секреты и персональные `.env`; для деплоя используйте переменные окружения на сервере.

## Полезные URL (приложение `assistant`)

- `/` — список событий (афиша).
- `/event/<id>/` — карточка мероприятия.
- `/chat/` — чат-помощник.
- `/cabinet/` — личный кабинет (нужна авторизация).
- `/accounts/register/`, `/accounts/login/`, `/accounts/logout/` — регистрация и вход.
- `/admin/` — админка Django.

Подробнее о внутреннем устройстве см. файл `HOW_IT_WORKS.md`.
