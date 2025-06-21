#!/usr/bin/env python3
"""
Скрипт для инициализации суперадминистратора

Создает первого суперадминистратора в системе.
Запускается только один раз при первоначальной настройке.
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Импортируем нашу базу данных
from src.db import get_database

def init_superadmin():
    """Инициализация суперадминистратора"""
    print("🔧 Инициализация суперадминистратора...")
    
    # Подключаемся к базе данных
    db = get_database()
    
    # Проверяем, есть ли уже суперадмин
    admins = db.get_all_admins()
    super_admins = [admin for admin in admins if admin['is_super_admin']]
    
    if super_admins:
        print("Суперадмин уже существует:")
        for admin in super_admins:
            print(f"  ID: {admin['user_id']}")
            print(f"  Username: @{admin['username'] or 'не указан'}")
            print(f"  ФИО: {admin['full_name'] or 'не указано'}")
        print("\nЕсли вы хотите добавить еще одного суперадмина, используйте админ-панель.")
        return
    
    print("Суперадмин не найден. Создаем нового...")
    
    # Запрашиваем данные суперадмина
    while True:
        try:
            user_id = int(input("Введите Telegram user_id суперадмина: "))
            break
        except ValueError:
            print("Ошибка: введите корректный числовой ID")
    
    username = input("Введите username суперадмина (без @, можно оставить пустым): ").strip()
    if not username:
        username = "superadmin"
    
    full_name = input("Введите ФИО суперадмина (можно оставить пустым): ").strip()
    if not full_name:
        full_name = "Суперадминистратор"
    
    # Создаем суперадмина
    success = db.add_admin(user_id, username, full_name, is_super=True, added_by=None)
    
    if success:
        print(f"\n✅ Суперадмин успешно создан!")
        print(f"  ID: {user_id}")
        print(f"  Username: @{username}")
        print(f"  ФИО: {full_name}")
        print(f"\nТеперь пользователь с ID {user_id} может использовать команду /admin в боте.")
    else:
        print(f"\n❌ Ошибка при создании суперадмина. Возможно, пользователь с ID {user_id} уже является админом.")

if __name__ == "__main__":
    init_superadmin() 