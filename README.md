# Go2Study Bot

**Telegram-бот для подготовки к экзаменам НИШ (5–7 классы)** с адаптивным тестированием, генерацией вопросов через Google Gemini и полноценной админ-панелью.

> Проект развёрнут в production. Исходный код приватный — этот README описывает архитектуру, функционал и технические решения для портфолио.

---

## Демонстрация

<!-- Замените ссылку на запись экрана или GIF -->
<!-- ![Демонстрация работы бота](docs/demo.gif) -->

| Сценарий | Описание |
|----------|----------|
| Выбор темы | Иерархическое меню: раздел → подтема → тест из 10 вопросов |
| Ответ на вопрос | Мгновенная обратная связь + развёрнутое объяснение |
| Пересдача | Повтор ошибок + новые AI-вопросы по слабым местам |
| Админ-панель | Управление учениками, темами, вопросами, импорт из PDF |

---

## Ключевые возможности

### Для учеников

- **Адаптивные тесты** — приоритет вопросов, на которых ученик ошибался ранее
- **Гибридный банк вопросов** — curated-вопросы из PostgreSQL + свежие задачи от Gemini AI
- **Режим пересдачи** — повторение ошибок с догенерацией похожих AI-вопросов
- **Рандомный тест** — сбалансированная выборка вопросов из разных тем
- **Подробная аналитика** — история тестов, прогресс по темам
- **Двуязычный интерфейс** — русский и казахский (отдельные иерархии тем)
- **Чистый UX** — inline-клавиатуры, управляемые сообщения без «мусора» в чате

### Для администраторов

- **Whitelist-доступ** — только одобренные ученики могут проходить тесты
- **CRUD учеников** — добавление по Telegram ID, редактирование ФИО, класса, языка, статуса
- **Управление учебной программой** — разделы и подтемы на двух языках
- **Банк вопросов** — ручное добавление, редактирование, поиск, удаление
- **Импорт из PDF** — парсинг вопросов с извлечением изображений (PyMuPDF)
- **AI-объяснения** — автогенерация пояснений к существующим вопросам
- **Статистика** — системная аналитика и история активности учеников
- **Управление админами** — роли суперадмина и обычного администратора

---

## Учебная программа

5 разделов, **23 подтемы** на каждом языке (русский / казахский):

| Раздел | Подтемы |
|--------|---------|
| Числа и арифметика | Дроби, сравнение чисел, проценты, пропорции, порядок действий, модуль, неравенства |
| Алгебраические выражения | Упрощение, выражения, скобки, линейные уравнения, системы уравнений |
| Геометрия | Площадь и периметр, углы, масштабы, круг и окружность |
| Анализ данных и статистика | Среднее арифметическое, последовательности, текстовые задачи, функции |
| Логико-математическое мышление | Закономерности, логические задачи, сравнение выражений |

---

## Архитектура

```mermaid
flowchart TB
    subgraph Client
        TG[Telegram Client]
    end

    subgraph App["Go2Study Bot (Docker / Railway)"]
        MAIN[main.py]
        FLASK[Flask Health Check :8000]
        CMD[CommandHandlers]
        CB[CallbackHandlers]
        ADM[AdminHandlers]
        QS[QuestionService]
        AI[ImprovedAIService]
        PDF[PDFProcessor]
        RTS[RandomTestService]
        MM[MessageManager]
    end

    subgraph External
        GEMINI[Google Gemini API]
        PG[(PostgreSQL / Neon)]
    end

    TG <-->|Bot API| MAIN
    MAIN --> FLASK
    MAIN --> CMD & CB & ADM
    CMD & CB & ADM --> QS & RTS & PDF & MM
    QS --> AI
    PDF --> AI
    AI <-->|REST| GEMINI
    CMD & CB & ADM & QS & RTS & MM --> FACADE[SyncDatabaseFacade]
    FACADE --> REPOS[Repositories]
    REPOS <-->|SQLAlchemy + psycopg2| PG
```

### Слои приложения

```
go2study_bot/
├── main.py                          # Точка входа: Telegram polling + Flask health check
├── Dockerfile                       # Production-образ (Python 3.9-slim)
├── railway.json                     # Конфигурация деплоя на Railway
├── requirements.txt
├── tests/
│   └── test_ai_service_improved.py
└── src/
    ├── init_app.py                  # Автоинициализация БД при первом запуске
    ├── init_database.py             # Создание схемы (SQLAlchemy)
    ├── init_topics.py               # Seed: 5 разделов × 23 подтемы × 2 языка
    ├── init_superadmin.py           # Создание суперадмина
    ├── config/
    │   ├── constants.py             # RU: темы, меню, HELP_TEXT
    │   ├── constants_kk.py          # KK: темы + маппинг переводов
    │   └── messages_kk.py           # Казахские UI-строки
    ├── handlers/
    │   ├── command_handlers.py      # /start, /stop, /reset, onboarding
    │   ├── callback_handlers.py     # Тесты, ответы, навигация
    │   └── admin/                   # Админ-панель (students, topics, questions, stats)
    ├── services/
    │   ├── question_service.py      # Адаптивная генерация тестов (ядро)
    │   ├── ai_service_improved.py   # Gemini: промпты, парсинг, retry
    │   ├── pdf_processor.py         # Импорт вопросов из PDF
    │   └── random_test_service.py   # Кросс-тематические рандом-тесты
    ├── db/
    │   ├── models.py                # SQLAlchemy ORM-модели
    │   ├── sync_database_facade.py  # Единый API доступа к данным + кэш
    │   └── repositories/            # Репозитории по доменам
    └── utils/
        ├── keyboards.py             # Inline/reply-клавиатуры
        ├── message_manager.py       # Дедупликация UI-сообщений
        └── translations.py          # RU ↔ KK
```

### Поток прохождения теста

1. Ученик выбирает подтему через inline-клавиатуру
2. `QuestionService.get_or_generate_tasks()` собирает 10 вопросов по адаптивному алгоритму
3. Ответы обрабатываются в `CallbackHandlers`; ошибки сохраняются в `user_errors`
4. Результаты записываются в `user_test_results` и `user_progress`
5. При пересдаче (`retake`) — приоритет прежних ошибок + AI-догенерация

### Адаптивный алгоритм генерации теста

**Обычный режим** (10 вопросов):
1. Вопросы из `user_errors` (слабые места ученика)
2. Вопросы из банка PostgreSQL (до 8 шт.)
3. Минимум 2 свежих AI-вопроса от Gemini

**Режим пересдачи**:
1. Все доступные ошибки по теме
2. Недостающее количество — AI-вопросы с контекстом «пересдача»

AI-вопросы проходят строгую валидацию (длина, соответствие теме, отсутствие мета-текста), дедупликацию через `pg_trgm` (порог similarity > 0.85) и сохраняются в БД для повторного использования.

---

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.9 |
| Bot framework | python-telegram-bot 20.8 (async polling) |
| AI | Google Gemini (`google-generativeai`) |
| База данных | PostgreSQL (Neon / Supabase) |
| ORM | SQLAlchemy 2.0 |
| DB driver | psycopg2-binary, asyncpg |
| PDF | PyPDF2, PyMuPDF (fitz), Pillow |
| Health check | Flask 3.1.1 |
| Конфигурация | python-dotenv |
| Деплой | Docker + Railway |
| Тесты | unittest + mocks |

---

## Схема базы данных

| Таблица | Назначение |
|---------|------------|
| `admins` | Администраторы (user_id, роль суперадмина) |
| `allowed_users` | Whitelist учеников (ФИО, класс, язык, доступ) |
| `main_topics` | Основные разделы (RU/KK) |
| `subtopics` | Подтемы, привязанные к разделам |
| `questions` | Вопросы с вариантами ответов и объяснениями (`source`: manual / ai / pdf) |
| `user_errors` | Ошибки учеников (для адаптивного обучения) |
| `user_progress` | Прогресс по темам (correct / total) |
| `user_test_results` | История результатов тестов |
| `managed_messages` | ID UI-сообщений для дедупликации в чате |

---

## Команды и интерфейс

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация (ФИО, класс 5–7), проверка whitelist, главное меню |
| `/stop` | Очистка сессии и данных активности |
| `/reset` | Сброс «застрявшего» состояния теста |
| `/myid` | Показать Telegram user ID (для добавления в whitelist) |
| `/language` | Выбор языка интерфейса (RU / KK) |
| `/admin` | Админ-панель (только для администраторов) |
| `/clear_cache <user_id>` | Сброс кэша доступа (только для админов) |

Справка доступна через кнопку **❓ Помощь** в главном меню.

### Главное меню

- **📚 Выбрать тему и начать** — иерархический выбор → тест
- **🎯 Начать рандомный тест** — вопросы из разных тем
- **📊 Мой прогресс** — последние 10 результатов
- **❓ Помощь** — инструкция по использованию
- **🔧 Админ-панель** — для администраторов

---

## Технические решения

### Структурированная генерация AI-вопросов

Промпт требует ответ в фиксированном формате с маркерами `[QUESTION]`, `[CORRECT_ANSWER]`, `[INCORRECT_OPTIONS]`, `[EXPLANATION]`. Модель проходит self-verification: объяснение должно совпадать с правильным ответом. При rate limit (429) — exponential backoff (2 → 4 → 8 сек).

```python
# src/services/ai_service_improved.py
def generate_task(self, topic, task_type, main_topic=None, language='ru', max_retries=3):
    prompt = self._get_universal_prompt(topic, task_type, main_topic, language)
    retries = 0
    while retries < max_retries:
        try:
            response_text = self.model.generate_content(prompt).text
            return self._parse_structured_response(response_text)
        except exceptions.ResourceExhausted:
            retries += 1
            time.sleep(2 ** retries)
```

### Параллельная генерация без блокировки event loop

```python
# src/services/question_service.py
semaphore = asyncio.Semaphore(10)

async def _semaphored_generate(task_type):
    async with semaphore:
        return await asyncio.to_thread(self._generate_ai_task, topic, task_type, main_topic, language)
```

### Управляемые сообщения (чистый чат)

`MessageManager` хранит одно сообщение на `message_type` в БД. При обновлении UI — редактирует существующее или удаляет старое перед отправкой нового. Исключает накопление десятков сообщений в чате.

### Zero-touch деплой

При первом запуске на пустой PostgreSQL (`USE_POSTGRESQL=true`) `init_app.py` автоматически:
1. Создаёт таблицы (`init_database`)
2. Наполняет темами RU + KK (`init_topics`)
3. Создаёт суперадмина из env-переменных (`init_superadmin`)

---

## Быстрый старт (локально)

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Переменные окружения

Создайте файл `.env`:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Google Gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname
USE_POSTGRESQL=true

# Суперадмин (для автоматической инициализации)
SUPERADMIN_ID=123456789
SUPERADMIN_USERNAME=admin_username
SUPERADMIN_FIO=Иванов Иван Иванович

# Health check (опционально)
PORT=8000
```

### 3. Инициализация (если `USE_POSTGRESQL=false` или ручной запуск)

```bash
python src/init_database.py
python src/init_topics.py
python src/init_superadmin.py
```

### 4. Запуск

```bash
python main.py
```

---

## Деплой в production

### Railway + Neon (рекомендуется)

1. Создайте PostgreSQL на [neon.tech](https://neon.tech)
2. Создайте проект на [railway.app](https://railway.app) и подключите репозиторий
3. Установите переменные окружения (`DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `USE_POSTGRESQL=true`, `SUPERADMIN_*`)
4. Railway соберёт Docker-образ и запустит `python main.py`
5. При первом запуске бот автоматически инициализирует БД

Flask health check на `GET /` возвращает `{"status": "ok"}` — Railway использует его для мониторинга.

### Docker

```bash
docker build -t go2study-bot .
docker run --env-file .env -p 8000:8000 go2study-bot
```

Образ запускается от непривилегированного пользователя `botuser` (uid 1000).

---

## Тестирование

```bash
python -m unittest tests/test_ai_service_improved.py
```

Покрытие: парсинг структурированных AI-ответов, обработка ошибок API, валидация формата вопросов.

---

## Дополнительная документация

Подробный changelog и технические заметки — в [DOCS.md](DOCS.md).
