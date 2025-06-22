#!/usr/bin/env python3
"""
Скрипт для инициализации суперадминистратора

Создает первого суперадминистратора в системе.
Запускается только один раз при первоначальной настройке.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv не обязателен

# Импортируем нашу базу данных
from db.repositories.admin_repository import AdminRepository

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        admin_repo = AdminRepository()
        # Пытаемся выполнить простой запрос
        result = await admin_repo._fetch_val_async("SELECT 1")
        return result == 1
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return False

async def init_superadmin():
    """Инициализация суперадминистратора"""
    print("🔧 Инициализация суперадминистратора...")
    
    # Проверяем подключение к БД
    if not await check_database_connection():
        print("\n❌ ОШИБКА: Нет подключения к базе данных!")
        print("\n🔧 РЕШЕНИЕ:")
        print("1. Проверьте переменные окружения SUPABASE_URL и SUPABASE_KEY")
        print("2. Убедитесь, что Supabase проект активен")
        print("3. Или создайте суперадмина вручную через Supabase Dashboard:")
        print("   - Откройте https://supabase.com/dashboard")
        print("   - Перейдите в SQL Editor")
        print("   - Выполните скрипт из файла supabase_create_superadmin.sql")
        return False
    
    try:
        admin_repo = AdminRepository()
        
        # Проверяем, есть ли уже суперадмин
        admins = await admin_repo._fetch_all_async(
            "SELECT user_id, username, full_name, is_super_admin FROM admins WHERE is_super_admin = true"
        )
        
        if admins:
            admin = admins[0]
            print(f"\n✅ Суперадмин уже существует:")
            print(f"  ID: {admin['user_id']}")
            print(f"  Username: @{admin['username']}")
            print(f"  Имя: {admin['full_name']}")
            return True
        
        print("Суперадмин не найден. Создаем нового...")
        
        # Получаем данные от пользователя
        while True:
            try:
                user_id = int(input("Введите Telegram user_id суперадмина: "))
                break
            except ValueError:
                print("❌ Введите корректный числовой ID")
        
        username = input("Введите username суперадмина (без @, можно оставить пустым): ").strip()
        if not username:
            username = f"superadmin_{user_id}"
        
        full_name = input("Введите ФИО суперадмина (можно оставить пустым): ").strip()
        if not full_name:
            full_name = f"Суперадмин {user_id}"
        
        # Создаем суперадмина
        query = """
            INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name,
                is_super_admin = EXCLUDED.is_super_admin
        """
        
        await admin_repo._execute_query_async(
            query, 
            (user_id, username, full_name, True, None)
        )
        
        # Проверяем, что админ действительно создан
        created_admin = await admin_repo._fetch_one_async(
            "SELECT user_id, username, full_name, is_super_admin FROM admins WHERE user_id = $1",
            (user_id,)
        )
        
        if created_admin and created_admin.get('is_super_admin'):
            print(f"\n✅ Суперадмин успешно создан!")
            print(f"  ID: {user_id}")
            print(f"  Username: @{username}")
            print(f"  ФИО: {full_name}")
            print(f"\nТеперь пользователь с ID {user_id} может использовать команду /admin в боте.")
            return True
        else:
            print(f"\n❌ Ошибка при создании суперадмина.")
            print(f"Создайте суперадмина вручную через Supabase Dashboard")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"Создайте суперадмина вручную через Supabase Dashboard")
        return False

async def main():
    """Главная асинхронная функция"""
    success = await init_superadmin()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1) 