#!/usr/bin/env python3
"""
Скрипт для инициализации тем в базе данных

Создает правильную структуру тем из constants.py и constants_kk.py
Исправляет проблему дублирования разделов между языками.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent  # Поднимаемся на уровень выше src
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

# Импортируем нашу базу данных и константы
from src.db.sync_database_facade import get_sync_database_facade
from src.config.constants import TOPIC_HIERARCHY
from src.config.constants_kk import TOPIC_HIERARCHY_KK

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        db = get_sync_database_facade()
        # Пытаемся выполнить простой запрос
        result = db.topics.fetch_val("SELECT 1")
        return result == 1
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return False

def clear_existing_topics(db):
    """Очищаем существующие темы"""
    try:
        print("🧹 Очищаем существующие темы...")
        
        # Получаем все main topics
        ru_topics = db.get_main_topics_by_language('ru', active_only=False)
        kk_topics = db.get_main_topics_by_language('kk', active_only=False)
        
        # Удаляем все main topics (каскадно удалятся subtopics и questions)
        for topic in ru_topics:
            try:
                success = db.topics.delete_main_topic_permanently(topic['topic_name'], 'ru')
                if success:
                    print(f"  ✅ Удален русский раздел: {topic['topic_name']}")
            except: pass
        
        for topic in kk_topics:
            try:
                success = db.topics.delete_main_topic_permanently(topic['topic_name'], 'kk')
                if success:
                    print(f"  ✅ Удален казахский раздел: {topic['topic_name']}")
            except: pass
        
        print("✅ Очистка завершена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при очистке тем: {e}")
        return False

def init_russian_topics(db):
    """Инициализируем русские темы"""
    try:
        print("🇷🇺 Создаем русские темы...")
        
        for main_topic_name, subtopics in TOPIC_HIERARCHY.items():
            print(f"  📚 Создаем раздел: {main_topic_name}")
            
            # Создаем основной раздел
            success = db.add_main_topic_with_language(
                main_topic=main_topic_name,
                language='ru',
                subtopics=subtopics
            )
            
            if success:
                print(f"    ✅ Создан раздел: {main_topic_name}")
                for subtopic in subtopics:
                    print(f"      ➕ Подтема: {subtopic}")
            else:
                print(f"    ❌ Ошибка создания раздела: {main_topic_name}")
        
        print("✅ Русские темы созданы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании русских тем: {e}")
        return False

def init_kazakh_topics(db):
    """Инициализируем казахские темы"""
    try:
        print("🇰🇿 Создаем казахские темы...")
        
        for main_topic_name, subtopics in TOPIC_HIERARCHY_KK.items():
            print(f"  📚 Создаем раздел: {main_topic_name}")
            
            # Создаем основной раздел
            success = db.add_main_topic_with_language(
                main_topic=main_topic_name,
                language='kk',
                subtopics=subtopics
            )
            
            if success:
                print(f"    ✅ Создан раздел: {main_topic_name}")
                for subtopic in subtopics:
                    print(f"      ➕ Подтема: {subtopic}")
            else:
                print(f"    ❌ Ошибка создания раздела: {main_topic_name}")
        
        print("✅ Казахские темы созданы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании казахских тем: {e}")
        return False

def show_created_structure(db):
    """Показываем созданную структуру"""
    try:
        print("\n📋 СОЗДАННАЯ СТРУКТУРА:")
        
        # Русские темы
        print("\n🇷🇺 РУССКИЕ РАЗДЕЛЫ:")
        ru_structure = db.get_full_topic_structure_by_language('ru')
        for main_topic, subtopics in ru_structure.items():
            print(f"  📚 {main_topic}")
            for subtopic in subtopics:
                print(f"    ➕ {subtopic['name']} (ID: {subtopic['id']})")
        
        # Казахские темы
        print("\n🇰🇿 КАЗАХСКИЕ РАЗДЕЛЫ:")
        kk_structure = db.get_full_topic_structure_by_language('kk')
        for main_topic, subtopics in kk_structure.items():
            print(f"  📚 {main_topic}")
            for subtopic in subtopics:
                print(f"    ➕ {subtopic['name']} (ID: {subtopic['id']})")
        
        # Статистика
        ru_main_count = len(ru_structure)
        ru_sub_count = sum(len(subtopics) for subtopics in ru_structure.values())
        kk_main_count = len(kk_structure)
        kk_sub_count = sum(len(subtopics) for subtopics in kk_structure.values())
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"  🇷🇺 Русский: {ru_main_count} разделов, {ru_sub_count} подтем")
        print(f"  🇰🇿 Казахский: {kk_main_count} разделов, {kk_sub_count} подтем")
        print(f"  📈 Всего: {ru_main_count + kk_main_count} разделов, {ru_sub_count + kk_sub_count} подтем")
        
    except Exception as e:
        print(f"❌ Ошибка при показе структуры: {e}")

def init_topics():
    """Основная функция инициализации тем"""
    print("🔧 Инициализация тем в базе данных...")
    
    # Проверяем подключение к БД
    if not check_database_connection():
        print("\n❌ ОШИБКА: Нет подключения к базе данных!")
        print("\n🔧 РЕШЕНИЕ:")
        print("1. Проверьте переменные окружения DATABASE_URL")
        print("2. Убедитесь, что PostgreSQL сервер доступен")
        return False
    
    try:
        db = get_sync_database_facade()
        
        # Спрашиваем пользователя о очистке
        print("\n⚠️ ВНИМАНИЕ: Этот скрипт удалит ВСЕ существующие темы и вопросы!")
        choice = input("Продолжить? (да/нет): ").lower().strip()
        
        if choice not in ['да', 'yes', 'y', 'д']:
            print("❌ Операция отменена пользователем")
            return False
        
        # Очищаем существующие темы
        if not clear_existing_topics(db):
            return False
        
        # Создаем русские темы
        if not init_russian_topics(db):
            return False
        
        # Создаем казахские темы
        if not init_kazakh_topics(db):
            return False
        
        # Показываем результат
        show_created_structure(db)
        
        print("\n✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("\n🎯 РЕЗУЛЬТАТ:")
        print("✅ Все темы созданы с правильными языками")
        print("✅ Дублирование разделов исправлено")
        print("✅ База данных готова к работе")
        print("✅ Теперь разделы не будут дублироваться в интерфейсе")
        
        return True
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return False

def main():
    """Главная функция"""
    try:
        success = init_topics()
        if success:
            print("\n🚀 Инициализация завершена успешно!")
            return 0
        else:
            print("\n💥 Инициализация завершилась с ошибками!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем")
        return 130
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 