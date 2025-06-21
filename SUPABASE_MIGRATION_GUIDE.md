# 🚀 Руководство по миграции на Supabase

## Обзор изменений

Проект **Go2Study Bot** был полностью переработан для работы исключительно с **Supabase PostgreSQL**. Поддержка SQLite полностью удалена для упрощения архитектуры и повышения производительности.

## ⚠️ Важные изменения

### Что удалено:
- ❌ Поддержка SQLite
- ❌ Дублирующий код для двух типов БД
- ❌ Прямые SQLite подключения в handlers
- ❌ Sync методы для SQLite

### Что добавлено:
- ✅ Чистая архитектура только для Supabase
- ✅ Упрощенный connection manager
- ✅ Скрипт миграции данных
- ✅ Улучшенная производительность

## 📋 Пошаговая миграция

### Шаг 1: Подготовка Supabase

1. **Создайте проект в Supabase:**
   - Перейдите на [supabase.com](https://supabase.com)
   - Создайте новый проект
   - Получите connection string

2. **Настройте переменные окружения:**
   ```bash
   # Скопируйте пример конфигурации
   cp env.supabase.example .env
   
   # Отредактируйте .env файл:
   DATABASE_TYPE=supabase
   SUPABASE_DATABASE_URL=postgresql://postgres.your_project_id:your_password@aws-0-eu-north-1.pooler.supabase.com:6543/postgres
   TELEGRAM_BOT_TOKEN=your_bot_token
   OPENAI_API_KEY=your_openai_key
   ```

### Шаг 2: Инициализация Supabase

```bash
# Создайте таблицы в Supabase
python init_supabase.py
```

Этот скрипт:
- ✅ Создаст все необходимые таблицы
- ✅ Настроит индексы для производительности
- ✅ Инициализирует базовые темы
- ✅ Проверит подключение

### Шаг 3: Миграция данных (если есть SQLite база)

```bash
# Мигрируйте данные с SQLite на Supabase
python migrate_to_supabase.py
```

Скрипт перенесет:
- 👥 Администраторов
- 👤 Пользователей
- 📚 Темы и подтемы
- ❓ Вопросы
- 📊 Результаты тестов
- ❌ Ошибки пользователей

### Шаг 4: Очистка (опционально)

```bash
# Удалите SQLite импорты (уже выполнено)
python cleanup_sqlite_imports.py

# После проверки работы можете удалить:
rm math_bot.db
rm cleanup_sqlite_imports.py
rm migrate_to_supabase.py
```

## 🏗️ Новая архитектура

### Структура базы данных:

```
src/db/
├── __init__.py              # Экспорт основных компонентов
├── connection_manager.py    # Управление подключениями Supabase
├── base_repository.py       # Базовый класс репозиториев
├── models.py               # PostgreSQL схемы
├── database_facade.py      # Единый интерфейс БД
└── repositories/           # Модульные репозитории
    ├── user_repository.py
    ├── admin_repository.py
    ├── question_repository.py
    └── statistics_repository.py
```

### Использование в коде:

```python
# Старый способ (больше не работает):
import sqlite3
with sqlite3.connect(db_path) as conn:
    # ...

# Новый способ:
from src.db import get_database

db = get_database()
user_info = db.get_user_info(user_id)
```

## 🐛 Известные проблемы

### Файлы с остаточными SQLite подключениями:

Следующие файлы все еще содержат прямые SQLite подключения и требуют ручного исправления:

1. **src/handlers/callback_handlers.py** (2 места)
2. **src/handlers/admin/base.py** (1 место)
3. **src/handlers/admin/questions.py** (много мест)
4. **src/handlers/admin/stats.py** (2 места)
5. **src/handlers/admin/students.py** (4 места)
6. **src/services/random_test_service.py** (2 места)

### Как исправить:

Замените конструкции вида:
```python
with sqlite3.connect(self.db.db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    result = cursor.fetchall()
```

На:
```python
# Используйте методы database facade
result = self.db.fetch_all("SELECT ...", params)
```

## ✅ Проверка миграции

### 1. Проверьте подключение:
```bash
python -c "
from src.db import get_database
db = get_database()
print('✅ Подключение к Supabase работает!')
"
```

### 2. Проверьте данные:
```bash
python -c "
from src.db import get_database
db = get_database()
users = db.get_all_allowed_users()
print(f'✅ Найдено {len(users)} пользователей')
"
```

### 3. Запустите бота:
```bash
python main.py
```

## 🎯 Преимущества новой архитектуры

- **🚀 Производительность**: Нет переключения между типами БД
- **🧹 Чистота кода**: Убрано дублирование логики
- **🔒 Безопасность**: Централизованное управление подключениями
- **📈 Масштабируемость**: PostgreSQL лучше подходит для продакшена
- **🛠️ Поддержка**: Проще поддерживать один тип БД

## 🆘 Помощь

Если возникли проблемы:

1. **Проверьте переменные окружения** в `.env`
2. **Убедитесь, что Supabase проект активен**
3. **Проверьте connection string**
4. **Посмотрите логи ошибок**

### Контакты:
- GitHub Issues: [Создать issue](https://github.com/your-repo/issues)
- Документация: `DOCS.md`

---

**🎉 Поздравляем! Теперь ваш бот работает на современной Supabase архитектуре!** 