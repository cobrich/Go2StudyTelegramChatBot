#!/usr/bin/env python3
"""
Скрипт для инициализации суперадминистратора

Создает первого суперадминистратора в системе.
Запускается только один раз при первоначальной настройке.
"""

import os
import sys
import logging

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Импортируем нашу базу данных
from db import get_database

from db.repositories.admin_repository import AdminRepository

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        admin_repo = AdminRepository()
        # Пытаемся получить статистику - это проверит реальное подключение
        stats = admin_repo.get_admin_activity_stats()
        
        # Если получили fallback значения - значит БД недоступна
        if stats == {'total_admins': 0, 'super_admins': 0, 'regular_admins': 0, 'recent_additions': 0}:
            # Проверяем, действительно ли это fallback или просто нет админов
            # Пытаемся выполнить простой запрос
            try:
                admin_repo.fetch_val("SELECT 1")
                return True  # Запрос выполнился, БД доступна
            except:
                return False  # Запрос не выполнился, БД недоступна
        
        return True
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return False

def init_superadmin():
    """Инициализация суперадминистратора"""
    print("🔧 Инициализация суперадминистратора...")
    
    # Проверяем подключение к БД
    if not check_database_connection():
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
        admins = admin_repo.get_all_admins()
        if isinstance(admins, list) and len(admins) > 0:
            for admin in admins:
                if admin.get('is_super'):
                    print(f"\n✅ Суперадмин уже существует:")
                    print(f"  ID: {admin['user_id']}")
                    print(f"  Username: @{admin['username']}")
                    print(f"  Имя: {admin['name']}")
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
        success = admin_repo.add_admin(
            user_id=user_id,
            username=username,
            full_name=full_name,
            is_super=True,
            added_by=None
        )
        
        if success:
            # Проверяем, что админ действительно создан
            created_admin = admin_repo.get_admin_info(user_id)
            if created_admin and created_admin.get('is_super_admin'):
                print(f"\n✅ Суперадмин успешно создан!")
                print(f"  ID: {user_id}")
                print(f"  Username: @{username}")
                print(f"  ФИО: {full_name}")
                print(f"\nТеперь пользователь с ID {user_id} может использовать команду /admin в боте.")
                return True
            else:
                print(f"\n⚠️ Суперадмин создан в fallback режиме (БД недоступна)")
                print(f"Создайте суперадмина вручную через Supabase Dashboard")
                return False
        else:
            print(f"\n❌ Ошибка при создании суперадмина.")
            print(f"Создайте суперадмина вручную через Supabase Dashboard")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"Создайте суперадмина вручную через Supabase Dashboard")
        return False

if __name__ == "__main__":
    success = init_superadmin()
    sys.exit(0 if success else 1) 