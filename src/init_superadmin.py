#!/usr/bin/env python3
"""
Скрипт для инициализации суперадминистратора

Создает первого суперадминистратора в системе.
Может работать интерактивно или автоматически через переменные окружения.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    env_path = root_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"✅ Загружен .env файл: {env_path}")
    else:
        print(f"⚠️ .env файл не найден: {env_path}")
except ImportError:
    print("⚠️ dotenv не установлен - переменные окружения не загружены")

# Импортируем нашу базу данных
from src.db.sync_database_facade import get_sync_database_facade

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        db = get_sync_database_facade()
        # Пытаемся выполнить простой запрос через админ репозиторий
        admins = db.get_all_admins()
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
        print("1. Проверьте переменные окружения DATABASE_URL")
        print("2. Убедитесь, что PostgreSQL сервер доступен")
        print("3. Запустите сначала: python src/init_database.py")
        return False
    
    try:
        db = get_sync_database_facade()
        
        # Проверяем, есть ли уже суперадмин
        admins = db.get_all_admins()
        super_admins = [admin for admin in admins if admin.get('is_super_admin')]
        
        if super_admins:
            admin = super_admins[0]
            print(f"\n✅ Суперадмин уже существует:")
            print(f"  ID: {admin['user_id']}")
            print(f"  Username: @{admin.get('username', 'Не указан')}")
            print(f"  Имя: {admin.get('full_name', 'Не указано')}")
            return True
        
        print("Суперадмин не найден. Создаем нового...")
        
        # Пытаемся получить данные из переменных окружения
        superadmin_id_env = os.getenv('SUPERADMIN_ID')
        superadmin_username_env = os.getenv('SUPERADMIN_USERNAME')
        superadmin_fullname_env = os.getenv('SUPERADMIN_FIO')

        if superadmin_id_env:
            print("Найдены переменные окружения для суперадмина. Используем их.")
            try:
                user_id = int(superadmin_id_env)
                username = superadmin_username_env or f"superadmin_{user_id}"
                full_name = superadmin_fullname_env or f"Суперадмин {user_id}"
            except (ValueError, TypeError):
                print(f"❌ Неверный формат SUPERADMIN_ID: '{superadmin_id_env}'. Должно быть число.")
                return False
        else:
            print("Переменные окружения не найдены. Запрашиваем данные интерактивно.")
            # Получаем данные от пользователя
            while True:
                try:
                    user_id_input = input("Введите Telegram user_id суперадмина: ")
                    if not user_id_input:
                        print("❌ ID не может быть пустым.")
                        continue
                    user_id = int(user_id_input)
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
        success = db.add_admin(
            user_id=user_id,
            username=username,
            full_name=full_name,
            is_super_admin=True,
            created_by=None
        )
        
        if not success:
            print(f"\n❌ Ошибка при создании суперадмина.")
            return False
        
        # Проверяем, что админ действительно создан
        created_admin = db.get_admin_by_id(user_id)
        
        if created_admin and created_admin.get('is_super_admin'):
            print(f"\n✅ Суперадмин успешно создан!")
            print(f"  ID: {user_id}")
            print(f"  Username: @{username}")
            print(f"  ФИО: {full_name}")
            print(f"\nТеперь пользователь с ID {user_id} может использовать команду /admin в боте.")
            return True
        else:
            print(f"\n❌ Ошибка при создании суперадмина.")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

def main():
    """Главная функция"""
    try:
        success = init_superadmin()
        if success:
            print("\n🚀 Инициализация суперадмина завершена успешно!")
        else:
            print("\n❌ Инициализация суперадмина не удалась!")
        return success
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1) 