#!/usr/bin/env python3
"""
Скрипт для инициализации тем и подтем в базе данных

Создает полную иерархию тем из constants.py в базе данных.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения из корневой директории проекта
try:
    from dotenv import load_dotenv
    # Ищем .env файл в корневой директории проекта (на уровень выше src)
    env_path = root_dir.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"✅ Загружен .env файл: {env_path}")
    else:
        print(f"⚠️ .env файл не найден: {env_path}")
except ImportError:
    print("⚠️ dotenv не установлен - переменные окружения не загружены")

# Импортируем нашу базу данных и константы
from db.repositories.admin_repository import AdminRepository
from config.constants import TOPIC_HIERARCHY

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        admin_repo = AdminRepository()
        result = await admin_repo._fetch_val_async("SELECT 1")
        return result == 1
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return False

async def init_topics():
    """Инициализация полной структуры тем"""
    print("🔧 Инициализация структуры тем...")
    
    # Проверяем подключение к БД
    if not await check_database_connection():
        print("\n❌ ОШИБКА: Нет подключения к базе данных!")
        return False
    
    try:
        admin_repo = AdminRepository()
        
        print(f"\n📊 Найдено {len(TOPIC_HIERARCHY)} основных разделов:")
        for main_topic in TOPIC_HIERARCHY.keys():
            print(f"  • {main_topic}")
        
        total_subtopics = sum(len(subtopics) for subtopics in TOPIC_HIERARCHY.values())
        print(f"\n📝 Всего подтем: {total_subtopics}")
        
        # Создаем основные темы и подтемы для русского и казахского языков
        languages = ['ru', 'kk']
        
        for language in languages:
            print(f"\n🌐 Обрабатываем язык: {'Русский' if language == 'ru' else 'Казахский'}")
            
            for main_topic, subtopics in TOPIC_HIERARCHY.items():
                # Создаем основную тему
                main_topic_query = """
                    INSERT INTO main_topics (topic_name, language, is_active)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (topic_name, language) DO UPDATE SET
                        is_active = EXCLUDED.is_active
                    RETURNING id
                """
                
                main_topic_result = await admin_repo._fetch_one_async(
                    main_topic_query, 
                    (main_topic, language, True)
                )
                
                if main_topic_result:
                    main_topic_id = main_topic_result['id']
                    print(f"  ✅ Основная тема: {main_topic} (ID: {main_topic_id})")
                    
                    # Создаем подтемы
                    for subtopic in subtopics:
                        subtopic_query = """
                            INSERT INTO subtopics (subtopic_name, main_topic_id, is_active)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (subtopic_name, main_topic_id) DO UPDATE SET
                                is_active = EXCLUDED.is_active
                        """
                        
                        await admin_repo._execute_query_async(
                            subtopic_query,
                            (subtopic, main_topic_id, True)
                        )
                        print(f"    • {subtopic}")
                else:
                    print(f"  ❌ Ошибка создания основной темы: {main_topic}")
        
        # Проверяем результаты
        print(f"\n📊 ПРОВЕРКА РЕЗУЛЬТАТОВ:")
        
        # Считаем основные темы
        main_topics_count = await admin_repo._fetch_val_async(
            "SELECT COUNT(*) FROM main_topics WHERE is_active = true"
        )
        print(f"  Основных тем: {main_topics_count}")
        
        # Считаем подтемы
        subtopics_count = await admin_repo._fetch_val_async(
            "SELECT COUNT(*) FROM subtopics WHERE is_active = true"
        )
        print(f"  Подтем: {subtopics_count}")
        
        # Показываем структуру
        structure_query = """
            SELECT 
                mt.topic_name as main_topic,
                mt.language,
                COUNT(st.id) as subtopics_count
            FROM main_topics mt
            LEFT JOIN subtopics st ON mt.id = st.main_topic_id AND st.is_active = true
            WHERE mt.is_active = true
            GROUP BY mt.id, mt.topic_name, mt.language
            ORDER BY mt.language, mt.topic_name
        """
        
        structure = await admin_repo._fetch_all_async(structure_query)
        
        print(f"\n📋 СТРУКТУРА ТЕМ:")
        current_language = None
        for row in structure:
            if row['language'] != current_language:
                current_language = row['language']
                lang_name = 'Русский' if current_language == 'ru' else 'Казахский'
                print(f"\n🌐 {lang_name}:")
            
            print(f"  📚 {row['main_topic']} ({row['subtopics_count']} подтем)")
        
        print(f"\n✅ Инициализация тем завершена успешно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

async def main():
    """Главная асинхронная функция"""
    try:
        success = await init_topics()
        return success
    finally:
        # Корректно закрываем пул соединений
        try:
            from db.connection_manager import get_connection_manager
            connection_manager = get_connection_manager()
            await connection_manager.close_pool()
            print("\n🔧 Соединения с БД корректно закрыты")
        except Exception as e:
            print(f"\n⚠️ Ошибка при закрытии соединений: {e}")

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