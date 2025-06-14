#!/usr/bin/env python3
"""
Миграционный скрипт для удаления столбца phone_number из таблиц allowed_users и users.

Этот скрипт:
1. Создает резервные копии таблиц
2. Создает новые таблицы без столбца phone_number
3. Копирует данные из старых таблиц в новые
4. Удаляет старые таблицы и переименовывает новые
5. Восстанавливает индексы и ограничения
"""

import sqlite3
import os
import sys
from datetime import datetime

def backup_database(db_path: str) -> str:
    """Создает резервную копию базы данных."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    # Копируем файл базы данных
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"[LOG] Создана резервная копия: {backup_path}")
    return backup_path

def remove_phone_number_columns(db_path: str):
    """Удаляет столбец phone_number из таблиц allowed_users и users."""
    
    # Создаем резервную копию
    backup_path = backup_database(db_path)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("[LOG] Начинаем миграцию...")
            
            # === МИГРАЦИЯ ТАБЛИЦЫ allowed_users ===
            print("[LOG] Миграция таблицы allowed_users...")
            
            # Проверяем, есть ли столбец phone_number в allowed_users
            cursor.execute("PRAGMA table_info(allowed_users)")
            allowed_users_columns = [column[1] for column in cursor.fetchall()]
            
            if 'phone_number' in allowed_users_columns:
                print("[LOG] Найден столбец phone_number в allowed_users, удаляем...")
                
                # Создаем новую таблицу без phone_number
                cursor.execute('''
                    CREATE TABLE allowed_users_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        full_name TEXT,
                        grade INTEGER,
                        added_by INTEGER,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        user_id INTEGER,
                        language TEXT DEFAULT "ru",
                        FOREIGN KEY (added_by) REFERENCES admins(user_id)
                    )
                ''')
                
                # Копируем данные (исключая phone_number)
                cursor.execute('''
                    INSERT INTO allowed_users_new 
                    (id, username, full_name, grade, added_by, added_at, is_active, user_id, language)
                    SELECT id, username, full_name, grade, added_by, added_at, is_active, user_id, language
                    FROM allowed_users
                ''')
                
                # Удаляем старую таблицу и переименовываем новую
                cursor.execute('DROP TABLE allowed_users')
                cursor.execute('ALTER TABLE allowed_users_new RENAME TO allowed_users')
                
                # Восстанавливаем индексы
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_allowed_users_user_id ON allowed_users(user_id) WHERE user_id IS NOT NULL')
                
                print("[LOG] ✅ Столбец phone_number удален из allowed_users")
            else:
                print("[LOG] ✅ Столбец phone_number отсутствует в allowed_users")
            
            # === МИГРАЦИЯ ТАБЛИЦЫ users ===
            print("[LOG] Миграция таблицы users...")
            
            # Проверяем, есть ли столбец phone_number в users
            cursor.execute("PRAGMA table_info(users)")
            users_columns = [column[1] for column in cursor.fetchall()]
            
            if 'phone_number' in users_columns:
                print("[LOG] Найден столбец phone_number в users, удаляем...")
                
                # Создаем новую таблицу без phone_number
                cursor.execute('''
                    CREATE TABLE users_new (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        full_name TEXT,
                        grade INTEGER,
                        language TEXT DEFAULT 'ru',
                        is_active BOOLEAN DEFAULT 0,
                        current_topic TEXT,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Копируем данные (исключая phone_number)
                cursor.execute('''
                    INSERT INTO users_new 
                    (user_id, username, full_name, grade, language, is_active, current_topic, last_activity)
                    SELECT user_id, username, full_name, grade, language, is_active, current_topic, last_activity
                    FROM users
                ''')
                
                # Удаляем старую таблицу и переименовываем новую
                cursor.execute('DROP TABLE users')
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                print("[LOG] ✅ Столбец phone_number удален из users")
            else:
                print("[LOG] ✅ Столбец phone_number отсутствует в users")
            
            conn.commit()
            print("[LOG] ✅ Миграция завершена успешно!")
            
            # Проверяем результат
            cursor.execute("PRAGMA table_info(allowed_users)")
            new_allowed_users_columns = [column[1] for column in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(users)")
            new_users_columns = [column[1] for column in cursor.fetchall()]
            
            print(f"[LOG] Столбцы allowed_users: {new_allowed_users_columns}")
            print(f"[LOG] Столбцы users: {new_users_columns}")
            
            # Проверяем количество записей
            cursor.execute("SELECT COUNT(*) FROM allowed_users")
            allowed_users_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]
            
            print(f"[LOG] Записей в allowed_users: {allowed_users_count}")
            print(f"[LOG] Записей в users: {users_count}")
            
    except Exception as e:
        print(f"[ERROR] Ошибка миграции: {e}")
        print(f"[ERROR] Восстановите базу данных из резервной копии: {backup_path}")
        raise

def main():
    # Определяем путь к базе данных
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # По умолчанию ищем в корне проекта
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "math_bot.db")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] База данных не найдена: {db_path}")
        sys.exit(1)
    
    print(f"[LOG] Используется база данных: {db_path}")
    
    # Подтверждение от пользователя
    response = input("Вы уверены, что хотите удалить столбцы phone_number? (да/нет): ")
    if response.lower() not in ['да', 'yes', 'y']:
        print("[LOG] Миграция отменена пользователем")
        sys.exit(0)
    
    remove_phone_number_columns(db_path)
    print("[LOG] 🎉 Миграция завершена! Столбцы phone_number удалены из обеих таблиц.")

if __name__ == "__main__":
    main() 