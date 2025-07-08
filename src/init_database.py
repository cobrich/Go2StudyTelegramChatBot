#!/usr/bin/env python3
"""
Скрипт для инициализации схемы базы данных с использованием SQLAlchemy.

Создает все таблицы на основе метаданных моделей.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
        
# Импортируем необходимые компоненты
from src.db.sync_connection_manager import get_sync_connection_manager
from src.db.models import DatabaseSchema

def init_database():
    """
    Основная функция для создания всех таблиц в базе данных.
    """
    logger.info("🔧 Инициализация схемы базы данных...")
    
    conn_manager = None
    try:
        # Получаем connection manager и его engine
        conn_manager = get_sync_connection_manager()
        engine = conn_manager.get_engine()
        
        logger.info("Проверка подключения к базе данных...")
        with engine.connect() as connection:
            logger.info("✅ Подключение к базе данных успешно установлено.")

        # Создаем все таблицы
        schema = DatabaseSchema(engine)
        logger.info("🏗️ Создание таблиц на основе метаданных моделей...")
        schema.create_all()
        
        logger.info("🎉 ИНИЦИАЛИЗАЦИЯ СХЕМЫ ЗАВЕРШЕНА УСПЕШНО!")
        logger.info("✅ Все таблицы, включая 'managed_messages', должны быть созданы.")
        return True

    except Exception as e:
        logger.error(f"❌ Произошла критическая ошибка при инициализации базы данных: {e}", exc_info=True)
        return False

def main():
    """Главная функция-обертка"""
    try:
        # Загружаем переменные окружения для локального запуска
        from dotenv import load_dotenv
        env_path = root_dir / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"✅ Загружен .env файл: {env_path}")
        else:
            logger.warning(f"⚠️ .env файл не найден: {env_path}")

        if init_database():
            return 0  # Успех
        else:
            return 1  # Ошибка

    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка в main: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 