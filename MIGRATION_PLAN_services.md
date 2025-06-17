# План обновления сервисов для полного перехода на topic_id

## Найденные проблемы

### QuestionService - использует старое поле 'topic'

**Файл:** `src/services/question_service.py`

**Проблемные места:**
1. **Строка 370** - AI вопросы (retake mode)
2. **Строка 514** - AI вопросы (final generation)  
3. **Строка 584** - AI вопросы (additional attempts)

**Текущий код:**
```python
self.db.add_question({
    'topic': topic,  # ❌ Использует старое поле
    'question': question,
    'answer': correct_answer,
    'explanation': explanation,
    'incorrect_options': '...',
    'question_type': 'standard',
    'source': 'ai'
})
```

**Проблема:**
При генерации AI вопросов всё ещё используется старое поле `topic`, что:
- Заполняет старую колонку `topic` в таблице `questions`
- Поддерживает старую архитектуру
- Препятствует полному переходу на `topic_id`

## Решение

### 1. Обновить QuestionService

**Заменить на:**
```python
# Получаем topic_id для темы
topic_id = self.db._get_topic_id_by_name(topic)
if not topic_id:
    logging.error(f"Не найден topic_id для темы '{topic}'")
    continue

# Используем новый метод с topic_id
success = self.db.add_question_with_topic_id({
    'question': question,
    'answer': correct_answer,
    'explanation': explanation,
    'incorrect_options': '...',
    'question_type': 'standard',
    'source': 'ai'
}, topic_id)
```

### 2. Обновить метод add_question() в Database

**Текущий add_question() использует поле topic:**
```python
def add_question(self, question: dict) -> None:
    cursor.execute('''
        INSERT INTO questions (topic, question, answer, ...)
        VALUES (?, ?, ?, ...)
    ''', (question['topic'], ...))
```

**Нужно обновить на:**
```python
def add_question(self, question: dict) -> None:
    # Получаем topic_id
    topic_id = self._get_topic_id_by_name(question['topic'])
    if not topic_id:
        logging.error(f"Не найден topic_id для темы '{question['topic']}'")
        return False
    
    # Используем add_question_with_topic_id
    return self.add_question_with_topic_id(question, topic_id)
```

### 3. Проверить другие сервисы

**AI Service** - ✅ Не работает напрямую с БД, только генерирует вопросы

**Другие места использования add_question:**
- Нужно найти все вызовы `add_question()` в проекте
- Обновить их для использования topic_id

## План реализации

### Этап 1: Обновление QuestionService ✨
```python
# В методе get_or_generate_tasks()
# Заменить все 3 места:

# Получаем topic_id один раз в начале метода
topic_id = self.db._get_topic_id_by_name(topic)
if not topic_id:
    logging.error(f"Не найден topic_id для темы '{topic}'")
    return []

# Далее используем add_question_with_topic_id
success = self.db.add_question_with_topic_id({
    'question': question,
    'answer': correct_answer,
    'explanation': explanation,
    'incorrect_options': '...',
    'question_type': 'standard',
    'source': 'ai'
}, topic_id)
```

### Этап 2: Обновление Database.add_question() ✨
```python
def add_question(self, question: dict) -> bool:
    """
    Обновленный метод для обратной совместимости.
    Автоматически конвертирует topic -> topic_id
    """
    if 'topic' in question:
        topic_id = self._get_topic_id_by_name(question['topic'])
        if not topic_id:
            logging.error(f"Не найден topic_id для темы '{question['topic']}'")
            return False
        
        # Удаляем topic из словаря и используем topic_id
        question_copy = question.copy()
        del question_copy['topic']
        return self.add_question_with_topic_id(question_copy, topic_id)
    else:
        logging.error("Не указана тема (topic) для вопроса")
        return False
```

### Этап 3: Поиск других мест ✨
```bash
# Найти все использования add_question
grep -r "add_question" src/ --include="*.py"

# Найти все использования поля topic в INSERT
grep -r "INSERT.*topic" src/ --include="*.py"
```

### Этап 4: Тестирование ✨
- Проверить что AI вопросы сохраняются с topic_id
- Убедиться что старые методы работают (обратная совместимость)
- Протестировать генерацию вопросов

### Этап 5: Финальная миграция ✨
После обновления всех сервисов:
```python
# В Database.__init__()
self._migrate_remove_topic_column(cursor)
```

## Ожидаемый результат

После всех обновлений:
1. ✅ AI вопросы сохраняются только с `topic_id`
2. ✅ Поле `topic` больше не используется при создании вопросов
3. ✅ Можно безопасно удалить колонку `topic` из `questions`
4. ✅ Переименование тем затрагивает ТОЛЬКО `subtopics` (1 операция)

## Приоритет

**ВЫСОКИЙ** - это критически важно для завершения решения проблемы переименования тем. 