# 📁 Полная структура проекта Go2Study Bot

## 🏗️ Общая архитектура

Go2Study Bot - это Telegram бот для изучения математики с адаптивной системой обучения. Проект построен по модульной архитектуре с четким разделением ответственности.

### 🎯 Основные принципы архитектуры:
- **Модульность**: Каждый модуль отвечает за конкретную функциональность
- **Разделение слоев**: Handlers → Services → Database
- **Нормализованная БД**: Структура main_topics → subtopics → questions
- **Многоязычность**: Поддержка русского и казахского языков
- **Админ-система**: Полноценная панель управления

---

## 📂 Корневая директория

### 🔧 Конфигурационные файлы

#### `requirements.txt` (295B, 9 строк)
Зависимости Python проекта:
```
python-telegram-bot>=20.0
google-generativeai
PyPDF2
Pillow
python-dotenv
requests
aiofiles
python-multipart
fastapi
```

#### `setup.py` (5.3KB, 171 строк)
Скрипт автоматической установки и настройки проекта:
- **Функции:**
  - `check_python_version()` - проверка версии Python (≥3.8)
  - `install_requirements()` - установка зависимостей
  - `create_env_file()` - создание .env файла
  - `setup_database()` - инициализация базы данных
  - `create_superadmin()` - создание суперадмина
  - `main()` - основная функция установки

#### `.gitignore` (188B, 24 строки)
Исключения для Git:
- Файлы окружения (.env)
- Кэш Python (__pycache__)
- База данных (*.db)
- Логи и временные файлы

### 🚀 Деплой файлы

#### `Dockerfile` (995B, 38 строк)
Контейнеризация приложения:
- Базовый образ: python:3.10-slim
- Установка зависимостей
- Копирование кода
- Запуск бота

#### `docker-compose.yml` (1.1KB, 35 строк)
Оркестрация Docker контейнеров:
- Сервис go2study-bot
- Переменные окружения
- Монтирование томов
- Политика перезапуска

#### `Procfile` (32B, 1 строка)
Конфигурация для Heroku:
```
web: python main.py
```

#### `go2study-bot.service` (609B, 30 строк)
Systemd сервис для Linux:
- Автозапуск при загрузке системы
- Перезапуск при сбоях
- Логирование

### 📖 Документация

#### `README.md` (6.5KB, 235 строк)
Основная документация проекта:
- Описание функций
- Инструкции по установке
- Примеры использования

#### `DOCS.md` (98KB, 1568 строк)
Подробная техническая документация:
- Архитектура системы
- Changelog изменений
- Готовность к продакшену

#### `deploy_guide.md` (7.4KB, 310 строк)
Руководство по деплою:
- VPS/Сервер установка
- Docker деплой
- Cloud платформы (Heroku, Railway)

#### `PDF_FORMAT_GUIDE.md` (7.6KB, 217 строк)
Руководство по формату PDF файлов для импорта вопросов

### 🗄️ Данные и логи

#### `math_bot.db` (1.2MB)
SQLite база данных со всеми данными проекта

#### `database_monitor.log` (1.9KB, 23 строки)
Файл логирования мониторинга базы данных

### 📁 Директории для данных

#### `question_images/`
Директория для хранения изображений вопросов (пустая)

#### `files/`
Директория для хранения PDF файлов с вопросами:
- `Логические задачи.pdf` (59KB)
- `Действия с дробями.pdf` (53KB)
- `Өрнектерді салыстыру.pdf` (39KB)
- `Чётные и нечётные числа.pdf` (56KB)
- `Перевод единиц.pdf` (41KB)
- `Сравнение дробей.pdf` (52KB)
- `Тема_ Логические вопросы (31).pdf` (106KB)

#### `backups/`
Директория для резервных копий базы данных:
- `startup_backup` (331B)
- `scheduled_backup_20250620_170129.db` (1.2MB)
- `scheduled_backup_20250620_170129_metadata.json` (331B)

#### `temp/`
Временная директория (пустая)

#### `uploads/`
Директория для загрузок (пустая)

#### `venv/`
Виртуальное окружение Python

---

## 🤖 Основной файл бота

### `main.py` (18KB, 521 строк)
**Главный файл запуска бота с полной функциональностью**

**Основные функции:**
- `main()` - точка входа в приложение
- `handle_text_with_admin()` - обработка текста с админскими функциями
- `handle_document_with_admin()` - обработка документов с админскими функциями

**Инициализация сервисов:**
- Создание экземпляров Database, AIService, QuestionService
- Инициализация обработчиков команд, callback'ов и админ-панели
- Настройка таймаутов HTTP запросов

**Обработчики команд:**
- `/start` - запуск бота
- `/stop` - остановка теста
- `/reset` - сброс прогресса
- `/change_fio` - изменение ФИО
- `/change_grade` - изменение класса
- `/change_language` - изменение языка
- `/myid` - получение ID пользователя
- `/admin` - админ-панель

**Callback обработчики:**
- Админ-панель и все её разделы
- Управление студентами (добавление, редактирование, удаление)
- Управление темами и вопросами
- Статистика и отчеты

---

## 📁 src/ - Исходный код

### 🔧 Инициализация

#### `init_superadmin.py` (2.8KB, 69 строк)
**Скрипт для создания суперадмина**

**Основные функции:**
- `create_superadmin()` - создание суперадмина
- `main()` - интерактивное создание админа

---

## 📁 src/services/ - Бизнес-логика

### 🗄️ `database.py` (142KB, 3178 строк)
**Главный сервис для работы с базой данных**

#### **Основной класс Database:**

**Инициализация и структура:**
- `__init__()` - инициализация БД
- `_init_db()` - создание всех таблиц
- `_initialize_main_topics()` - инициализация базовых тем

**Управление пользователями:**
- `set_user_active(user_id, topic)` - установить пользователя активным
- `set_user_inactive(user_id)` - деактивировать пользователя
- `is_user_active(user_id)` - проверить активность в тесте
- `update_user_activity(user_id)` - обновить время активности
- `register_user(user_id, username)` - регистрация пользователя

**Управление тестами:**
- `add_test_result(user_id, topic, percentage)` - добавить результат теста
- `get_user_test_results(user_id)` - получить результаты пользователя
- `get_user_progress(user_id)` - получить прогресс пользователя
- `get_recent_topics(user_id, limit)` - получить недавние темы

**Управление ошибками:**
- `add_user_error()` - добавить ошибку пользователя
- `decrement_error_count()` - уменьшить счетчик ошибок
- `get_error_topics(user_id)` - получить темы с ошибками
- `get_error_tasks_for_user()` - получить задания с ошибками

**Управление вопросами:**
- `add_question(question)` - добавить вопрос
- `update_question()` - обновить вопрос
- `get_all_questions()` - получить все вопросы
- `get_tasks_for_topic()` - получить задания по теме
- `delete_question_by_id()` - удалить вопрос

**Управление темами:**
- `get_all_topics(active_only)` - получить все темы
- `add_topic()` - добавить тему
- `update_topic()` - обновить тему
- `delete_topic()` - удалить тему (мягкое)
- `delete_topic_permanently()` - удалить тему (жесткое)

**Управление админами:**
- `is_admin(user_id)` - проверить права админа
- `is_super_admin(user_id)` - проверить права суперадмина
- `add_admin()` - добавить админа
- `remove_admin()` - удалить админа
- `get_all_admins()` - получить всех админов

**Управление whitelist:**
- `is_user_allowed(username)` - проверить доступ по username
- `is_user_allowed_by_id(user_id)` - проверить доступ по ID
- `add_allowed_user()` - добавить в whitelist
- `remove_allowed_user()` - удалить из whitelist
- `get_all_allowed_users()` - получить всех разрешенных

**Многоязычность:**
- `get_user_language(user_id)` - получить язык пользователя
- `update_user_language()` - обновить язык
- `get_topics_by_language()` - получить темы по языку
- `clear_user_data_on_language_change()` - очистить данные при смене языка

**Статистика (для админов):**
- `get_student_detailed_statistics()` - детальная статистика ученика
- `get_all_students_summary()` - сводка всех учеников
- `get_class_statistics()` - статистика по классам
- `get_user_historical_stats()` - историческая статистика

**Новые методы с topic_id:**
- `get_tasks_for_topic_id()` - получить задания по ID темы
- `add_question_with_topic_id()` - добавить вопрос с ID темы
- `rename_topic_by_id()` - переименовать тему по ID

### 🤖 `ai_service.py` (36KB, 535 строк)
**Сервис для работы с AI (Google Gemini)**

#### **Основной класс AIService:**

**Инициализация:**
- `__init__()` - настройка API ключа и модели
- `_setup_model()` - конфигурация модели Gemini

**Генерация вопросов:**
- `generate_questions()` - основная функция генерации
- `_create_prompt()` - создание промпта для AI
- `_parse_ai_response()` - парсинг ответа AI
- `_validate_question()` - валидация сгенерированного вопроса

**Обработка ответов:**
- `_clean_text()` - очистка текста от лишних символов
- `_extract_question_parts()` - извлечение частей вопроса
- `_format_question()` - форматирование вопроса

**Работа с промптами:**
- `_get_topic_context()` - получение контекста темы
- `_build_examples()` - построение примеров для AI
- `_optimize_prompt()` - оптимизация промпта

### 🧠 `ai_service_improved.py` (26KB, 405 строк)
**Улучшенная версия AI сервиса (экспериментальная)**

### 📚 `question_service.py` (48KB, 799 строк)
**Сервис для управления вопросами и тестами**

#### **Основной класс QuestionService:**

**Получение заданий:**
- `get_tasks_for_topic()` - получить задания по теме
- `get_error_tasks()` - получить задания с ошибками
- `get_mixed_tasks()` - получить смешанные задания

**Обработка ответов:**
- `process_user_answer()` - обработать ответ пользователя
- `check_answer_correctness()` - проверить правильность ответа
- `update_user_errors()` - обновить ошибки пользователя

**Управление тестами:**
- `start_test()` - начать тест
- `finish_test()` - завершить тест
- `calculate_test_result()` - вычислить результат теста

**Адаптивная логика:**
- `get_adaptive_questions()` - получить адаптивные вопросы
- `adjust_difficulty()` - настроить сложность
- `analyze_user_performance()` - анализ производительности

### 🎯 `topic_manager.py` (25KB, 544 строки)
**Сервис для управления темами**

#### **Основной класс TopicManager:**

**Управление темами:**
- `get_all_topics()` - получить все темы
- `get_topics_by_language()` - получить темы по языку
- `create_topic()` - создать тему
- `update_topic()` - обновить тему
- `delete_topic()` - удалить тему

**Структура тем:**
- `get_main_topics()` - получить основные разделы
- `get_subtopics()` - получить подтемы
- `get_topic_hierarchy()` - получить иерархию тем

**Статистика тем:**
- `get_topic_statistics()` - статистика по темам
- `get_question_counts()` - количество вопросов по темам
- `get_topic_progress()` - прогресс по темам

### 📄 `pdf_processor.py` (47KB, 927 строк)
**Сервис для обработки PDF файлов**

#### **Основной класс PDFProcessor:**

**Обработка PDF:**
- `process_pdf()` - основная функция обработки
- `extract_text_from_pdf()` - извлечение текста
- `parse_questions()` - парсинг вопросов из текста

**Парсинг вопросов:**
- `_parse_question_block()` - парсинг блока вопроса
- `_extract_options()` - извлечение вариантов ответов
- `_identify_correct_answer()` - определение правильного ответа

**Валидация:**
- `_validate_question_format()` - валидация формата вопроса
- `_check_required_fields()` - проверка обязательных полей
- `_clean_question_text()` - очистка текста вопроса

**Функции-помощники:**
- `add_questions_to_db()` - добавление вопросов в БД
- `format_pdf_results()` - форматирование результатов

### 🎲 `random_test_service.py` (22KB, 415 строк)
**Сервис для случайных тестов**

#### **Основной класс RandomTestService:**

**Генерация тестов:**
- `generate_random_test()` - генерация случайного теста
- `select_random_questions()` - выбор случайных вопросов
- `mix_question_sources()` - смешивание источников вопросов

**Логика адаптации:**
- `adjust_test_difficulty()` - настройка сложности теста
- `balance_question_types()` - балансировка типов вопросов
- `prioritize_weak_areas()` - приоритет слабых мест

**Статистика тестов:**
- `get_test_statistics()` - статистика тестов
- `analyze_test_performance()` - анализ производительности
- `track_improvement()` - отслеживание улучшений

---

## 📁 src/handlers/ - Обработчики

### 🎮 `callback_handlers.py` (63KB, 1181 строка)
**Обработчики callback запросов (нажатия кнопок)**

#### **Основные функции:**

**Выбор языка и тем:**
- `handle_language_selection()` - выбор языка
- `handle_topic_selection()` - выбор темы для теста
- `handle_main_topic_selection()` - выбор основного раздела

**Навигация по тестам:**
- `handle_answer_selection()` - выбор ответа на вопрос
- `handle_next_question()` - переход к следующему вопросу
- `handle_previous_question()` - возврат к предыдущему вопросу
- `show_question_with_navigation()` - показать вопрос с навигацией

**Завершение тестов:**
- `handle_finish_test()` - завершение теста
- `show_test_results()` - показ результатов теста
- `handle_restart_test()` - перезапуск теста

**Работа с ошибками:**
- `handle_review_errors()` - просмотр ошибок
- `handle_error_practice()` - практика ошибок
- `show_error_explanation()` - показ объяснения ошибки

**Навигация:**
- `handle_back_to_main()` - возврат в главное меню
- `handle_back_to_topics()` - возврат к выбору тем

### 💬 `command_handlers.py` (45KB, 854 строки)
**Обработчики текстовых команд**

#### **Основные команды:**

**Пользовательские команды:**
- `start_command()` - команда /start
- `help_command()` - команда /help
- `stats_command()` - команда /stats
- `myid_command()` - команда /myid

**Регистрация и настройка:**
- `handle_user_setup()` - настройка пользователя
- `handle_language_choice()` - выбор языка
- `collect_user_info()` - сбор информации о пользователе

**Обработка текста:**
- `handle_text_message()` - обработка текстовых сообщений
- `handle_user_info_input()` - ввод информации пользователя
- `validate_user_input()` - валидация ввода

**Админ команды:**
- `admin_command()` - команда /admin
- `handle_admin_access()` - проверка админских прав

### 🏗️ `base_handler.py` (3.0KB, 71 строка)
**Базовый класс для всех обработчиков**

#### **Класс BaseHandler:**
- `__init__()` - инициализация с БД и сервисами
- `safe_answer_callback()` - безопасный ответ на callback
- `handle_callback_error()` - обработка ошибок callback
- `log_user_action()` - логирование действий пользователя

---

## 📁 src/handlers/admin/ - Админ-панель

### 🏛️ `base.py` (15KB, 267 строк)
**Базовый класс для админ-обработчиков**

#### **Класс AdminBaseHandler:**
- `admin_panel()` - главная админ-панель
- `handle_admin_text()` - обработка текста в админ-режиме
- `handle_admin_document()` - обработка документов (PDF)

### 📊 `stats.py` (9.6KB, 200 строк)
**Статистика и отчеты**

#### **Класс StatsHandler:**
- `show_stats()` - общая статистика системы
- `show_user_history()` - история активности пользователей
- `generate_reports()` - генерация отчетов
- `export_statistics()` - экспорт статистики

### 👥 `students.py` (50KB, 906 строк)
**Управление учениками**

#### **Класс StudentsHandler:**

**Главное меню:**
- `students_menu()` - меню управления учениками

**Добавление учеников:**
- `add_student_by_id_start()` - начало добавления по ID
- `handle_add_student_by_id()` - обработка добавления по ID
- `handle_student_by_id_fullname()` - ввод ФИО
- `handle_student_by_id_grade()` - ввод класса

**Просмотр учеников:**
- `list_students()` - список всех учеников
- `show_student_details()` - детальная информация об ученике
- `show_class_statistics()` - статистика по классам

**Редактирование учеников:**
- `edit_student_start()` - начало редактирования
- `edit_student_select()` - выбор параметра для редактирования
- `edit_student_name_start()` - изменение ФИО
- `edit_student_grade_start()` - изменение класса
- `edit_student_language_start()` - изменение языка
- `set_student_language()` - установка языка
- `edit_student_status_toggle()` - переключение статуса доступа

**Удаление учеников:**
- `remove_student_start()` - начало удаления
- `remove_student_confirm()` - подтверждение удаления
- `remove_student_execute()` - выполнение удаления

**Обработчики текста:**
- `handle_edit_student_name()` - обработка изменения ФИО
- `handle_edit_student_grade()` - обработка изменения класса

### ❓ `questions.py` (104KB, 1949 строк)
**Управление вопросами**

#### **Класс QuestionsHandler:**

**Главное меню:**
- `questions_menu()` - меню управления вопросами

**Просмотр вопросов:**
- `view_questions()` - просмотр всех вопросов
- `search_questions_start()` - начало поиска
- `handle_search_questions()` - обработка поиска
- `show_question_details()` - детали вопроса

**Добавление вопросов:**
- `add_question_menu()` - меню добавления
- `add_single_question_start()` - добавление одного вопроса
- `handle_add_question_text()` - ввод текста вопроса
- `handle_add_question_option_a/b/c/d()` - ввод вариантов ответов
- `handle_add_question_correct()` - ввод правильного ответа
- `handle_add_question_explanation()` - ввод объяснения

**Импорт из PDF:**
- `upload_pdf_start()` - начало загрузки PDF
- `process_pdf_file()` - обработка PDF файла
- `confirm_pdf_import()` - подтверждение импорта

**Редактирование вопросов:**
- `edit_question_start()` - начало редактирования
- `handle_edit_question_search()` - поиск для редактирования
- `handle_edit_question_id()` - редактирование по ID
- `handle_edit_question_explanation()` - изменение объяснения

**Удаление вопросов:**
- `delete_questions_menu()` - меню удаления
- `delete_single_question_start()` - удаление одного вопроса
- `delete_ai_questions_start()` - удаление AI вопросов
- `delete_all_questions_confirm()` - подтверждение массового удаления

**AI генерация:**
- `generate_ai_questions_start()` - начало AI генерации
- `handle_ai_generation_count()` - количество для генерации
- `process_ai_generation()` - процесс генерации

### 📚 `topics.py` (48KB, 861 строка)
**Управление темами**

#### **Класс TopicsHandler:**

**Главное меню:**
- `topics_menu()` - меню управления темами

**Просмотр тем:**
- `view_topics()` - просмотр всех тем
- `show_topic_details()` - детали темы
- `show_topics_by_language()` - темы по языку

**Добавление тем:**
- `add_topic_start()` - начало добавления темы
- `handle_add_topic_name()` - ввод названия темы
- `select_main_topic_for_new()` - выбор основного раздела

**Редактирование тем:**
- `edit_topic_start()` - начало редактирования
- `edit_topic_select()` - выбор темы для редактирования
- `rename_topic_start()` - переименование темы
- `handle_rename_topic()` - обработка переименования
- `toggle_topic_status()` - переключение статуса темы
- `change_topic_section()` - изменение раздела темы

**Удаление тем:**
- `delete_topic_start()` - начало удаления
- `delete_topic_confirm()` - подтверждение удаления
- `delete_topic_execute()` - выполнение удаления

### 📋 `sections.py` (30KB, 584 строки)
**Управление разделами (main_topics)**

#### **Класс SectionsHandler:**

**Главное меню:**
- `sections_menu()` - меню управления разделами

**Просмотр разделов:**
- `view_sections()` - просмотр всех разделов
- `show_section_details()` - детали раздела
- `show_sections_by_language()` - разделы по языку

**Управление разделами:**
- `add_section_start()` - добавление раздела
- `edit_section_start()` - редактирование раздела
- `delete_section_start()` - удаление раздела
- `toggle_section_status()` - переключение статуса

### 👑 `admins.py` (22KB, 395 строк)
**Управление администраторами**

#### **Класс AdminsHandler:**

**Главное меню:**
- `admins_menu()` - меню управления админами

**Просмотр админов:**
- `list_admins()` - список всех админов
- `show_admin_details()` - детали админа

**Добавление админов:**
- `add_admin_start()` - начало добавления админа
- `handle_add_admin_id()` - ввод ID админа
- `handle_add_admin_name()` - ввод имени админа
- `confirm_add_admin()` - подтверждение добавления

**Удаление админов:**
- `remove_admin_start()` - начало удаления админа
- `remove_admin_confirm()` - подтверждение удаления
- `remove_admin_execute()` - выполнение удаления

### 🔧 `__init__.py` (31KB, 562 строки)
**Инициализация админ-модуля и роутинг**

**Основные функции:**
- `setup_admin_handlers()` - настройка всех админ-обработчиков
- `route_admin_callback()` - маршрутизация админ-callbacks
- `handle_admin_text_input()` - обработка текстового ввода
- `check_admin_permissions()` - проверка прав доступа

---

## 📁 src/utils/ - Утилиты

### ⌨️ `keyboards.py` (10KB, 210 строк)
**Клавиатуры для интерфейса**

**Основные функции:**
- `get_language_keyboard()` - клавиатура выбора языка
- `get_main_topics_keyboard()` - клавиатура основных тем
- `get_topics_keyboard()` - клавиатура тем
- `get_test_navigation_keyboard()` - навигация по тесту
- `get_answer_options_keyboard()` - варианты ответов
- `get_admin_main_keyboard()` - главная админ-клавиатура

### 🌐 `translations.py` (9.5KB, 152 строки)
**Переводы и локализация**

**Основные функции:**
- `get_translation()` - получить перевод
- `translate_message()` - перевести сообщение
- `get_user_language()` - получить язык пользователя
- `format_localized_message()` - форматировать локализованное сообщение

**Словари переводов:**
- `TRANSLATIONS_RU` - русские переводы
- `TRANSLATIONS_KK` - казахские переводы

---

## 📁 src/config/ - Конфигурация

### 🔧 `constants.py` (6.5KB, 138 строк)
**Основные константы (русский язык)**

**Основные константы:**
- `TELEGRAM_BOT_TOKEN` - токен бота
- `GEMINI_API_KEY` - ключ Gemini API
- `DATABASE_PATH` - путь к базе данных
- `MAX_QUESTIONS_PER_TEST` - максимум вопросов в тесте
- `DEFAULT_LANGUAGE` - язык по умолчанию

**Иерархия тем:**
```python
TOPIC_HIERARCHY = {
    "Алгебра": [
        "Линейные уравнения",
        "Квадратные уравнения",
        "Системы уравнений"
    ],
    "Геометрия": [
        "Треугольники",
        "Четырехугольники",
        "Окружности"
    ]
    # ... и другие
}
```

**Сообщения:**
- `WELCOME_MESSAGE` - приветственное сообщение
- `HELP_MESSAGE` - справочное сообщение
- `ERROR_MESSAGES` - сообщения об ошибках

### 🇰🇿 `constants_kk.py` (8.9KB, 143 строки)
**Константы для казахского языка**

**Иерархия тем на казахском:**
```python
TOPIC_HIERARCHY_KK = {
    "Алгебра": [
        "Сызықтық теңдеулер",
        "Квадрат теңдеулер",
        "Теңдеулер жүйесі"
    ],
    "Геометрия": [
        "Үшбұрыштар",
        "Төртбұрыштар",
        "Шеңберлер"
    ]
    # ... и другие
}
```

### 💬 `messages_kk.py` (8.4KB, 119 строк)
**Сообщения на казахском языке**

**Основные сообщения:**
- `WELCOME_MESSAGE_KK` - приветствие на казахском
- `HELP_MESSAGE_KK` - справка на казахском
- `TEST_MESSAGES_KK` - сообщения тестов
- `ERROR_MESSAGES_KK` - ошибки на казахском

### 📁 `src/question_images/`
Дублированная директория для изображений вопросов (пустая)

---

## 🗄️ Структура базы данных

### 📋 Основные таблицы:

#### `admins`
- `user_id` (PRIMARY KEY) - ID администратора
- `username` - username в Telegram
- `full_name` - полное имя
- `is_super_admin` - флаг суперадмина
- `created_by` - кто создал
- `created_at` - дата создания

#### `allowed_users` (whitelist)
- `id` (PRIMARY KEY) - автоинкремент ID
- `user_id` - ID пользователя в Telegram
- `username` - username в Telegram
- `full_name` - полное имя ученика
- `grade` - класс (1-11)
- `language` - язык интерфейса (ru/kk)
- `is_active` - активность в тесте (0/1)
- `has_access` - доступ к системе (0/1)
- `current_topic` - текущая тема теста
- `last_activity` - последняя активность
- `added_by` - кто добавил
- `added_at` - дата добавления

#### `main_topics`
- `id` (PRIMARY KEY) - ID основного раздела
- `name` - название раздела
- `language` - язык (ru/kk)
- `is_active` - активность (0/1)
- `order_index` - порядок отображения
- `created_by` - кто создал
- `created_at` - дата создания

#### `subtopics`
- `id` (PRIMARY KEY) - ID подтемы
- `name` - название подтемы
- `main_topic_id` - ссылка на основной раздел
- `description` - описание
- `is_active` - активность (0/1)
- `order_index` - порядок отображения
- `created_by` - кто создал
- `created_at` - дата создания

#### `questions`
- `id` (PRIMARY KEY) - ID вопроса
- `topic_id` - ссылка на подтему
- `question` - текст вопроса
- `answer` - правильный ответ
- `explanation` - объяснение
- `incorrect_options` - неправильные варианты (JSON)
- `question_type` - тип вопроса (standard/multiple)
- `source` - источник (db/ai/pdf)
- `image_path` - путь к изображению
- `created_at` - дата создания

#### `test_results`
- `id` (PRIMARY KEY) - ID результата
- `user_id` - ID пользователя
- `topic` - название темы
- `percentage` - процент правильных ответов
- `timestamp` - время прохождения

#### `user_errors`
- `id` (PRIMARY KEY) - ID ошибки
- `user_id` - ID пользователя
- `question_id` - ID вопроса
- `topic` - название темы
- `user_answer` - ответ пользователя
- `correct_answer` - правильный ответ
- `error_count` - количество ошибок
- `first_error_date` - дата первой ошибки
- `last_error_date` - дата последней ошибки

---

## 🔄 Основные потоки данных

### 1. Регистрация пользователя:
```
/start → check whitelist → language selection → user info → ready to test
```

### 2. Прохождение теста:
```
topic selection → question generation → answer processing → result calculation → error tracking
```

### 3. Админ-управление:
```
/admin → admin panel → specific management → database operations → confirmation
```

### 4. AI генерация:
```
topic selection → prompt creation → Gemini API → response parsing → database storage
```

---

## 🔧 Ключевые особенности архитектуры

### ✅ Преимущества:

1. **Модульность**: Четкое разделение ответственности
2. **Масштабируемость**: Легко добавлять новые функции
3. **Многоязычность**: Полная поддержка ru/kk
4. **Нормализованная БД**: Эффективная структура данных
5. **Админ-система**: Полноценное управление
6. **AI интеграция**: Автоматическая генерация контента
7. **Обработка ошибок**: Надежная работа
8. **Логирование**: Полное отслеживание действий
9. **Система резервного копирования**: Автоматические бэкапы
10. **Мониторинг БД**: Отслеживание состояния базы данных

### 🎯 Принципы проектирования:

1. **DRY (Don't Repeat Yourself)**: Избегание дублирования кода
2. **SOLID**: Соблюдение принципов объектно-ориентированного программирования
3. **Separation of Concerns**: Разделение ответственности между модулями
4. **Database First**: Нормализованная структура БД как основа
5. **API First**: Четкие интерфейсы между модулями

---

## 🚀 Готовность к продакшену

Проект полностью готов к развертыванию в продакшене с поддержкой:
- Docker контейнеризации
- Systemd сервисов
- Облачных платформ (Heroku, Railway)
- VPS/выделенных серверов
- Автоматического масштабирования
- Мониторинга и логирования
- Системы резервного копирования
- Обработки больших объемов данных

---

## 📊 Изменения в структуре

### ✅ Обновлено:
1. **Основной файл**: `main.py` вместо `bot.py`
2. **Удалены отсутствующие файлы**: `bot_universal.py`, `bot_factory.py`, `bot_compat.py`
3. **Добавлены новые директории**: `backups/`, `temp/`, `uploads/`, `venv/`
4. **Обновлены размеры файлов** согласно текущему состоянию
5. **Добавлены файлы логирования**: `database_monitor.log`
6. **Обновлено содержимое `files/`** с реальными PDF файлами
7. **Исправлен `Procfile`** для запуска `main.py`

---

*Документация актуальна на январь 2025 года* 