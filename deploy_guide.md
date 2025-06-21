# 🚀 Руководство по деплою Go2Study Bot

## 📋 Варианты деплоя

### 1. VPS/Сервер (Рекомендуется) 💻

#### Требования к серверу:
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: минимум 1GB, рекомендуется 2GB
- **CPU**: 1 vCPU (достаточно)
- **Диск**: 10GB свободного места
- **Интернет**: стабильное соединение

#### Пошаговая установка:

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Python 3.8+
sudo apt install python3 python3-pip python3-venv git -y

# 3. Клонирование проекта
git clone <your-repository-url> go2study_bot
cd go2study_bot

# 4. Автоматическая установка
python3 setup.py

# 5. Настройка .env
cp .env.template .env
nano .env  # Заполните TELEGRAM_BOT_TOKEN и GEMINI_API_KEY

# 6. Инициализация супер-админа
python3 src/init_superadmin.py

# 7. Запуск бота
python3 main.py
```

#### Настройка как системный сервис:

```bash
# Создание systemd сервиса
sudo nano /etc/systemd/system/go2study-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=Go2Study Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/go2study_bot
ExecStart=/home/ubuntu/go2study_bot/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/ubuntu/go2study_bot

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable go2study-bot
sudo systemctl start go2study-bot

# Проверка статуса
sudo systemctl status go2study-bot

# Просмотр логов
sudo journalctl -u go2study-bot -f
```

---

### 2. Docker (Для продвинутых) 🐳

#### Создание Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов
COPY requirements.txt .
COPY setup.py .
COPY src/ ./src/
COPY main.py .
COPY .env.template .

# Установка Python зависимостей
RUN python setup.py

# Создание пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Запуск
CMD ["python", "main.py"]
```

#### Docker Compose:

```yaml
version: '3.8'

services:
  go2study-bot:
    build: .
    container_name: go2study-bot
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - PYTHONPATH=/app
```

```bash
# Запуск через Docker
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

---

### 3. Облачные платформы ☁️

#### Heroku:
```bash
# Создание Procfile
echo "worker: python main.py" > Procfile

# Деплой
heroku create your-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set GEMINI_API_KEY=your_key
git push heroku main
```

#### Railway:
1. Подключите GitHub репозиторий
2. Добавьте переменные окружения
3. Автоматический деплой

#### DigitalOcean App Platform:
1. Создайте новое приложение
2. Подключите репозиторий
3. Настройте переменные окружения

---

## 🔧 Настройка после деплоя

### 1. Инициализация супер-админа:
```bash
python3 src/init_superadmin.py
# Введите ваш Telegram user_id, username и ФИО
```

### 2. Добавление учеников:
1. Запустите бота: `/start`
2. Войдите в админ-панель: `/admin`
3. Добавьте учеников через "Управление учениками"

### 3. Загрузка вопросов:
1. Админ-панель → "Управление темами"
2. Добавьте нужные темы
3. Загрузите PDF файлы с вопросами

---

## 📊 Мониторинг и обслуживание

### Проверка статуса:
```bash
# Системный сервис
sudo systemctl status go2study-bot

# Docker
docker-compose ps

# Процессы
ps aux | grep main.py
```

### Логи:
```bash
# Системный сервис
sudo journalctl -u go2study-bot -f

# Docker
docker-compose logs -f

# Прямой запуск
tail -f nohup.out
```

### Перезапуск:
```bash
# Системный сервис
sudo systemctl restart go2study-bot

# Docker
docker-compose restart

# Прямой запуск
pkill -f main.py
python3 main.py
```

---

## 🚨 Решение проблем

### Ошибки запуска:
```bash
# Проверка зависимостей
python3 -m pip install -r requirements.txt

# Проверка .env файла
cat .env

# Проверка структуры проекта
ls -la
```

### Проблемы с базой данных:
```bash
# Создание резервной копии
cp math_bot.db math_bot.db.backup

# Пересоздание БД
rm math_bot.db
python3 src/services/database.py
```

### Проблемы с правами:
```bash
# Исправление прав доступа
chmod +x main.py
chown -R $USER:$USER .
```

---

## 📋 Чеклист деплоя

### Перед деплоем:
- [ ] API ключи получены и добавлены в .env
- [ ] Сервер соответствует требованиям
- [ ] Код протестирован локально

### После деплоя:
- [ ] Бот отвечает на команду /start
- [ ] Супер-админ создан и имеет доступ
- [ ] Системный сервис настроен (для VPS)
- [ ] Мониторинг настроен
- [ ] Резервное копирование настроено

### Безопасность:
- [ ] .env файл не попадает в git
- [ ] Права доступа к файлам ограничены
- [ ] Firewall настроен (если нужно)
- [ ] SSL сертификат установлен (для веб-интерфейса)

---

## 💰 Стоимость хостинга

### VPS провайдеры (месяц):
- **Vultr**: от $3.50 (1GB RAM, 1 vCPU)
- **DigitalOcean**: от $4 (1GB RAM, 1 vCPU)  
- **Hetzner**: от €3.29 (1GB RAM, 1 vCPU)
- **Contabo**: от €3.99 (4GB RAM, 2 vCPU)

### Cloud платформы (месяц):
- **Heroku**: $7 (Hobby tier)
- **Railway**: $5 (Pro plan)
- **Render**: $7 (Starter)
- **DigitalOcean Apps**: $5 (Basic)

### Рекомендации:
- **Для начала**: Vultr или DigitalOcean VPS
- **Для простоты**: Railway или Heroku
- **Для экономии**: Hetzner или Contabo
- **Для масштабирования**: DigitalOcean Apps

---

*Руководство обновлено: 2025-01-19* 