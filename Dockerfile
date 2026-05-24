# Music Playlist Bot — Dockerfile

FROM python:3.11-slim

# Метаданные
LABEL maintainer="Music Playlist Bot"
LABEL version="1.0"

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY bot.py .
COPY database.py .
COPY keyboards.py .
COPY config.py .

# Создаём папку для БД
RUN mkdir -p /app/data

# Точка монтирования данных
VOLUME ["/app/data"]

# Запуск бота
CMD ["python", "-u", "bot.py"] 