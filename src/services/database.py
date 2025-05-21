import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional, Tuple

class Database:
    def __init__(self, db_path: str = None):
        # Всегда использовать базу в корне проекта
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, "math_bot.db")
        self.db_path = db_path
        print(f"[LOG] Используется база данных: {os.path.abspath(self.db_path)}")
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    current_topic TEXT,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT,
                    percentage REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    question TEXT,
                    answer TEXT,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard'
                )
            ''')
            
            # User errors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT,
                    question_text TEXT,
                    user_answer TEXT,
                    correct_answer TEXT,
                    explanation TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            conn.commit()

    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active and update their current topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, is_active, current_topic, last_activity)
                VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ''', (user_id, topic))
            conn.commit()

    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_active = 0, current_topic = NULL 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def is_user_active(self, user_id: int) -> bool:
        """Check if user is currently active."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])

    def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add a new test result."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO test_results (user_id, topic, percentage)
                VALUES (?, ?, ?)
            ''', (user_id, topic, percentage))
            conn.commit()

    def get_user_progress(self, user_id: int) -> Tuple[int, float]:
        """Get user's test progress statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as total_tests, AVG(percentage) as avg_percentage
                FROM test_results
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result or (0, 0)

    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[Tuple[str, float, str]]:
        """Get user's recent test topics with results."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic, percentage, timestamp
                FROM test_results
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            return cursor.fetchall()

    def get_error_topics(self, user_id: int) -> List[Tuple[str, int]]:
        """Get topics where user made errors."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic, COUNT(*) as error_count
                FROM user_errors
                WHERE user_id = ?
                GROUP BY topic
            ''', (user_id,))
            return cursor.fetchall()

    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add a user's error to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_errors 
                (user_id, topic, question_text, user_answer, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, topic, question_text, user_answer_text,
                 correct_answer_text, explanation_text))
            conn.commit()

    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for a specific topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT question, answer, explanation, incorrect_options, question_type
                FROM questions
                WHERE topic = ?
                ORDER BY RANDOM()
                LIMIT ?
            ''', (topic, limit))
            columns = ['question', 'answer', 'explanation', 'incorrect_options', 'question_type']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get tasks that user previously answered incorrectly."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT q.question, q.answer, q.explanation, q.incorrect_options
                FROM questions q
                JOIN user_errors ue ON q.question = ue.question_text
                WHERE ue.user_id = ? AND ue.topic = ?
                ORDER BY ue.timestamp DESC
                LIMIT ?
            ''', (user_id, topic, limit))
            columns = ['question', 'answer', 'explanation', 'incorrect_options']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation for a question by exact text match."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT explanation
                FROM questions
                WHERE question = ?
            ''', (question_text,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_explanation_fuzzy_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation for a question using fuzzy matching."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT explanation
                FROM questions
                WHERE question LIKE ?
                LIMIT 1
            ''', (f'%{question_text}%',))
            result = cursor.fetchone()
            return result[0] if result else None

    def delete_all_user_data(self, user_id: int) -> bool:
        """Delete all data associated with a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM test_results WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM user_errors WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting user data: {e}")
            return False

    def set_all_users_inactive(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_active = 0, current_topic = NULL')
            conn.commit() 