"""
Database Models - Supabase PostgreSQL Schema

Defines database schema for Supabase PostgreSQL database.
"""

import logging
from typing import Dict, List
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, UniqueConstraint
from datetime import datetime
from sqlalchemy import (
    create_engine, MetaData, Table, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

logger = logging.getLogger(__name__)

Base = declarative_base()

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    is_super_admin = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(BigInteger)

class AllowedUser(Base):
    __tablename__ = 'allowed_users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, index=True)
    full_name = Column(String)
    has_access = Column(Boolean, default=False)
    added_by = Column(BigInteger, nullable=True)
    grade = Column(Integer)
    language = Column(String(2), default='ru')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MainTopic(Base):
    __tablename__ = 'main_topics'
    id = Column(Integer, primary_key=True)
    topic_name = Column(String, nullable=False)
    emoji = Column(String, nullable=True)
    language = Column(String(2), nullable=False)
    is_active = Column(Boolean, default=True)
    subtopics = relationship("SubTopic", back_populates="main_topic")

    __table_args__ = (UniqueConstraint('topic_name', 'language', name='_topic_language_uc'),)

class SubTopic(Base):
    __tablename__ = 'subtopics'
    id = Column(Integer, primary_key=True)
    main_topic_id = Column(Integer, ForeignKey('main_topics.id'), nullable=False)
    subtopic_name = Column(String, nullable=False)
    language = Column(String(2), nullable=False)
    is_active = Column(Boolean, default=True)
    questions = relationship("Question", back_populates="topic")
    main_topic = relationship("MainTopic", back_populates="subtopics")

    __table_args__ = (UniqueConstraint('subtopic_name', 'language', name='_subtopic_language_uc'),)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('subtopics.id'))
    question_text = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)
    incorrect_options = Column(Text)
    question_type = Column(String, default='standard')
    source = Column(String, default='manual')
    topic = relationship("SubTopic", back_populates="questions")

class UserError(Base):
    __tablename__ = 'user_errors'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    topic_id = Column(Integer, ForeignKey('subtopics.id'), nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='_user_question_uc'),)

class UserProgress(Base):
    __tablename__ = 'user_progress'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    topic_id = Column(Integer, ForeignKey('subtopics.id'), nullable=False)
    correct_answers = Column(Integer, default=0)
    total_answers = Column(Integer, default=0)
    last_answered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'topic_id', name='_user_topic_progress_uc'),)

class UserTestResult(Base):
    __tablename__ = 'user_test_results'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    topic = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ManagedMessage(Base):
    __tablename__ = 'managed_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    message_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'message_type', name='_user_message_type_uc'),
    )

    def __repr__(self):
        return (
            f"<ManagedMessage(id={self.id}, user_id={self.user_id}, "
            f"message_id={self.message_id}, message_type='{self.message_type}')>"
        )

class DatabaseSchema:
    def __init__(self, engine):
        self.engine = engine
        self.metadata = Base.metadata

    def create_all(self):
        logger.info("Creating all tables based on Base metadata...")
        self.metadata.create_all(self.engine)
        logger.info("✅ All tables created successfully.")

class DatabaseModels:
    def __init__(self):
        # This class is a placeholder for models if needed elsewhere,
        # but primarily we use the Base declarative models directly.
        self.Admin = Admin
        self.AllowedUser = AllowedUser
        self.MainTopic = MainTopic
        self.SubTopic = SubTopic
        self.Question = Question
        self.UserError = UserError
        self.UserProgress = UserProgress
        self.UserTestResult = UserTestResult
        self.ManagedMessage = ManagedMessage
    
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
                    grade INTEGER CHECK (grade >= 5 AND grade <= 7),
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
                    explanation TEXT,
                    incorrect_options TEXT,
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
            ''',
            
            'user_test_results': '''
                CREATE TABLE IF NOT EXISTS user_test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'managed_messages': '''
                CREATE TABLE IF NOT EXISTS managed_messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    chat_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL,
                    message_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT _user_message_type_uc UNIQUE (user_id, message_type)
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
            'CREATE INDEX IF NOT EXISTS idx_managed_messages_user_id ON managed_messages(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_managed_messages_message_type ON managed_messages(message_type)'
        ] 