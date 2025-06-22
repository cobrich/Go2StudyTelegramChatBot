# 🚀 Railway + Neon Deployment Guide

## 📋 Обзор

Это руководство поможет развернуть Go2Study Bot на Railway с базой данных Neon PostgreSQL.

**Преимущества Railway + Neon:**
- 🆓 **Бесплатный тариф**: $5 кредитов/месяц
- 🔗 **Автоматическая интеграция** с Neon
- ⚡ **Быстрый деплой** из GitHub
- 🔄 **Автоматические обновления**
- 📊 **Мониторинг** в реальном времени

## 🛠️ Подготовка

### 1. Создание Neon базы данных

1. **Перейдите на [neon.tech](https://neon.tech)**
2. **Создайте аккаунт** (можно через GitHub)
3. **Создайте новый проект**:
   - Название: `go2study-bot`
   - Регион: выберите ближайший к вашим пользователям
4. **Скопируйте connection string**:
   ```
   postgresql://username:password@ep-xxx-xxx-xxx.region.aws.neon.tech/database
   ```

### 2. Подготовка Telegram Bot

1. **Создайте бота через [@BotFather](https://t.me/BotFather)**:
   - `/newbot`
   - Название: `Go2Study Bot`
   - Username: `your_bot_username_bot`
2. **Скопируйте токен**: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 3. Получение Google Gemini API Key

1. **Перейдите на [Google AI Studio](https://aistudio.google.com/)**
2. **Создайте API ключ**
3. **Скопируйте ключ**: `AIzaSy...`

## 🚀 Деплой на Railway

### 1. Подготовка репозитория

1. **Убедитесь, что код в GitHub**:
   ```bash
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

2. **Проверьте наличие файлов**:
   - ✅ `Dockerfile`
   - ✅ `Procfile`
   - ✅ `requirements.txt`
   - ✅ `railway.json`
   - ✅ `main.py`

### 2. Создание проекта на Railway

1. **Перейдите на [railway.app](https://railway.app)**
2. **Войдите через GitHub**
3. **Нажмите "New Project"**
4. **Выберите "Deploy from GitHub repo"**
5. **Выберите ваш репозиторий** `go2study_bot`

### 3. Настройка переменных окружения

В Railway Dashboard → Variables добавьте:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Google Gemini AI
GEMINI_API_KEY1=AIzaSy...
GEMINI_MODEL=gemini-pro

# Database (Neon)
DATABASE_URL=postgresql://username:password@ep-xxx-xxx-xxx.region.aws.neon.tech/database
USE_POSTGRESQL=true

# Environment
PYTHONUNBUFFERED=1
```

### 4. Подключение Neon базы данных

1. **В Railway Dashboard** → "New Service" → "Database"
2. **Выберите "Neon"**
3. **Введите connection string** из Neon
4. **Railway автоматически создаст переменную `DATABASE_URL`**

### 5. Запуск деплоя

1. **Railway автоматически начнет деплой**
2. **Следите за логами** в реальном времени
3. **Дождитесь успешного завершения**

## 🔧 Инициализация базы данных

После успешного деплоя нужно инициализировать БД:

### Вариант 1: Через Railway CLI

```bash
# Установка Railway CLI
npm install -g @railway/cli

# Логин
railway login

# Подключение к проекту
railway link

# Запуск инициализации
railway run python src/init_database.py
railway run python src/init_superadmin.py
railway run python src/init_topics.py
```

### Вариант 2: Через Railway Dashboard

1. **Откройте Railway Dashboard**
2. **Перейдите в "Deployments"**
3. **Найдите последний деплой**
4. **Нажмите "View Logs"**
5. **В консоли выполните команды**:
   ```bash
   python src/init_database.py
   python src/init_superadmin.py
   python src/init_topics.py
   ```

## 👥 Создание суперадмина

После инициализации БД создайте суперадмина:

1. **Получите ваш Telegram user_id**:
   - Напишите боту `/myid`
   - Или используйте [@userinfobot](https://t.me/userinfobot)

2. **Запустите скрипт создания суперадмина**:
   ```bash
   railway run python src/init_superadmin.py
   ```

3. **Введите данные**:
   - Telegram user_id: `123456789`
   - Username: `your_username` (без @)
   - ФИО: `Ваше Имя Фамилия`

## 🧪 Тестирование

### 1. Проверка бота

1. **Найдите бота в Telegram**: `@your_bot_username_bot`
2. **Отправьте `/start`**
3. **Проверьте основные функции**:
   - ✅ Выбор темы
   - ✅ Прохождение теста
   - ✅ Админ-панель (`/admin`)

### 2. Проверка логов

В Railway Dashboard → "Deployments" → "View Logs":
- ✅ Нет ошибок подключения к БД
- ✅ Бот успешно запустился
- ✅ API ключи загружены

## 🔄 Автоматические обновления

Railway автоматически обновляет бота при push в GitHub:

1. **Внесите изменения в код**
2. **Запушьте в GitHub**:
   ```bash
   git add .
   git commit -m "Update bot functionality"
   git push origin main
   ```
3. **Railway автоматически перезапустит бота**

## 📊 Мониторинг

### Railway Dashboard
- **Deployments**: история деплоев
- **Logs**: логи в реальном времени
- **Metrics**: использование ресурсов
- **Variables**: управление переменными окружения

### Neon Dashboard
- **Database**: состояние БД
- **Queries**: активные запросы
- **Storage**: использование диска

## 💰 Стоимость

**Бесплатный тариф Railway:**
- $5 кредитов/месяц
- Достаточно для бота с ~1000 пользователей
- Автоматическое масштабирование

**Neon PostgreSQL:**
- Бесплатно до 3GB БД
- Достаточно для миллионов записей
- Автоматические бэкапы

## 🛠️ Устранение неполадок

### Проблема: Бот не запускается
```bash
# Проверьте логи
railway logs

# Проверьте переменные окружения
railway variables
```

### Проблема: Ошибки подключения к БД
```bash
# Проверьте DATABASE_URL
echo $DATABASE_URL

# Проверьте доступность Neon
ping ep-xxx-xxx-xxx.region.aws.neon.tech
```

### Проблема: API ключи не работают
```bash
# Проверьте переменные
railway variables

# Перезапустите сервис
railway service restart
```

## 🎉 Готово!

Ваш Go2Study Bot теперь работает на Railway с Neon PostgreSQL!

**Преимущества:**
- ✅ Высокая доступность
- ✅ Автоматические обновления
- ✅ Масштабируемость
- ✅ Бесплатный тариф
- ✅ Простота управления

**Следующие шаги:**
1. Добавьте пользователей в whitelist через админ-панель
2. Импортируйте вопросы из PDF файлов
3. Настройте мониторинг и уведомления
4. Расскажите о боте ученикам!

---

**🎯 Результат**: Полностью функциональный бот для изучения математики, работающий 24/7 на надежной платформе! 