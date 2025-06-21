"""
Database Models - Supabase PostgreSQL Schema

Defines database schema for Supabase PostgreSQL database.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class DatabaseModels:
    """Supabase PostgreSQL database schema definitions"""
    
    def __init__(self):
        pass
    
    def get_table_definitions(self) -> Dict[str, str]:
        """Get all table definitions for Supabase PostgreSQL"""
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
    
    def get_indexes(self) -> List[str]:
        """Get index definitions for Supabase PostgreSQL"""
        return [
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
        ]
    
    def get_initial_data(self) -> Dict[str, List[Dict]]:
        """Get initial data for database seeding"""
        return {
            'main_topics_ru': [
                {'topic_name': 'Математика', 'language': 'ru'},
                {'topic_name': 'Физика', 'language': 'ru'},
                {'topic_name': 'Химия', 'language': 'ru'},
                {'topic_name': 'Биология', 'language': 'ru'},
            ],
            'main_topics_kk': [
                {'topic_name': 'Математика', 'language': 'kk'},
                {'topic_name': 'Физика', 'language': 'kk'},
                {'topic_name': 'Химия', 'language': 'kk'},
                {'topic_name': 'Биология', 'language': 'kk'},
            ]
        } 