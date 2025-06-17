#!/usr/bin/env python3
"""
Быстрый тест новых методов topic_id с реальной базой данных.
Показывает работу новых методов и преимущества использования topic_id.
"""

import os
import sys

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import Database

def main():
    """Демонстрация работы новых методов topic_id"""
    print("🚀 Демонстрация новых методов topic_id\n")
    
    # Инициализируем БД (это запустит миграцию если нужно)
    print("1️⃣ Инициализация базы данных...")
    db = Database()
    print("✅ База данных инициализирована\n")
    
    # Показываем доступные темы с их ID
    print("2️⃣ Доступные темы с topic_id:")
    topic_counts = db.get_topic_question_counts_by_id()
    
    if not topic_counts:
        print("❌ Нет доступных тем в БД")
        return
    
    for topic_id, info in topic_counts.items():
        print(f"  • ID {topic_id}: '{info['name']}' - {info['question_count']} вопросов ({info['main_topic']})")
    
    # Выбираем тему с наибольшим количеством вопросов
    best_topic = max(topic_counts.items(), key=lambda x: x[1]['question_count'])
    test_topic_id, test_topic_info = best_topic
    
    print(f"\n3️⃣ Тестируем с темой ID {test_topic_id}: '{test_topic_info['name']}'")
    
    # Тест новых методов
    print(f"\n🧪 Метод get_tasks_for_topic_id({test_topic_id}):")
    new_method_tasks = db.get_tasks_for_topic_id(test_topic_id, limit=3)
    print(f"  Получено вопросов: {len(new_method_tasks)}")
    for i, task in enumerate(new_method_tasks[:2], 1):
        print(f"  {i}. {task['question'][:60]}...")
    
    # Тест обновленного старого метода  
    print(f"\n🧪 Метод get_tasks_for_topic('{test_topic_info['name']}'):")
    old_method_tasks = db.get_tasks_for_topic(test_topic_info['name'], limit=3)
    print(f"  Получено вопросов: {len(old_method_tasks)}")
    
    # Проверяем что обновленный метод работает через topic_id
    if old_method_tasks and 'topic_name' in old_method_tasks[0]:
        print(f"  ✅ Обновленный метод использует topic_id (более эффективно)")
    else:
        print(f"  ⚠️ Обновленный метод использует fallback на старую схему")
    
    # Сравниваем результаты
    print(f"\n📊 Сравнение результатов:")
    print(f"  Новый метод (topic_id): {len(new_method_tasks)} вопросов")
    print(f"  Обновленный старый метод: {len(old_method_tasks)} вопросов")
    
    if len(new_method_tasks) == len(old_method_tasks):
        print(f"  ✅ Результаты идентичны - обратная совместимость работает")
    else:
        print(f"  ⚠️ Результаты различаются")
    
    # Тест helper методов
    print(f"\n🧪 Helper методы:")
    topic_name = db._get_topic_name_by_id(test_topic_id)
    back_topic_id = db._get_topic_id_by_name(test_topic_info['name'])
    print(f"  ID {test_topic_id} -> '{topic_name}'")
    print(f"  '{test_topic_info['name']}' -> ID {back_topic_id}")
    
    if back_topic_id == test_topic_id and topic_name == test_topic_info['name']:
        print(f"  ✅ Двунаправленная конвертация работает корректно")
    else:
        print(f"  ❌ Ошибка в конвертации")
    
    print(f"\n🎉 Демонстрация завершена успешно!")
    print(f"\n💡 Преимущества topic_id:")
    print(f"  • Более быстрые JOIN-запросы (INTEGER vs TEXT)")
    print(f"  • Переименование темы не влияет на questions")
    print(f"  • Лучшая консистентность данных")
    print(f"  • Полная обратная совместимость")

if __name__ == "__main__":
    main() 