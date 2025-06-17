#!/usr/bin/env python3
"""
Тестовый скрипт для проверки миграции topic_id в таблице questions.
Этот скрипт проверяет работу миграции без влияния на основную базу данных.
"""

import os
import sys
import sqlite3
import tempfile
import shutil

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import Database

def create_test_db_with_old_structure(db_path):
    """Создает тестовую БД со старой структурой"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Создаем таблицы в старом формате
        cursor.execute('''
            CREATE TABLE main_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                language TEXT DEFAULT "ru",
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE subtopics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                main_topic_id INTEGER NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (main_topic_id) REFERENCES main_topics(id)
            )
        ''')
        
        # Таблица questions БЕЗ topic_id (старый формат)
        cursor.execute('''
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                explanation TEXT,
                incorrect_options TEXT,
                question_type TEXT DEFAULT 'standard',
                source TEXT DEFAULT 'db',
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем тестовые данные
        # Основная тема
        cursor.execute("INSERT INTO main_topics (name, language) VALUES ('Математика', 'ru')")
        main_topic_id = cursor.lastrowid
        
        # Подтемы
        cursor.execute("INSERT INTO subtopics (name, main_topic_id) VALUES ('Алгебра', ?)", (main_topic_id,))
        cursor.execute("INSERT INTO subtopics (name, main_topic_id) VALUES ('Геометрия', ?)", (main_topic_id,))
        cursor.execute("INSERT INTO subtopics (name, main_topic_id) VALUES ('Арифметика', ?)", (main_topic_id,))
        
        # Вопросы (со старой структурой - только topic по названию)
        test_questions = [
            ("Алгебра", "Что такое x в уравнении x + 2 = 5?", "3", "x = 5 - 2 = 3"),
            ("Алгебра", "Решите уравнение 2x = 10", "5", "x = 10 / 2 = 5"),
            ("Геометрия", "Сколько углов у треугольника?", "3", "У треугольника всегда 3 угла"),
            ("Арифметика", "Сколько будет 2 + 2?", "4", "2 + 2 = 4"),
            ("Несуществующая тема", "Тестовый вопрос", "Ответ", "Объяснение"), # Орфанная тема
        ]
        
        for topic, question, answer, explanation in test_questions:
            cursor.execute('''
                INSERT INTO questions (topic, question, answer, explanation, source)
                VALUES (?, ?, ?, ?, 'db')
            ''', (topic, question, answer, explanation))
        
        conn.commit()
        print(f"✅ Создана тестовая БД с {len(test_questions)} вопросами")

def check_migration_results(db_path):
    """Проверяет результаты миграции"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы questions
        cursor.execute("PRAGMA table_info(questions)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Колонки таблицы questions: {columns}")
        
        # Проверяем наличие topic_id
        if 'topic_id' in columns:
            print("✅ Колонка topic_id успешно добавлена")
        else:
            print("❌ Колонка topic_id не найдена")
            return False
        
        # Проверяем заполнение topic_id
        cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id IS NOT NULL')
        filled_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM questions')
        total_count = cursor.fetchone()[0]
        
        print(f"📊 Вопросов с topic_id: {filled_count}/{total_count}")
        
        # Проверяем связь topic_id с subtopics
        cursor.execute('''
            SELECT q.id, q.topic, q.topic_id, s.name as subtopic_name
            FROM questions q
            LEFT JOIN subtopics s ON q.topic_id = s.id
            ORDER BY q.id
        ''')
        
        results = cursor.fetchall()
        print("\n📝 Детали миграции:")
        for qid, old_topic, topic_id, subtopic_name in results:
            status = "✅" if topic_id and subtopic_name else "❌"
            print(f"  {status} Вопрос {qid}: '{old_topic}' -> topic_id={topic_id} ({subtopic_name})")
        
        # Проверяем созданные подтемы
        cursor.execute('SELECT id, name, description FROM subtopics WHERE description LIKE "%Auto-created%"')
        auto_created = cursor.fetchall()
        if auto_created:
            print("\n🔧 Автоматически созданные подтемы:")
            for sid, name, desc in auto_created:
                print(f"  • {name} (ID: {sid})")
        
        return True

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование миграции topic_id\n")
    
    # Создаем временную директорию
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = os.path.join(temp_dir, "test_migration.db")
        
        # Шаг 1: Создаем БД со старой структурой
        print("1️⃣ Создание тестовой БД со старой структурой...")
        create_test_db_with_old_structure(test_db_path)
        
        # Шаг 2: Проверяем структуру до миграции
        print("\n2️⃣ Проверка структуры до миграции...")
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(questions)")
            columns_before = [column[1] for column in cursor.fetchall()]
            print(f"📋 Колонки до миграции: {columns_before}")
            
            if 'topic_id' in columns_before:
                print("⚠️ topic_id уже существует - тест некорректен")
                return
        
        # Шаг 3: Инициализируем Database (это запустит миграцию)
        print("\n3️⃣ Запуск миграции через Database()...")
        try:
            db = Database(test_db_path)
            print("✅ Миграция завершена без ошибок")
        except Exception as e:
            print(f"❌ Ошибка во время миграции: {e}")
            return
        
        # Шаг 4: Проверяем результаты
        print("\n4️⃣ Проверка результатов миграции...")
        success = check_migration_results(test_db_path)
        
        if success:
            print("\n🎉 Миграция topic_id прошла успешно!")
        else:
            print("\n💥 Миграция topic_id завершилась с ошибками!")

if __name__ == "__main__":
    main() 