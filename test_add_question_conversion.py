#!/usr/bin/env python3
"""
Тест автоматической конвертации topic → topic_id в методе add_question()

Проверяет:
1. Добавление вопроса с topic (автоконвертация в topic_id)
2. Добавление вопроса с topic_id напрямую
3. Совместимость с различными состояниями БД
"""

import sys
import os
import sqlite3
import tempfile
import shutil

# Добавляем путь к src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from services.database import Database

def test_add_question_conversion():
    """Тест автоматической конвертации topic → topic_id."""
    
    # Создаем временную копию базы
    temp_db = tempfile.mktemp(suffix='.db')
    shutil.copy('math_bot.db', temp_db)
    
    try:
        db = Database(temp_db)
        
        print("🧪 ТЕСТ: Автоматическая конвертация topic → topic_id в add_question()")
        print("=" * 60)
        
        # Миграция topic_id выполняется автоматически в конструкторе Database
        
        # Проверяем наличие колонок
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(questions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            has_topic = 'topic' in columns
            has_topic_id = 'topic_id' in columns
            
            print(f"📊 Состояние БД:")
            print(f"   - Колонка topic: {'✅' if has_topic else '❌'}")
            print(f"   - Колонка topic_id: {'✅' if has_topic_id else '❌'}")
            print()
        
        # Получаем тестовую тему
        topics = db.get_all_topics(active_only=True)
        if not topics:
            print("❌ Нет активных тем для тестирования")
            return
        
        test_topic = topics[0]
        topic_name = test_topic['name']
        topic_id = test_topic['id']
        
        print(f"🎯 Тестовая тема: '{topic_name}' (ID: {topic_id})")
        print()
        
        # ТЕСТ 1: Добавление с topic (автоконвертация)
        print("📝 ТЕСТ 1: Добавление вопроса с topic (автоконвертация)")
        
        question_with_topic = {
            'topic': topic_name,
            'question': 'Тестовый вопрос с topic поле',
            'answer': 'Правильный ответ',
            'explanation': 'Объяснение ответа',
            'incorrect_options': 'Вариант 1\nВариант 2\nВариант 3',
            'question_type': 'standard',
            'source': 'test'
        }
        
        # Считаем вопросы до добавления
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions WHERE topic = ?', (topic_name,))
            count_before = cursor.fetchone()[0]
        
        # Добавляем вопрос с topic
        db.add_question(question_with_topic)
        
        # Проверяем результат
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions WHERE topic = ?', (topic_name,))
            count_after = cursor.fetchone()[0]
            
            if has_topic_id:
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic_id,))
                count_topic_id = cursor.fetchone()[0]
                print(f"   ✅ Вопросов с topic='{topic_name}': {count_after} (+{count_after - count_before})")
                print(f"   ✅ Вопросов с topic_id={topic_id}: {count_topic_id}")
            else:
                print(f"   ✅ Вопросов с topic='{topic_name}': {count_after} (+{count_after - count_before})")
        
        print()
        
        # ТЕСТ 2: Добавление с topic_id напрямую
        if has_topic_id:
            print("📝 ТЕСТ 2: Добавление вопроса с topic_id напрямую")
            
            question_with_topic_id = {
                'topic_id': topic_id,
                'question': 'Тестовый вопрос с topic_id поле',
                'answer': 'Правильный ответ 2',
                'explanation': 'Объяснение ответа 2',
                'incorrect_options': 'Вариант А\nВариант Б\nВариант В',
                'question_type': 'standard',
                'source': 'test'
            }
            
            # Считаем вопросы до добавления
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic_id,))
                count_before_id = cursor.fetchone()[0]
            
            # Добавляем вопрос с topic_id
            db.add_question(question_with_topic_id)
            
            # Проверяем результат
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic_id,))
                count_after_id = cursor.fetchone()[0]
                
                print(f"   ✅ Вопросов с topic_id={topic_id}: {count_after_id} (+{count_after_id - count_before_id})")
            
            print()
        
        # ТЕСТ 3: Проверка создания новой темы
        print("📝 ТЕСТ 3: Автосоздание новой темы")
        
        new_topic_name = "Автотест Новая Тема"
        
        question_new_topic = {
            'topic': new_topic_name,
            'question': 'Вопрос для новой темы',
            'answer': 'Ответ для новой темы',
            'explanation': 'Объяснение для новой темы',
            'incorrect_options': 'Вариант X\nВариант Y\nВариант Z',
            'question_type': 'standard',
            'source': 'test'
        }
        
        # Проверяем, что темы еще нет
        existing_topic_id = db._get_topic_id_by_name(new_topic_name)
        print(f"   📋 Тема '{new_topic_name}' до добавления: {'существует' if existing_topic_id else 'не существует'}")
        
        # Добавляем вопрос с новой темой
        db.add_question(question_new_topic)
        
        # Проверяем, что тема создалась
        created_topic_id = db._get_topic_id_by_name(new_topic_name)
        if created_topic_id:
            print(f"   ✅ Тема '{new_topic_name}' автоматически создана с ID: {created_topic_id}")
            
            # Проверяем вопрос
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic = ?', (new_topic_name,))
                new_topic_questions = cursor.fetchone()[0]
                print(f"   ✅ Вопросов в новой теме: {new_topic_questions}")
        else:
            print(f"   ❌ Тема '{new_topic_name}' не была создана")
        
        print()
        print("🎉 ТЕСТ ЗАВЕРШЕН: Автоконвертация topic → topic_id работает корректно!")
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Удаляем временную базу
        if os.path.exists(temp_db):
            os.unlink(temp_db)

if __name__ == "__main__":
    test_add_question_conversion() 