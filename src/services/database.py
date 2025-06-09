import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from config.constants import TOPICS

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
            
            # Add source column if it doesn't exist and set default value for existing records
            try:
                cursor.execute('ALTER TABLE questions ADD COLUMN source TEXT DEFAULT "db"')
                # Update existing records to have 'db' as source
                cursor.execute('UPDATE questions SET source = "db" WHERE source IS NULL')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Update question_type from 'ai' to 'test'
            try:
                cursor.execute('UPDATE questions SET question_type = "test" WHERE question_type = "ai"')
                conn.commit()
            except sqlite3.OperationalError as e:
                logging.error(f"Error updating question_type: {e}")
            
            # Add language column if it doesn't exist
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ru"')
                # Update existing records to have 'ru' as default language
                cursor.execute('UPDATE users SET language = "ru" WHERE language IS NULL')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Admins table - для управления администраторами
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Allowed users table - whitelist учеников
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    full_name TEXT,
                    grade INTEGER,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (added_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Topics table - для управления темами
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    grade INTEGER,
                    language TEXT DEFAULT 'ru',
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
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT
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
                    error_count INTEGER DEFAULT 1,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Инициализация тем из constants.py если таблица пустая
            cursor.execute('SELECT COUNT(*) FROM topics')
            if cursor.fetchone()[0] == 0:
                for topic in TOPICS:
                    cursor.execute('''
                        INSERT INTO topics (name, description, is_active)
                        VALUES (?, ?, 1)
                    ''', (topic, f"Тема: {topic}"))
            
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
        """Add a user's error to the database or increment error count if exists."""
        try:
            logging.info(f"[DEBUG][add_user_error] user_id={user_id}, topic={topic}, question_text={question_text}, user_answer_text={user_answer_text}, correct_answer_text={correct_answer_text}, explanation_text={explanation_text}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Check if error already exists
                cursor.execute('''
                    SELECT id, error_count FROM user_errors 
                    WHERE user_id = ? AND question_text = ?
                ''', (user_id, question_text))
                result = cursor.fetchone()
                if result:
                    error_id, current_count = result
                    cursor.execute('''
                        UPDATE user_errors 
                        SET error_count = error_count + 1,
                            timestamp = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (error_id,))
                    logging.info(f"[DEBUG][add_user_error] Updated error_count for id={error_id}")
                else:
                    cursor.execute('''
                        INSERT INTO user_errors 
                        (user_id, topic, question_text, user_answer, correct_answer, explanation)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, topic, question_text, user_answer_text,
                         correct_answer_text, explanation_text))
                    logging.info(f"[DEBUG][add_user_error] Inserted new error for user_id={user_id}, question_text={question_text}")
                conn.commit()
                # Логируем количество строк и последние 3 записи
                cursor.execute('SELECT COUNT(*) FROM user_errors')
                count = cursor.fetchone()[0]
                logging.info(f"[DEBUG][add_user_error] user_errors row count after commit: {count}")
                cursor.execute('SELECT id, user_id, question_text, error_count FROM user_errors ORDER BY id DESC LIMIT 3')
                last_rows = cursor.fetchall()
                logging.info(f"[DEBUG][add_user_error] last 3 rows: {last_rows}")
        except Exception as e:
            logging.error(f"[DEBUG][add_user_error] Exception: {e}")

    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count for a question and remove if reaches 0."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_text = ?', (user_id, question_text))
            before = cursor.fetchone()
            logging.info(f"[DEBUG][decrement_error_count] before: {before}")
            cursor.execute('''
                UPDATE user_errors 
                SET error_count = error_count - 1
                WHERE user_id = ? AND question_text = ?
            ''', (user_id, question_text))
            cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_text = ?', (user_id, question_text))
            after = cursor.fetchone()
            logging.info(f"[DEBUG][decrement_error_count] after: {after}")
            # Remove if count reaches 0
            cursor.execute('''
                DELETE FROM user_errors 
                WHERE user_id = ? AND question_text = ? AND error_count <= 0
            ''', (user_id, question_text))
            logging.info(f"[DEBUG][decrement_error_count] deleted if error_count <= 0 for user_id={user_id}, question_text={question_text}")
            conn.commit()

    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for a specific topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT question, answer, explanation, incorrect_options, question_type, source
                FROM questions
                WHERE topic = ?
                ORDER BY RANDOM()
                LIMIT ?
            ''', (topic, limit))
            columns = ['question', 'answer', 'explanation', 'incorrect_options', 'question_type', 'source']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get tasks that user previously answered incorrectly."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT q.question, q.answer, q.explanation, q.incorrect_options, ue.error_count
                FROM questions q
                JOIN user_errors ue ON q.question = ue.question_text
                WHERE ue.user_id = ? AND ue.topic = ?
                ORDER BY ue.error_count DESC, ue.timestamp DESC
                LIMIT ?
            ''', (user_id, topic, limit))
            columns = ['question', 'answer', 'explanation', 'incorrect_options', 'error_count']
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

    def register_user(self, user_id: int, username: str) -> None:
        """Register a user if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))
            conn.commit()

    def add_question(self, question: dict) -> None:
        """Add a new question to the database."""
        # Validate required fields are not None or empty
        required_fields = ['topic', 'question', 'answer', 'explanation']
        for field in required_fields:
            if not question.get(field):
                logging.error(f"Cannot add question: {field} is None or empty. Question data: {question}")
                return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO questions (topic, question, answer, explanation, incorrect_options, question_type, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                question['topic'],
                question['question'],
                question['answer'],
                question['explanation'],
                question['incorrect_options'],
                question.get('question_type', 'standard'),
                question.get('source', 'db')
            ))
            conn.commit()

    def update_question(self, question_text: str, new_answer: str, new_explanation: str) -> None:
        """Update a question's answer and explanation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE questions 
                SET answer = ?, explanation = ?
                WHERE question = ?
            ''', (new_answer, new_explanation, question_text))
            conn.commit()

    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT question, answer, explanation, topic
                FROM questions
            ''')
            columns = ['question', 'answer', 'explanation', 'topic']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_recent_unique_topics(self, user_id: int, unique_limit: int = 5, history_limit: int = 20) -> list:
        """Get last unique topics with counts from the last history_limit test attempts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic
                FROM test_results
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, history_limit))
            rows = cursor.fetchall()
            topic_counts = {}
            topic_order = []
            for row in rows:
                topic = row[0]
                if topic not in topic_counts:
                    topic_counts[topic] = 1
                    topic_order.append(topic)
                else:
                    topic_counts[topic] += 1
            # Возвращаем только последние unique_limit уникальных тем
            return [(topic, topic_counts[topic]) for topic in topic_order[:unique_limit]]

    def update_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Update user's full name and grade."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET full_name = ?, grade = ? WHERE user_id = ?
            ''', (full_name, grade, user_id))
            conn.commit()

    def get_user_info(self, user_id: int):
        """Get user's full name, grade and language."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT full_name, grade, language FROM users WHERE user_id = ?
            ''', (user_id,))
            return cursor.fetchone()

    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user's full name and grade (insert or update)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET full_name = ?, grade = ? WHERE user_id = ?
            ''', (full_name, grade, user_id))
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO users (user_id, full_name, grade) VALUES (?, ?, ?)
                ''', (user_id, full_name, grade))
            conn.commit()

    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user's full name, grade and language (insert or update)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET full_name = ?, grade = ?, language = ? WHERE user_id = ?
            ''', (full_name, grade, language, user_id))
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO users (user_id, full_name, grade, language) VALUES (?, ?, ?, ?)
                ''', (user_id, full_name, grade, language))
            conn.commit()

    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET language = ? WHERE user_id = ?
            ''', (language, user_id))
            conn.commit()

    def get_user_language(self, user_id: int) -> str:
        """Get user's language."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT language FROM users WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 'ru'

    # === ADMIN MANAGEMENT METHODS ===
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_super_admin FROM admins WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (regular or super)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
    
    def add_admin(self, user_id: int, username: str, full_name: str, is_super: bool = False, added_by: int = None) -> bool:
        """Add new admin."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, full_name, is_super, added_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin (only super admin can do this)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM admins WHERE user_id = ? AND is_super_admin = 0', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def get_all_admins(self) -> List[Dict[str, Any]]:
        """Get all admins."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, is_super_admin, created_at
                FROM admins
                ORDER BY is_super_admin DESC, created_at ASC
            ''')
            results = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'is_super_admin': bool(row[3]),
                    'created_at': row[4]
                }
                for row in results
            ]
    
    # === ALLOWED USERS MANAGEMENT ===
    
    def is_user_allowed(self, username: str) -> bool:
        """Check if user is in whitelist."""
        # Проверяем, что username не None и не пустой
        if not username:
            return False
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM allowed_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int) -> bool:
        """Add user to whitelist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO allowed_users (username, full_name, grade, added_by)
                    VALUES (?, ?, ?, ?)
                ''', (username, full_name, grade, added_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_allowed_user(self, username: str) -> bool:
        """Remove user from whitelist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM allowed_users WHERE username = ?', (username,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def update_allowed_user(self, username: str, full_name: str = None, grade: int = None, is_active: bool = None) -> bool:
        """Update allowed user info."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if full_name is not None:
                    updates.append("full_name = ?")
                    params.append(full_name)
                if grade is not None:
                    updates.append("grade = ?")
                    params.append(grade)
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(is_active)
                
                if updates:
                    params.append(username)
                    cursor.execute(f'''
                        UPDATE allowed_users 
                        SET {", ".join(updates)}
                        WHERE username = ?
                    ''', params)
                    conn.commit()
                    return cursor.rowcount > 0
                return False
        except Exception:
            return False
    
    def get_all_allowed_users(self) -> List[Dict[str, Any]]:
        """Get all allowed users."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, full_name, grade, is_active, added_at
                FROM allowed_users
                ORDER BY added_at DESC
            ''')
            results = cursor.fetchall()
            return [
                {
                    'username': row[0],
                    'full_name': row[1],
                    'grade': row[2],
                    'is_active': bool(row[3]),
                    'added_at': row[4]
                }
                for row in results
            ]
    
    # === TOPICS MANAGEMENT ===
    
    def get_all_topics(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all topics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = 'SELECT id, name, description, is_active, created_at FROM topics'
            if active_only:
                query += ' WHERE is_active = 1'
            query += ' ORDER BY name'
            
            cursor.execute(query)
            results = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'is_active': bool(row[3]),
                    'created_at': row[4]
                }
                for row in results
            ]
    
    def add_topic(self, name: str, description: str = None, created_by: int = None) -> bool:
        """Add new topic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO topics (name, description, created_by)
                    VALUES (?, ?, ?)
                ''', (name, description or f"Тема: {name}", created_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def update_topic(self, topic_id: int, name: str = None, description: str = None, is_active: bool = None) -> bool:
        """Update topic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(is_active)
                
                if updates:
                    params.append(topic_id)
                    cursor.execute(f'''
                        UPDATE topics 
                        SET {", ".join(updates)}
                        WHERE id = ?
                    ''', params)
                    conn.commit()
                    return cursor.rowcount > 0
                return False
        except Exception:
            return False
    
    def delete_topic(self, topic_id: int) -> bool:
        """Delete topic (soft delete - set is_active to 0)."""
        return self.update_topic(topic_id, is_active=False)
    
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get list of topic names for compatibility with existing code."""
        topics = self.get_all_topics(active_only)
        return [topic['name'] for topic in topics]

    # === USER DATA MANAGEMENT ===
    
    def get_user_full_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get complete user profile combining users and allowed_users data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    u.user_id,
                    u.username as current_username,
                    u.full_name as current_full_name,
                    u.grade as current_grade,
                    u.language,
                    u.is_active,
                    u.current_topic,
                    u.last_activity,
                    au.username as whitelist_username,
                    au.full_name as whitelist_full_name,
                    au.grade as whitelist_grade,
                    au.is_active as whitelist_active,
                    au.added_at as whitelist_added_at
                FROM users u
                LEFT JOIN allowed_users au ON u.username = au.username
                WHERE u.user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                'user_id': result[0],
                'current_username': result[1],
                'current_full_name': result[2],
                'current_grade': result[3],
                'language': result[4],
                'is_active': bool(result[5]),
                'current_topic': result[6],
                'last_activity': result[7],
                'whitelist_username': result[8],
                'whitelist_full_name': result[9],
                'whitelist_grade': result[10],
                'whitelist_active': bool(result[11]) if result[11] is not None else False,
                'whitelist_added_at': result[12],
                'has_whitelist_access': result[11] is not None and bool(result[11])
            }
    
    def sync_user_with_whitelist(self, user_id: int, username: str) -> bool:
        """Sync user data with whitelist information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get whitelist data
                cursor.execute('''
                    SELECT full_name, grade FROM allowed_users 
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                whitelist_data = cursor.fetchone()
                
                if whitelist_data:
                    # Update users table with whitelist data if it's newer/better
                    cursor.execute('''
                        UPDATE users 
                        SET username = ?, 
                            full_name = COALESCE(?, full_name),
                            grade = COALESCE(?, grade)
                        WHERE user_id = ?
                    ''', (username, whitelist_data[0], whitelist_data[1], user_id))
                    
                    return True
                return False
        except Exception as e:
            logging.error(f"Error syncing user with whitelist: {e}")
            return False
    
    def get_user_historical_stats(self, user_id: int) -> Dict[str, Any]:
        """Get historical statistics for a user, even if they're not in whitelist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Test results
            cursor.execute('''
                SELECT COUNT(*), AVG(percentage), MIN(timestamp), MAX(timestamp)
                FROM test_results WHERE user_id = ?
            ''', (user_id,))
            test_stats = cursor.fetchone()
            
            # Error count
            cursor.execute('''
                SELECT COUNT(DISTINCT question_text), SUM(error_count)
                FROM user_errors WHERE user_id = ?
            ''', (user_id,))
            error_stats = cursor.fetchone()
            
            # User info
            cursor.execute('''
                SELECT username, full_name, grade, language, last_activity
                FROM users WHERE user_id = ?
            ''', (user_id,))
            user_info = cursor.fetchone()
            
            return {
                'user_id': user_id,
                'username': user_info[0] if user_info else None,
                'full_name': user_info[1] if user_info else None,
                'grade': user_info[2] if user_info else None,
                'language': user_info[3] if user_info else 'ru',
                'last_activity': user_info[4] if user_info else None,
                'total_tests': test_stats[0] if test_stats else 0,
                'avg_percentage': test_stats[1] if test_stats else 0,
                'first_test': test_stats[2] if test_stats else None,
                'last_test': test_stats[3] if test_stats else None,
                'unique_errors': error_stats[0] if error_stats else 0,
                'total_error_count': error_stats[1] if error_stats else 0
            }
    
    def get_all_users_with_history(self) -> List[Dict[str, Any]]:
        """Get all users who have any activity history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT u.user_id
                FROM users u
                WHERE u.user_id IN (
                    SELECT DISTINCT user_id FROM test_results
                    UNION
                    SELECT DISTINCT user_id FROM user_errors
                )
                ORDER BY u.last_activity DESC
            ''')
            
            user_ids = [row[0] for row in cursor.fetchall()]
            return [self.get_user_historical_stats(user_id) for user_id in user_ids] 