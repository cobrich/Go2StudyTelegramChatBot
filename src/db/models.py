"""
Database Models and SQL Definitions

Contains all SQL table definitions and database schema management.
"""

import logging
from typing import Dict, List
from .connection_manager import get_connection_manager, DatabaseType

logger = logging.getLogger(__name__)

class DatabaseModels:
    """Database schema definitions for both SQLite and PostgreSQL"""
    
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'allowed_users': '''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE,
                    full_name TEXT,
                    grade INTEGER,
                    added_by BIGINT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT FALSE,
                    user_id BIGINT,
                    language TEXT DEFAULT 'ru',
                    current_topic TEXT,
                    last_activity TIMESTAMP,
                    has_access BOOLEAN DEFAULT TRUE
                )
            ''',
            
            'main_topics': '''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    language TEXT DEFAULT 'ru',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0
                )
            ''',
            
            'subtopics': '''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0,
                    FOREIGN KEY (main_topic_id) REFERENCES main_topics(id)
                )
            ''',
            
            'questions': '''
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    topic_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (topic_id) REFERENCES subtopics(id)
                )
            ''',
            
            'test_results': '''
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    topic TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'user_errors': '''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    question_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
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
                    is_super_admin BOOLEAN DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'allowed_users': '''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    full_name TEXT,
                    grade INTEGER,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 0,
                    user_id INTEGER,
                    language TEXT DEFAULT "ru",
                    current_topic TEXT,
                    last_activity TIMESTAMP,
                    has_access BOOLEAN DEFAULT 1,
                    FOREIGN KEY (added_by) REFERENCES admins(user_id)
                )
            ''',
            
            'main_topics': '''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    language TEXT DEFAULT "ru",
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0,
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''',
            
            'subtopics': '''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0,
                    FOREIGN KEY (main_topic_id) REFERENCES main_topics(id),
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''',
            
            'questions': '''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (topic_id) REFERENCES subtopics(id)
                )
            ''',
            
            'test_results': '''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES allowed_users(user_id)
                )
            ''',
            
            'user_errors': '''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
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
            'CREATE INDEX IF NOT EXISTS idx_test_results_timestamp ON test_results(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_user_id ON user_errors(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_question_id ON user_errors(question_id)',
            'CREATE INDEX IF NOT EXISTS idx_subtopics_main_topic_id ON subtopics(main_topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_is_active ON allowed_users(is_active)',
            'CREATE INDEX IF NOT EXISTS idx_main_topics_language ON main_topics(language)',
            'CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source)'
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