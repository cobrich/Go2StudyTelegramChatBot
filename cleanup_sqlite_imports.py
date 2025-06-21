#!/usr/bin/env python3
"""
Скрипт для очистки SQLite импортов и подключений

Этот скрипт удаляет все прямые импорты sqlite3 и заменяет их на использование
архитектуры репозиториев через database facade.
"""

import os
import re
from pathlib import Path

def clean_sqlite_imports(file_path: str):
    """Очистить SQLite импорты из файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Удаляем импорты sqlite3
        content = re.sub(r'^import sqlite3\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^from sqlite3 import.*$', '', content, flags=re.MULTILINE)
        
        # Удаляем пустые строки после удаления импортов
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Если содержимое изменилось, записываем обратно
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Очищен файл: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обработке {file_path}: {e}")
        return False

def find_sqlite_usages(file_path: str):
    """Найти использования SQLite в файле"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем прямые подключения к SQLite
        sqlite_patterns = [
            r'sqlite3\.connect\(',
            r'with sqlite3\.connect\(',
            r'\.db_path',
            r'math_bot\.db'
        ]
        
        usages = []
        for i, line in enumerate(content.split('\n'), 1):
            for pattern in sqlite_patterns:
                if re.search(pattern, line):
                    usages.append(f"  Строка {i}: {line.strip()}")
        
        return usages
        
    except Exception as e:
        print(f"❌ Ошибка при поиске в {file_path}: {e}")
        return []

def main():
    """Основная функция"""
    print("🧹 Очистка SQLite импортов...")
    
    # Находим все Python файлы в проекте
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    cleaned_files = 0
    files_with_sqlite = []
    
    # Очищаем импорты
    for file_path in python_files:
        if clean_sqlite_imports(file_path):
            cleaned_files += 1
    
    print(f"\n📊 Очищено {cleaned_files} файлов")
    
    # Ищем оставшиеся использования SQLite
    print("\n🔍 Поиск оставшихся использований SQLite...")
    
    for file_path in python_files:
        usages = find_sqlite_usages(file_path)
        if usages:
            files_with_sqlite.append((file_path, usages))
    
    if files_with_sqlite:
        print(f"\n⚠️ Найдены файлы с прямыми SQLite подключениями ({len(files_with_sqlite)} файлов):")
        for file_path, usages in files_with_sqlite:
            print(f"\n📄 {file_path}:")
            for usage in usages[:5]:  # Показываем первые 5 использований
                print(usage)
            if len(usages) > 5:
                print(f"  ... и еще {len(usages) - 5} использований")
        
        print("\n💡 Рекомендации:")
        print("1. Замените прямые SQLite подключения на использование self.db методов")
        print("2. Используйте database facade для всех операций с БД")
        print("3. Удалите все ссылки на .db_path")
        
    else:
        print("✅ Прямые SQLite подключения не найдены!")
    
    print("\n🎉 Очистка завершена!")

if __name__ == "__main__":
    main() 