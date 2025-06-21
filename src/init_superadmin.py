#!/usr/bin/env python3
"""
Скрипт для инициализации суперадмина.
Запустите этот скрипт один раз для создания первого суперадмина.
"""

import sys
import os
import logging

from datetime import datetime
import hashlib
import secrets
import asyncio
from typing import Optional

# Добавляем корневую директорию проекта в sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.db import Database

def main():
    print("=== Инициализация суперадмина ===")
    
    db = Database()
    
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
    main() 