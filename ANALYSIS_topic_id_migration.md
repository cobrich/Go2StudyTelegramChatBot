# Анализ изменения структуры базы данных: Добавление topic_id в таблицу questions

## Текущая структура

### Таблицы:
1. **main_topics** - основные разделы (id, name, language, is_active, ...)
2. **subtopics** - подтемы (id, name, main_topic_id, is_active, ...)  
3. **questions** - вопросы (id, topic TEXT, question, answer, ...)

### Текущая связь:
```
questions.topic (TEXT) <---> subtopics.name (TEXT)
```

## Предлагаемые изменения

### Два варианта решения:

#### Вариант 1: Добавить topic_id (РЕКОМЕНДУЕМЫЙ)
**Плюсы:**
- Надежная связь по ID вместо названий
- При изменении названия темы не нужно обновлять сотни строк в questions
- Более эффективные JOIN-запросы
- Соответствует принципам нормализации БД

**Минусы:**
- Требует миграции данных
- Больше изменений в коде

#### Вариант 2: Оставить как есть (topic по названию)
**Плюсы:**
- Минимальные изменения в коде
- Простая структура

**Минусы:**
- При переименовании темы нужно обновлять все связанные вопросы
- Возможны проблемы с консистентностью данных
- Менее эффективные запросы

## РЕКОМЕНДАЦИЯ: Вариант 1 (topic_id)

### План миграции:

#### 1. Изменения в схеме БД:
```sql
-- Добавляем новую колонку
ALTER TABLE questions ADD COLUMN topic_id INTEGER;

-- Заполняем topic_id на основе существующих названий
UPDATE questions 
SET topic_id = (SELECT id FROM subtopics WHERE name = questions.topic);

-- Удаляем записи где не нашлось соответствие (orphaned records)
DELETE FROM questions WHERE topic_id IS NULL;

-- Добавляем внешний ключ
-- (SQLite не поддерживает добавление FK к существующей колонке, 
-- поэтому создадим с ограничением в приложении)

-- Опционально: можем оставить topic для совместимости или удалить позже
```

#### 2. Функции БД, требующие изменений:

##### В `src/services/database.py`:

1. **`_init_db()`** - изменить CREATE TABLE для questions:
   ```sql
   CREATE TABLE questions (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       topic_id INTEGER NOT NULL,
       topic TEXT,  -- временно оставляем для совместимости
       question TEXT NOT NULL,
       answer TEXT NOT NULL,
       explanation TEXT,
       incorrect_options TEXT,
       question_type TEXT DEFAULT 'standard',
       source TEXT DEFAULT 'db',
       image_path TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (topic_id) REFERENCES subtopics(id)
   )
   ```

2. **`add_question()`** - изменить для работы с topic_id
3. **`get_questions_by_user_language()`** - обновить JOIN
4. **`update_topic_name()`** - упростить (не нужно обновлять questions)
5. **`get_all_questions()`** - обновить SELECT
6. **`get_topic_question_counts()`** - обновить GROUP BY
7. **Все методы с JOIN на questions** - использовать topic_id

##### В `src/services/topic_manager.py`:
1. **`merge_topics()`** - изменить UPDATE на topic_id
2. **`create_topic_if_not_exists()`** - проверить совместимость

##### В `src/handlers/admin/topics.py`:
1. **`handle_edit_topic_name()`** - убрать обновление questions
2. **Все методы работы с темами** - проверить совместимость

##### В `src/handlers/admin/questions.py`:
1. **Методы добавления/редактирования вопросов** - использовать topic_id
2. **Методы выборки** - обновить JOIN

##### В `src/services/random_test_service.py`:
1. **Все методы получения вопросов** - обновить JOIN

##### В `src/handlers/callback_handlers.py`:
1. **Методы работы с вопросами** - обновить для topic_id

#### 3. Порядок изменений:

**Этап 1: Подготовка миграции**
1. Создать метод миграции в Database
2. Добавить поддержку topic_id в существующие методы (с fallback на topic)

**Этап 2: Миграция данных**
1. Выполнить миграцию схемы
2. Заполнить topic_id
3. Проверить консистентность

**Этап 3: Обновление кода**
1. Обновить методы Database для использования topic_id
2. Обновить handlers для работы с новой структурой
3. Тестирование

**Этап 4: Очистка**
1. Удалить колонку topic (опционально)
2. Убрать fallback код

### Оценка рисков:
- **Низкий риск** - изменения затрагивают только БД слой
- **Обратимость** - можем откатиться к topic по названию
- **Тестируемость** - можно тестировать поэтапно

### Альтернативный подход (если слишком сложно):
Если миграция кажется слишком рискованной, можно:
1. Оставить текущую структуру
2. Добавить транзакционное обновление при переименовании тем
3. Добавить проверки консистентности

## Заключение:
Рекомендую **Вариант 1 с topic_id**, так как он решает проблему в корне и улучшает архитектуру. Миграция выполнима и не очень рискованна. 