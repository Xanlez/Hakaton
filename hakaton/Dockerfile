# Базовый образ с Python
FROM python:3.12-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем зависимости (они на уровень выше в твоем репозитории)
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код текущей папки в контейнер
COPY . .

# Открываем порт для Django
EXPOSE 8000

# Команда запуска
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]