#!/usr/bin/env python3
"""
Автоматический инициализатор приложения.

Проверяет, инициализирована ли база данных. Если нет, запускает
полную настройку: создание таблиц, наполнение темами и создание суперадмина.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь для корректного импорта
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_app_if_needed():
    """
    Проверяет, инициализирована ли БД (по наличию таблицы 'admins').
    Если нет, запускает все скрипты инициализации.
    """
    # Пропускаем, если не используется PostgreSQL (например, локально с SQLite)
    use_postgres = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'
    if not use_postgres:
        logger.info("Пропуск автоматической инициализации для SQLite. Используйте ручные скрипты.")
        return

    logger.info("Проверка необходимости инициализации приложения для PostgreSQL...")
    
    # Импорты должны быть здесь, чтобы sys.path успел обновиться
    from src.db.sync_connection_manager import SyncConnectionManager
    from src.init_database import main as init_db
    from src.init_topics import main as init_topics
    from src.init_superadmin import main as init_admin

    conn_manager = SyncConnectionManager()
    try:
        # Используем контекстный менеджер для получения соединения
        with conn_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Проверяем наличие таблицы 'admins' как индикатор инициализации
                cur.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables 
                       WHERE table_schema = 'public' AND table_name = 'admins'
                    );
                """)
                table_exists = cur.fetchone()[0]

        if not table_exists:
            logger.warning("База данных не инициализирована. Запуск полной автоматической настройки...")
            
            logger.info("Шаг 1/3: Создание таблиц базы данных...")
            if not init_db():
                raise RuntimeError("Не удалось создать таблицы базы данных.")
            logger.info("✅ Таблицы успешно созданы.")

            logger.info("Шаг 2/3: Наполнение базы данных темами...")
            if not init_topics():
                raise RuntimeError("Не удалось наполнить базу данных темами.")
            logger.info("✅ Темы успешно добавлены.")

            logger.info("Шаг 3/3: Создание суперадминистратора...")
            if not init_admin():
                logger.warning("Не удалось создать суперадмина. Возможно, не заданы переменные SUPERADMIN_ID.")
                logger.warning("Придется создать его вручную: python src/init_superadmin.py")
            else:
                logger.info("✅ Суперадминистратор успешно создан.")

            logger.info("🎉 Автоматическая инициализация приложения успешно завершена!")

        else:
            logger.info("База данных уже инициализирована. Пропуск настройки.")

    except Exception as e:
        logger.error(f"❌ Произошла ошибка во время процесса инициализации: {e}", exc_info=True)
        logger.error("Приложение может работать некорректно. Проверьте подключение к БД и переменные окружения.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    # Для локального тестирования скрипта
    env_path = root_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Для теста загружен .env файл: {env_path}")
    
    initialize_app_if_needed() 