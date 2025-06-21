"""
Database Models - Улучшенная схема базы данных

Изменения:
- allowed_users: user_id как PRIMARY KEY
- test_results: добавлен topic_id, убрано дублирование date/timestamp
- user_errors: убрано дублирующее поле topic
- Добавлены updated_at поля для аудита
- Оптимизированы индексы
"""

import logging
from typing import Dict, List
from .connection_manager import get_connection_manager, DatabaseType

logger = logging.getLogger(__name__)

class DatabaseModels:
    """Определения схемы базы данных для SQLite и PostgreSQL"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
        self.is_postgresql = self.connection_manager.is_postgresql()
    
    def get_table_definitions(self) -> Dict[str, str]:
        """Get all table definitions based on database type"""
        if self.is_postgresql:
            return self._get_postgresql_tables()
        else:
            return self._get_sqlite_tables()
    
    def _get_postgresql_tables(self) -> Dict[str, str]:
        """PostgreSQL table definitions"""
        return {
            'admins': '''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'allowed_users': '''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT UNIQUE,
                    full_name TEXT,
                    grade INTEGER CHECK (grade IN (5, 6)),
                    added_by BIGINT REFERENCES admins(user_id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT FALSE,
                    language TEXT DEFAULT 'ru' CHECK (language IN ('ru', 'kk')),
                    current_topic TEXT,
                    last_activity TIMESTAMP,
                    has_access BOOLEAN DEFAULT TRUE
                )
            ''',
            
            'main_topics': '''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id SERIAL PRIMARY KEY,
                    topic_name TEXT NOT NULL,
                    language TEXT NOT NULL CHECK (language IN ('ru', 'kk')),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(topic_name, language)
                )
            ''',
            
            'subtopics': '''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id SERIAL PRIMARY KEY,
                    subtopic_name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL REFERENCES main_topics(id) ON DELETE CASCADE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subtopic_name, main_topic_id)
                )
            ''',
            
            'questions': '''
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_text TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'test_results': '''
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
                    percentage REAL NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'user_errors': '''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, question_id)
                )
            '''
        }
    
    def _get_sqlite_tables(self) -> Dict[str, str]:
        """SQLite table definitions"""
        return {
            'admins': '''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'allowed_users': '''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    full_name TEXT NOT NULL,
                    grade INTEGER CHECK (grade IN (5, 6)),
                    added_by INTEGER REFERENCES admins(user_id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 0,
                    language TEXT DEFAULT "ru",
                    current_topic TEXT,
                    last_activity TIMESTAMP,
                    has_access INTEGER DEFAULT 1
                )
            ''',
            
            'main_topics': '''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_name TEXT NOT NULL,
                    language TEXT DEFAULT "ru",
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(topic_name, language)
                )
            ''',
            
            'subtopics': '''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subtopic_name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL REFERENCES main_topics(id),
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subtopic_name, main_topic_id)
                )
            ''',
            
            'questions': '''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_text TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'test_results': '''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES allowed_users(user_id),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
                    percentage REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES allowed_users(user_id)
                )
            ''',
            
            'user_errors': '''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES allowed_users(user_id),
                    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, question_id)
                )
            '''
        }
    
    def get_indexes(self) -> List[str]:
        """Get index definitions"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_user_id ON allowed_users(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_questions_topic_id ON questions(topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON test_results(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_topic_id ON test_results(topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_user_id ON user_errors(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_question_id ON user_errors(question_id)',
            'CREATE INDEX IF NOT EXISTS idx_subtopics_main_topic_id ON subtopics(main_topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_is_active ON allowed_users(is_active)',
            'CREATE INDEX IF NOT EXISTS idx_main_topics_language ON main_topics(language)',
            'CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_created_at ON test_results(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_user_topic_results ON test_results(user_id, topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_question_errors ON user_errors(user_id, question_id)',
            'CREATE INDEX IF NOT EXISTS idx_active_topics ON subtopics(is_active, main_topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_active_main_topics ON main_topics(is_active, language)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_grade ON allowed_users(grade)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_language ON allowed_users(language)',
            'CREATE INDEX IF NOT EXISTS idx_questions_correct_answer ON questions(correct_answer)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_percentage ON test_results(percentage)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_has_access ON allowed_users(has_access)'
        ]
        return indexes
    
    def get_initial_data(self) -> Dict[str, List[Dict]]:
        """Get initial data for database seeding"""
        return {
            'main_topics_ru': [
                {'name': 'Арифметика', 'language': 'ru', 'order_index': 0},
                {'name': 'Алгебра', 'language': 'ru', 'order_index': 1},
                {'name': 'Геометрия', 'language': 'ru', 'order_index': 2},
                {'name': 'Логика', 'language': 'ru', 'order_index': 3}
            ],
            'main_topics_kk': [
                {'name': 'Арифметика', 'language': 'kk', 'order_index': 0},
                {'name': 'Алгебра', 'language': 'kk', 'order_index': 1},
                {'name': 'Геометрия', 'language': 'kk', 'order_index': 2},
                {'name': 'Логика', 'language': 'kk', 'order_index': 3}
            ],
            'subtopics_ru': {
                'Арифметика': ['Арифметические задачи', 'Пропорции', 'Проценты'],
                'Алгебра': ['Уравнения', 'Неравенства', 'Функции'],
                'Геометрия': ['Планиметрия', 'Стереометрия', 'Тригонометрия'],
                'Логика': ['Логические задачи', 'Числовые последовательности', 'Вероятность']
            },
            'subtopics_kk': {
                'Арифметика': ['Арифметикалық есептер', 'Пропорция', 'Пайыз есептеулері'],
                'Алгебра': ['Теңдеулер', 'Теңсіздіктер', 'Функциялар'],
                'Геометрия': ['Планиметрия', 'Стереометрия', 'Тригонометрия'],
                'Логика': ['Логикалық сұрақтар', 'Сандық тізбектер', 'Ықтималдық']
            }
        } 