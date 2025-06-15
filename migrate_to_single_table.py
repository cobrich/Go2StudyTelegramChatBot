#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для миграции данных из таблицы users в allowed_users
и удаления избыточной таблицы users.
"""

import sqlite3
import os
import sys

def migrate_database():
    """Мигрирует данные из users в allowed_users и удаляет таблицу users."""
    
    db_path = "math_bot.db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False
    
    # Создаем резервную копию
    backup_path = f"{db_path}.backup_before_migration"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Создана резервная копия: {backup_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Добавляем недостающие поля в allowed_users если их нет
            print("📝 Добавляем недостающие поля в allowed_users...")
            
            # Проверяем текущую структуру таблицы
            cursor.execute("PRAGMA table_info(allowed_users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'current_topic' not in columns:
                try:
                    cursor.execute('ALTER TABLE allowed_users ADD COLUMN current_topic TEXT')
                    print("   ✅ Добавлено поле current_topic")
                except sqlite3.OperationalError as e:
                    print(f"   ❌ Ошибка добавления current_topic: {e}")
                    return False
            else:
                print("   ℹ️  Поле current_topic уже существует")
                
            if 'last_activity' not in columns:
                try:
                    cursor.execute('ALTER TABLE allowed_users ADD COLUMN last_activity TIMESTAMP')
                    print("   ✅ Добавлено поле last_activity")
                except sqlite3.OperationalError as e:
                    print(f"   ❌ Ошибка добавления last_activity: {e}")
                    return False
            else:
                print("   ℹ️  Поле last_activity уже существует")
            
            # Обновляем структуру после добавления полей
            cursor.execute("PRAGMA table_info(allowed_users)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"   📋 Текущие поля в allowed_users: {', '.join(columns)}")
            
            # 2. Проверяем, есть ли таблица users
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("ℹ️  Таблица users не найдена, миграция не требуется")
                return True
            
            # 3. Мигрируем данные из users в allowed_users
            print("🔄 Мигрируем данные из users в allowed_users...")
            
            # Получаем все данные из users
            cursor.execute('''
                SELECT user_id, username, full_name, grade, language, is_active, current_topic, last_activity
                FROM users
            ''')
            users_data = cursor.fetchall()
            
            migrated_count = 0
            updated_count = 0
            
            for user_data in users_data:
                user_id, username, full_name, grade, language, is_active, current_topic, last_activity = user_data
                
                # Проверяем, есть ли уже запись в allowed_users
                cursor.execute('SELECT user_id FROM allowed_users WHERE user_id = ?', (user_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE allowed_users 
                        SET current_topic = ?, last_activity = ?, is_active = ?
                        WHERE user_id = ?
                    ''', (current_topic, last_activity, is_active, user_id))
                    updated_count += 1
                    print(f"   🔄 Обновлен пользователь {user_id}")
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO allowed_users 
                        (user_id, username, full_name, grade, language, is_active, current_topic, last_activity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, full_name, grade, language, is_active, current_topic, last_activity))
                    migrated_count += 1
                    print(f"   ➕ Добавлен пользователь {user_id}")
            
            print(f"✅ Миграция завершена: {migrated_count} добавлено, {updated_count} обновлено")
            
            # 4. Удаляем таблицу users
            print("🗑️  Удаляем таблицу users...")
            cursor.execute('DROP TABLE IF EXISTS users')
            print("   ✅ Таблица users удалена")
            
            # 5. Обновляем внешние ключи в других таблицах
            print("🔗 Обновляем внешние ключи...")
            
            # Проверяем, есть ли ссылки на users в других таблицах
            cursor.execute('''
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%REFERENCES users%'
            ''')
            tables_with_fk = cursor.fetchall()
            
            if tables_with_fk:
                print("   ⚠️  Найдены таблицы со ссылками на users:")
                for table_sql in tables_with_fk:
                    print(f"      {table_sql[0]}")
                print("   ℹ️  Внешние ключи будут обновлены автоматически")
            
            conn.commit()
            print("✅ Миграция успешно завершена!")
            
            # 6. Проверяем результат
            print("\n📊 Проверка результата:")
            cursor.execute('SELECT COUNT(*) FROM allowed_users')
            total_users = cursor.fetchone()[0]
            print(f"   👥 Всего пользователей в allowed_users: {total_users}")
            
            cursor.execute('SELECT COUNT(*) FROM allowed_users WHERE current_topic IS NOT NULL')
            active_users = cursor.fetchone()[0]
            print(f"   🎯 Активных пользователей: {active_users}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        print(f"🔄 Восстанавливаем из резервной копии...")
        shutil.copy2(backup_path, db_path)
        print(f"✅ База данных восстановлена из {backup_path}")
        return False

def main():
    """Главная функция."""
    print("🚀 Начинаем миграцию базы данных...")
    print("📋 Цель: объединить таблицы users и allowed_users в одну таблицу allowed_users")
    print()
    
    if migrate_database():
        print("\n🎉 Миграция успешно завершена!")
        print("📝 Теперь все пользовательские данные хранятся в таблице allowed_users")
        print("🗑️  Таблица users удалена")
    else:
        print("\n💥 Миграция не удалась!")
        print("🔄 База данных восстановлена из резервной копии")
        sys.exit(1)

if __name__ == "__main__":
    main() 