import os
from typing import Union

# Импорты для разных типов баз данных
from src.services.database import Database, get_database_instance
from src.services.supabase_database import SupabaseDatabase, get_supabase_database_instance

class DatabaseConfig:
    """Конфигурация базы данных с поддержкой SQLite и Supabase"""
    
    # Типы баз данных
    SQLITE = "sqlite"
    SUPABASE = "supabase"
    
    def __init__(self):
        # Определяем тип БД из переменной окружения
        self.db_type = os.getenv('DATABASE_TYPE', self.SQLITE).lower()
        
        # Проверяем валидность типа БД
        if self.db_type not in [self.SQLITE, self.SUPABASE]:
            raise ValueError(f"Неподдерживаемый тип БД: {self.db_type}. Доступны: {self.SQLITE}, {self.SUPABASE}")
        
        print(f"[DATABASE_CONFIG] Выбран тип БД: {self.db_type.upper()}")

    def get_database_instance(self) -> Union[Database, SupabaseDatabase]:
        """Получить экземпляр базы данных в зависимости от конфигурации"""
        
        if self.db_type == self.SQLITE:
            return get_database_instance()
        
        elif self.db_type == self.SUPABASE:
            # Проверяем наличие строки подключения
            connection_string = os.getenv('SUPABASE_DATABASE_URL')
            if not connection_string:
                raise ValueError(
                    "Для использования Supabase необходимо установить переменную окружения SUPABASE_DATABASE_URL"
                )
            return get_supabase_database_instance()
        
        else:
            raise ValueError(f"Неизвестный тип БД: {self.db_type}")

    def is_sqlite(self) -> bool:
        """Проверить, используется ли SQLite"""
        return self.db_type == self.SQLITE

    def is_supabase(self) -> bool:
        """Проверить, используется ли Supabase"""
        return self.db_type == self.SUPABASE

    def get_db_type(self) -> str:
        """Получить тип используемой БД"""
        return self.db_type

# Глобальный экземпляр конфигурации
_database_config = None

def get_database_config() -> DatabaseConfig:
    """Получить глобальный экземпляр конфигурации БД"""
    global _database_config
    if _database_config is None:
        _database_config = DatabaseConfig()
    return _database_config

def get_configured_database() -> Union[Database, SupabaseDatabase]:
    """Получить настроенный экземпляр базы данных"""
    config = get_database_config()
    return config.get_database_instance()

# Удобные функции для проверки типа БД
def is_using_sqlite() -> bool:
    """Проверить, используется ли SQLite"""
    return get_database_config().is_sqlite()

def is_using_supabase() -> bool:
    """Проверить, используется ли Supabase"""
    return get_database_config().is_supabase()

def get_current_db_type() -> str:
    """Получить текущий тип БД"""
    return get_database_config().get_db_type() 