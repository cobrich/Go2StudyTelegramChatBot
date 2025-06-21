FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY requirements.txt .
COPY setup.py .
COPY src/ ./src/
COPY main.py .
COPY .env.template .

# Установка Python зависимостей
RUN python setup.py

# Создание пользователя для безопасности
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Создание директории для данных
RUN mkdir -p /app/data

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Порт (если понадобится веб-интерфейс)
EXPOSE 8000

# Команда запуска
CMD ["python", "main.py"] 