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
cd src
python3 init_superadmin.py

# 7. Запуск бота
python3 bot.py
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
WorkingDirectory=/home/ubuntu/go2study_bot/src
ExecStart=/home/ubuntu/go2study_bot/venv/bin/python bot.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/ubuntu/go2study_bot/src

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
COPY .env.template .

# Установка Python зависимостей
RUN python setup.py

# Создание пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Запуск
WORKDIR /app/src
CMD ["python", "bot.py"]
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
      - PYTHONPATH=/app/src
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
echo "worker: cd src && python bot.py" > Procfile

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
cd src
python3 init_superadmin.py
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
ps aux | grep bot.py
```

### Просмотр логов:
```bash
# Системный сервис
sudo journalctl -u go2study-bot -f

# Docker
docker-compose logs -f

# Файловые логи
tail -f bot.log
```

### Обновление бота:
```bash
# Остановка
sudo systemctl stop go2study-bot

# Обновление кода
git pull origin main

# Установка новых зависимостей (если есть)
python3 setup.py

# Запуск
sudo systemctl start go2study-bot
```

### Резервное копирование:
```bash
# Создание бэкапа базы данных
cp math_bot.db math_bot_backup_$(date +%Y%m%d).db

# Автоматический бэкап (добавить в crontab)
0 2 * * * cp /path/to/go2study_bot/math_bot.db /path/to/backups/math_bot_$(date +\%Y\%m\%d).db
```

---

## 🔐 Безопасность

### Настройка файрвола:
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### SSL сертификат (если нужен веб-интерфейс):
```bash
# Certbot
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

### Обновления безопасности:
```bash
# Автоматические обновления
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

---

## 💰 Стоимость хостинга

### VPS провайдеры:
- **DigitalOcean**: $5-10/месяц
- **Vultr**: $3.50-6/месяц  
- **Linode**: $5-10/месяц
- **Hetzner**: €3-5/месяц

### Облачные платформы:
- **Heroku**: $7/месяц (Hobby)
- **Railway**: $5/месяц
- **DigitalOcean Apps**: $5/месяц

---

## 📞 Поддержка

### Если что-то не работает:
1. Проверьте логи: `sudo journalctl -u go2study-bot -f`
2. Проверьте статус: `sudo systemctl status go2study-bot`
3. Перезапустите: `sudo systemctl restart go2study-bot`
4. Проверьте .env файл с токенами

### Частые проблемы:
- **Бот не отвечает**: Проверьте TELEGRAM_BOT_TOKEN
- **ИИ не работает**: Проверьте GEMINI_API_KEY
- **База данных**: Проверьте права доступа к файлу math_bot.db

---

## ✅ Чек-лист готовности

- [ ] Сервер настроен и обновлен
- [ ] Python 3.8+ установлен
- [ ] Проект склонирован и настроен
- [ ] .env файл заполнен корректными токенами
- [ ] Супер-админ инициализирован
- [ ] Бот запущен и отвечает
- [ ] Системный сервис настроен (опционально)
- [ ] Мониторинг настроен
- [ ] Резервное копирование настроено

**Ваш бот готов к работе! 🎉** 