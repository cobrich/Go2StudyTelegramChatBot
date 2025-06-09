# Go2Study Bot 🤖📚

Telegram-бот для изучения математики с поддержкой ИИ, тестирования и административными функциями.

## ⚡ Быстрая установка

### Метод 1: Автоматическая установка (Рекомендуется)
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd go2study_bot

# Запустите автоматическую установку
python setup.py
```

### Метод 2: Ручная установка
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd go2study_bot

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .env.template .env
# Отредактируйте .env файл и добавьте ваши API ключи
```

## 🔧 Совместимость версий

### Python Telegram Bot версии

**✅ Поддерживаемые версии:**
- `python-telegram-bot 20.x` (Рекомендуется)
- `python-telegram-bot 21.x+` (Экспериментально)

**🚀 Запуск для разных версий:**

#### Версия 20.x (Стабильная)
```bash
cd src
python bot.py
```

#### Версия 21.x+ (Универсальная)
```bash
cd src
python bot_universal.py
```

#### Автоопределение версии
```bash
cd src
python bot_compat.py
```

## 📋 Требования

### Системные требования
- Python 3.8+
- pip
- Интернет соединение

### API ключи
- **Telegram Bot Token** - получить у [@BotFather](https://t.me/BotFather)
- **Google Gemini API Key** - получить в [Google AI Studio](https://makersuite.google.com/)

## ⚙️ Настройка

### 1. Настройка .env файла
```env
# Telegram Bot Token (обязательно)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Google Gemini API Key (обязательно)  
GEMINI_API_KEY=your_gemini_api_key_here

# Gemini Model (опционально)
GEMINI_MODEL=gemini-pro
```

### 2. Настройка супер-администратора
```bash
# Получите ваш user_id
python -c "
import sys; sys.path.append('src')
from services.database import Database
db = Database()
# Замените на ваши данные
user_id = 1234567890
username = 'your_username'
full_name = 'Your Full Name'
db.add_admin(user_id, username, full_name, is_super=True)
print('Super admin added!')
"
```

## 🚀 Запуск

### Обычный запуск
```bash
cd src && python bot.py
```

### Фоновый запуск (Linux/Mac)
```bash
cd src && nohup python bot.py > bot.log 2>&1 &
```

### Проверка статуса
```bash
ps aux | grep bot.py
```

## 🔨 Решение проблем

### Ошибка инициализации бота
```bash
# Если получаете RuntimeError: ExtBot is not properly initialized
pip install "python-telegram-bot==20.8"
cd src && python bot.py
```

### Конфликт версий
```bash
# Автоматическое решение конфликтов
python setup.py

# Или ручное решение
pip uninstall python-telegram-bot
pip install "python-telegram-bot>=20.0,<21.0"
```

### Проблемы с Google AI
```bash
# Попробуйте разные версии
pip install "google-generativeai==0.3.2"
# или
pip install "google-generativeai<1.0.0"
```

## 📊 Функции

### Для учеников
- 📚 Интерактивные тесты по математике
- 🤖 ИИ-генерация вопросов
- 📈 Отслеживание прогресса
- 🔄 Повторение ошибок
- 🌍 Поддержка русского и казахского языков

### Для администраторов
- 👥 Управление пользователями (whitelist)
- 📄 Загрузка вопросов через PDF
- 📊 Статистика и аналитика
- 🎯 Управление темами
- 👤 Управление администраторами

## 🏗️ Архитектура

```
go2study_bot/
├── src/
│   ├── bot.py              # Основной бот (v20.x)
│   ├── bot_universal.py    # Универсальная версия
│   ├── bot_compat.py       # Модуль совместимости
│   ├── config/             # Конфигурация
│   ├── handlers/           # Обработчики команд
│   ├── services/           # Бизнес-логика
│   └── utils/              # Утилиты
├── requirements.txt        # Зависимости
├── setup.py               # Автоматическая установка
└── README.md              # Документация
```

## 🔐 Безопасность

### Whitelist система
- Только разрешенные пользователи могут использовать бота
- Админы добавляют учеников через панель управления
- Аудит всех действий

### Роли пользователей
- **Супер-админ**: Полный доступ ко всем функциям
- **Админ**: Управление студентами и контентом
- **Студент**: Доступ к тестам и обучению

## 📝 Поддержка

### Логи
```bash
# Просмотр логов в реальном времени
tail -f bot.log

# Просмотр последних ошибок
grep ERROR bot.log | tail -10
```

### Отладка
```bash
# Запуск с подробным логированием
cd src && python -u bot.py
```

### База данных
```bash
# Резервная копия
cp math_bot.db math_bot.db.backup

# Просмотр базы данных
sqlite3 math_bot.db ".tables"
```

## 🤝 Содействие

1. Fork репозиторий
2. Создайте feature branch
3. Внесите изменения
4. Обновите DOCS.md
5. Создайте Pull Request

## 📄 Лицензия

MIT License - смотрите LICENSE файл для деталей.

---

**🎓 Удачи в изучении математики! 💪** 