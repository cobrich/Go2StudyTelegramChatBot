import sqlite3
import logging
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

# Добавляем корневую директорию проекта в sys.path для импортов
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
            
            # Add language column to main_topics if it doesn't exist
            try:
                # Проверяем, существует ли уже поле language
                cursor.execute("PRAGMA table_info(main_topics)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'language' not in columns:
                    cursor.execute('ALTER TABLE main_topics ADD COLUMN language TEXT DEFAULT "ru"')
                    # Update existing records to have 'ru' as default language
                    cursor.execute('UPDATE main_topics SET language = "ru" WHERE language IS NULL')
                    conn.commit()
                    print("[LOG] Добавлено поле language в таблицу main_topics")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Update main_topics UNIQUE constraint to support (name, language)
            try:
                # Проверяем, существует ли уже индекс
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='idx_main_topics_name_language'
                ''')
                index_exists = cursor.fetchone() is not None
                
                if not index_exists:
                    cursor.execute('''
                        CREATE UNIQUE INDEX idx_main_topics_name_language 
                        ON main_topics(name, language)
                    ''')
                    conn.commit()
                    print("[LOG] Обновлен UNIQUE constraint для main_topics")
            except sqlite3.OperationalError:
                # Index already exists or other error
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
            
            # Add user_id column for users without username
            try:
                cursor.execute('ALTER TABLE allowed_users ADD COLUMN user_id INTEGER')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add phone_number column for contact information
            try:
                cursor.execute('ALTER TABLE allowed_users ADD COLUMN phone_number TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add language column to allowed_users
            try:
                # Проверяем, существует ли уже поле language
                cursor.execute("PRAGMA table_info(allowed_users)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'language' not in columns:
                    cursor.execute('ALTER TABLE allowed_users ADD COLUMN language TEXT DEFAULT "ru"')
                    # Update existing records to have 'ru' as default language
                    cursor.execute('UPDATE allowed_users SET language = "ru" WHERE language IS NULL')
                    conn.commit()
                    print("[LOG] Добавлено поле language в таблицу allowed_users")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add unique constraint for user_id to prevent duplicates
            try:
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_allowed_users_user_id ON allowed_users(user_id) WHERE user_id IS NOT NULL')
                conn.commit()
            except sqlite3.OperationalError:
                # Index already exists
                pass
            
            # Main topics table - основные разделы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Subtopics table - подтемы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    main_topic_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(main_topic_id, name),
                    FOREIGN KEY (main_topic_id) REFERENCES main_topics(id) ON DELETE CASCADE
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
            
            # Add phone_number column to users table if it doesn't exist
            try:
                # Проверяем, существует ли уже поле phone_number
                cursor.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'phone_number' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN phone_number TEXT')
                    conn.commit()
                    print("[LOG] Добавлено поле phone_number в таблицу users")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
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
            
            # Инициализация нормализованной структуры из constants.py если таблицы пустые
            cursor.execute('SELECT COUNT(*) FROM main_topics')
            if cursor.fetchone()[0] == 0:
                try:
                    from config.constants import TOPIC_HIERARCHY
                    # Добавляем основные разделы
                    for order_index, main_topic in enumerate(TOPIC_HIERARCHY.keys()):
                        cursor.execute('''
                            INSERT INTO main_topics (name, order_index, is_active)
                            VALUES (?, ?, 1)
                        ''', (main_topic, order_index))
                    
                    # Получаем ID основных тем и добавляем подтемы
                    cursor.execute('SELECT id, name FROM main_topics')
                    main_topics_map = {name: id for id, name in cursor.fetchall()}
                    
                    for main_topic, subtopics in TOPIC_HIERARCHY.items():
                        main_topic_id = main_topics_map[main_topic]
                        for subtopic_order, subtopic in enumerate(subtopics):
                            cursor.execute('''
                                INSERT INTO subtopics (main_topic_id, name, order_index, is_active)
                                VALUES (?, ?, ?, 1)
                            ''', (main_topic_id, subtopic, subtopic_order))
                    
                    print(f"[LOG] Инициализированы темы из иерархической структуры: {len(TOPIC_HIERARCHY)} основных разделов")
                except ImportError:
                    print("[LOG] config.constants не найден, пропускаем инициализацию тем")
            
            conn.commit()

    def _get_connection(self):
        """Get database connection context manager."""
        return sqlite3.connect(self.db_path)

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
        """Add test result for user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO test_results (user_id, topic, percentage) VALUES (?, ?, ?)',
                (user_id, topic, percentage)
            )
            conn.commit()

    def get_user_test_results(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all test results for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic, percentage, timestamp 
                FROM test_results 
                WHERE user_id = ? 
                ORDER BY timestamp DESC
            ''', (user_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'topic': row[0],
                    'percentage': row[1],
                    'date': row[2][:10] if row[2] else ''  # Extract date part from timestamp
                })
            
            return results

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

    def clear_user_activity(self, user_id: int) -> None:
        """Clear user activity and set as inactive."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_active = 0, current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def register_user(self, user_id: int, username: str) -> None:
        """Register a new user and sync with whitelist data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем данные из whitelist если есть
            cursor.execute('''
                SELECT full_name, grade 
                FROM allowed_users 
                WHERE user_id = ? OR username = ?
            ''', (user_id, username))
            whitelist_data = cursor.fetchone()
            
            if whitelist_data:
                full_name, grade = whitelist_data
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, full_name, grade, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, full_name, grade))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, last_activity)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
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
        """Update user's language and clear their data if language changed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем текущий язык пользователя
            cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            current_language = result[0] if result else 'ru'
            
            # Обновляем язык в таблице users
            cursor.execute('''
                UPDATE users SET language = ? WHERE user_id = ?
            ''', (language, user_id))
            
            # Обновляем язык в таблице allowed_users
            cursor.execute('''
                UPDATE allowed_users SET language = ? WHERE user_id = ?
            ''', (language, user_id))
            
            conn.commit()
            
            # Если язык изменился, очищаем данные пользователя
            if current_language != language:
                print(f"[LOG] Язык пользователя {user_id} изменен с '{current_language}' на '{language}', очищаем данные")
                self.clear_user_data_on_language_change(user_id)

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
            cursor.execute('''
                SELECT is_super_admin FROM admins WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] == 1 if result else False
    
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
    
    def get_all_admins(self) -> List[Dict]:
        """Get list of all admins."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, is_super_admin, created_at
                FROM admins
                ORDER BY is_super_admin DESC, created_at ASC
            ''')
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'is_super': bool(row[3]),
                    'added_at': row[4]
                }
                for row in rows
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
    
    def is_user_allowed_by_id(self, user_id: int) -> bool:
        """Check if user is allowed by user_id (for users without username)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def check_user_access(self, user_id: int, username: str = None) -> bool:
        """
        Comprehensive access check for users.
        Checks admin status, username whitelist, and user_id whitelist.
        """
        # First check if user is admin
        if self.is_admin(user_id):
            return True
        
        # Check username whitelist if username exists
        if username and self.is_user_allowed(username):
            return True
        
        # Check user_id whitelist for users without username
        if self.is_user_allowed_by_id(user_id):
            return True
        
        return False
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int, user_id: int = None, language: str = "ru") -> bool:
        """Add user to whitelist with language support."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, что есть хотя бы один идентификатор
                if not user_id:
                    return False
                
                cursor.execute('''
                    INSERT INTO allowed_users (username, full_name, grade, user_id, added_by, language)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, full_name, grade, user_id, added_by, language))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def add_allowed_user_by_id(self, user_id: int, full_name: str, grade: int, added_by: int, username: str = None, language: str = "ru") -> bool:
        """Add user to whitelist by user_id (for users without username) with language support."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, что есть хотя бы один идентификатор
                if not user_id:
                    return False
                
                cursor.execute('''
                    INSERT INTO allowed_users (user_id, username, full_name, grade, added_by, language)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, full_name, grade, added_by, language))
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

    def remove_allowed_user_by_id(self, user_id: int) -> bool:
        """Remove user from whitelist by user_id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM allowed_users WHERE user_id = ?', (user_id,))
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
        """Получить всех разрешенных пользователей."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, full_name, grade, is_active, added_at
                    FROM allowed_users
                    ORDER BY added_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting allowed users: {e}")
            return []

    def get_allowed_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Получить информацию о разрешенном пользователе по ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, full_name, grade, is_active, added_at, added_by
                    FROM allowed_users
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except sqlite3.Error as e:
            logging.error(f"Error getting allowed user by ID {user_id}: {e}")
            return None
    
    # === TOPICS MANAGEMENT (Updated to use normalized structure) ===
    
    def get_all_topics(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all subtopics as flat list for compatibility."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = '''
                SELECT st.id, st.name, mt.name as main_topic, st.is_active, st.created_at
                FROM subtopics st
                JOIN main_topics mt ON st.main_topic_id = mt.id
            '''
            if active_only:
                query += ' WHERE st.is_active = 1 AND mt.is_active = 1'
            query += ' ORDER BY mt.order_index, st.order_index'
            
            cursor.execute(query)
            results = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'description': f"Подтема раздела '{row[2]}': {row[1]}",
                    'main_topic': row[2],
                    'is_active': bool(row[3]),
                    'created_at': row[4]
                }
                for row in results
            ]
    
    def add_topic(self, name: str, description: str = None, created_by: int = None, main_topic_name: str = None) -> bool:
        """Add new subtopic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Если указан основной раздел, найдем его ID
                if main_topic_name:
                    cursor.execute('SELECT id FROM main_topics WHERE name = ?', (main_topic_name,))
                    result = cursor.fetchone()
                    if not result:
                        return False
                    main_topic_id = result[0]
                else:
                    # Если не указан, создаем в первом доступном разделе
                    cursor.execute('SELECT id FROM main_topics WHERE is_active = 1 ORDER BY order_index LIMIT 1')
                    result = cursor.fetchone()
                    if not result:
                        return False
                    main_topic_id = result[0]
                
                # Получаем следующий order_index
                cursor.execute('SELECT MAX(order_index) FROM subtopics WHERE main_topic_id = ?', (main_topic_id,))
                max_order = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    INSERT INTO subtopics (main_topic_id, name, order_index)
                    VALUES (?, ?, ?)
                ''', (main_topic_id, name, max_order + 1))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def update_topic(self, topic_id: int, name: str = None, description: str = None, is_active: bool = None) -> bool:
        """Update subtopic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(is_active)
                
                if updates:
                    params.append(topic_id)
                    cursor.execute(f'''
                        UPDATE subtopics 
                        SET {", ".join(updates)}
                        WHERE id = ?
                    ''', params)
                    conn.commit()
                    return cursor.rowcount > 0
                return False
        except Exception:
            return False
    
    def delete_topic(self, topic_id: int) -> bool:
        """Delete subtopic (soft delete - set is_active to 0)."""
        return self.update_topic(topic_id, is_active=False)
    
    def delete_topic_permanently(self, topic_id: int) -> bool:
        """Permanently delete topic and all related data (hard delete)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем название темы для логирования
                cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
                topic_result = cursor.fetchone()
                if not topic_result:
                    return False
                
                topic_name = topic_result[0]
                
                # Удаляем все связанные данные
                # 1. Удаляем результаты тестов
                cursor.execute('DELETE FROM test_results WHERE topic = ?', (topic_name,))
                
                # 2. Удаляем ошибки пользователей
                cursor.execute('DELETE FROM user_errors WHERE topic = ?', (topic_name,))
                
                # 3. Удаляем вопросы по теме
                cursor.execute('DELETE FROM questions WHERE topic = ?', (topic_name,))
                
                # 4. Удаляем саму тему
                cursor.execute('DELETE FROM subtopics WHERE id = ?', (topic_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error permanently deleting topic: {e}")
            return False
    
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get list of subtopic names for compatibility with existing code."""
        topics = self.get_all_topics(active_only)
        return [topic['name'] for topic in topics]
    
    # === BASE TOPIC STRUCTURE MANAGEMENT (Updated for normalized structure) ===
    
    def get_base_topic_structure(self) -> Dict[str, List[str]]:
        """Get the current base topic structure from normalized database tables (все языки)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mt.name, st.name
                FROM main_topics mt
                JOIN subtopics st ON mt.id = st.main_topic_id
                WHERE mt.is_active = 1 AND st.is_active = 1
                ORDER BY mt.order_index, st.order_index
            ''')
            
            structure = {}
            for main_topic, subtopic in cursor.fetchall():
                if main_topic not in structure:
                    structure[main_topic] = []
                structure[main_topic].append(subtopic)
            
            return structure

    def get_base_topic_structure_by_language(self, language: str) -> Dict[str, List[str]]:
        """Get the base topic structure for specific language."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mt.name, st.name
                FROM main_topics mt
                JOIN subtopics st ON mt.id = st.main_topic_id
                WHERE mt.is_active = 1 AND st.is_active = 1 AND mt.language = ?
                ORDER BY mt.order_index, st.order_index
            ''', (language,))
            
            structure = {}
            for main_topic, subtopic in cursor.fetchall():
                if main_topic not in structure:
                    structure[main_topic] = []
                structure[main_topic].append(subtopic)
            
            return structure
    
    def add_base_topic_section(self, main_topic: str, subtopics: List[str], created_by: int = None) -> bool:
        """Add a new base topic section."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем следующий order_index для основной темы
                cursor.execute('SELECT MAX(order_index) FROM main_topics')
                max_main_order = cursor.fetchone()[0] or 0
                
                # Добавляем основную тему
                cursor.execute('''
                    INSERT INTO main_topics (name, order_index)
                    VALUES (?, ?)
                ''', (main_topic, max_main_order + 1))
                
                main_topic_id = cursor.lastrowid
                
                # Добавляем подтемы
                for i, subtopic in enumerate(subtopics):
                    cursor.execute('''
                        INSERT INTO subtopics (main_topic_id, name, order_index)
                        VALUES (?, ?, ?)
                    ''', (main_topic_id, subtopic, i))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def update_base_topic_section(self, old_main_topic: str, new_main_topic: str = None, 
                                 new_subtopics: List[str] = None) -> bool:
        """Update a base topic section."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Находим ID основной темы
                cursor.execute('SELECT id FROM main_topics WHERE name = ?', (old_main_topic,))
                result = cursor.fetchone()
                if not result:
                    return False
                main_topic_id = result[0]
                
                if new_main_topic and new_main_topic != old_main_topic:
                    cursor.execute('''
                        UPDATE main_topics 
                        SET name = ? 
                        WHERE id = ?
                    ''', (new_main_topic, main_topic_id))
                
                if new_subtopics is not None:
                    # Удаляем старые подтемы
                    cursor.execute('DELETE FROM subtopics WHERE main_topic_id = ?', (main_topic_id,))
                    
                    # Добавляем новые
                    for i, subtopic in enumerate(new_subtopics):
                        cursor.execute('''
                            INSERT INTO subtopics (main_topic_id, name, order_index)
                            VALUES (?, ?, ?)
                        ''', (main_topic_id, subtopic, i))
                
                conn.commit()
                return True
        except Exception:
            return False
    
    def delete_base_topic_section(self, main_topic: str, hard_delete: bool = False) -> bool:
        """Delete a base topic section."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT id FROM main_topics WHERE name = ?', (main_topic,))
                result = cursor.fetchone()
                if not result:
                    return False
                main_topic_id = result[0]
                
                if hard_delete:
                    # При hard delete подтемы удалятся автоматически через CASCADE
                    cursor.execute('DELETE FROM main_topics WHERE id = ?', (main_topic_id,))
                else:
                    cursor.execute('UPDATE main_topics SET is_active = 0 WHERE id = ?', (main_topic_id,))
                    cursor.execute('UPDATE subtopics SET is_active = 0 WHERE main_topic_id = ?', (main_topic_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def add_base_subtopic(self, main_topic: str, subtopic: str) -> bool:
        """Add a single subtopic to existing main topic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Находим ID основной темы
                cursor.execute('SELECT id FROM main_topics WHERE name = ?', (main_topic,))
                result = cursor.fetchone()
                if not result:
                    return False
                main_topic_id = result[0]
                
                # Получаем максимальный order_index для данной главной темы
                cursor.execute('SELECT MAX(order_index) FROM subtopics WHERE main_topic_id = ?', (main_topic_id,))
                max_order = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    INSERT INTO subtopics (main_topic_id, name, order_index)
                    VALUES (?, ?, ?)
                ''', (main_topic_id, subtopic, max_order + 1))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_base_subtopic(self, main_topic: str, subtopic: str) -> bool:
        """Remove a subtopic from base structure."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT st.id FROM subtopics st
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    WHERE mt.name = ? AND st.name = ?
                ''', (main_topic, subtopic))
                result = cursor.fetchone()
                if not result:
                    return False
                
                cursor.execute('DELETE FROM subtopics WHERE id = ?', (result[0],))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

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
        """Синхронизировать данные пользователя с whitelist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем данные из allowed_users
                cursor.execute('''
                    SELECT full_name, grade, is_active
                    FROM allowed_users 
                    WHERE user_id = ? OR username = ?
                    ORDER BY user_id IS NOT NULL DESC
                    LIMIT 1
                ''', (user_id, username))
                
                whitelist_data = cursor.fetchone()
                if not whitelist_data:
                    return False
                
                full_name, grade, is_whitelist_active = whitelist_data
                
                # Обновляем данные в users
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, full_name, grade, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, full_name, grade))
                
                # Обновляем данные в users
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, full_name, grade, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, full_name, grade))
                
                # Обновляем user_id в allowed_users если его не было
                cursor.execute('''
                    UPDATE allowed_users 
                    SET user_id = ?, username = ?
                    WHERE (user_id IS NULL OR user_id = 0) AND username = ?
                ''', (user_id, username, username))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации пользователя {user_id}: {e}")
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
        """Get all users with their test history and statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all users
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.grade, u.language, u.last_activity
                FROM users u
                ORDER BY u.last_activity DESC
            ''')
            users = cursor.fetchall()
            
            result = []
            for user in users:
                user_id, username, full_name, grade, language, last_activity = user
                
                # Get test statistics
                cursor.execute('''
                    SELECT COUNT(*) as total_tests, AVG(percentage) as avg_score
                    FROM test_results 
                    WHERE user_id = ?
                ''', (user_id,))
                stats = cursor.fetchone()
                total_tests, avg_score = stats if stats else (0, 0.0)
                
                # Get recent topics
                cursor.execute('''
                    SELECT topic, COUNT(*) as count
                    FROM test_results 
                    WHERE user_id = ?
                    GROUP BY topic
                    ORDER BY MAX(timestamp) DESC
                    LIMIT 3
                ''', (user_id,))
                recent_topics = cursor.fetchall()
                
                result.append({
                    'user_id': user_id,
                    'username': username or 'не указан',
                    'full_name': full_name or 'не указано',
                    'grade': grade,
                    'language': language,
                    'last_activity': last_activity,
                    'total_tests': total_tests,
                    'avg_score': round(avg_score or 0.0, 1),
                    'recent_topics': recent_topics
                })
            
            return result

    def get_topic_question_counts(self) -> Dict[str, int]:
        """Get question count for each topic."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic, COUNT(*) as question_count
                FROM questions
                GROUP BY topic
                ORDER BY topic
            ''')
            results = cursor.fetchall()
            return {topic: count for topic, count in results}

    def get_topics_with_question_counts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all topics with their question counts and availability status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all subtopics with question counts
            if active_only:
                cursor.execute('''
                    SELECT s.name, 
                           COALESCE(q.question_count, 0) as question_count,
                           m.name as main_topic
                    FROM subtopics s
                    JOIN main_topics m ON s.main_topic_id = m.id
                    LEFT JOIN (
                        SELECT topic, COUNT(*) as question_count
                        FROM questions
                        GROUP BY topic
                    ) q ON s.name = q.topic
                    WHERE s.is_active = 1 AND m.is_active = 1
                    ORDER BY m.order_index, s.order_index
                ''')
            else:
                cursor.execute('''
                    SELECT s.name, 
                           COALESCE(q.question_count, 0) as question_count,
                           m.name as main_topic
                    FROM subtopics s
                    JOIN main_topics m ON s.main_topic_id = m.id
                    LEFT JOIN (
                        SELECT topic, COUNT(*) as question_count
                        FROM questions
                        GROUP BY topic
                    ) q ON s.name = q.topic
                    ORDER BY m.order_index, s.order_index
                ''')
            
            results = cursor.fetchall()
            return [
                {
                    'name': name,
                    'question_count': question_count,
                    'main_topic': main_topic,
                    'has_questions': question_count > 0,
                    'availability_status': 'db' if question_count > 0 else 'ai'
                }
                for name, question_count, main_topic in results
            ]

    def get_student_detailed_statistics(self, user_id: int) -> Dict[str, Any]:
        """Получить детальную статистику ученика для админов."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Основная информация об ученике
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.grade, u.language, u.last_activity,
                       au.full_name as whitelist_name, au.grade as whitelist_grade, au.added_at
                FROM users u
                LEFT JOIN allowed_users au ON (u.user_id = au.user_id OR u.username = au.username)
                WHERE u.user_id = ?
            ''', (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return None
            
            # Статистика по тестам
            cursor.execute('''
                SELECT COUNT(*) as total_tests, 
                       AVG(percentage) as avg_score,
                       MIN(percentage) as min_score,
                       MAX(percentage) as max_score,
                       MIN(timestamp) as first_test,
                       MAX(timestamp) as last_test
                FROM test_results 
                WHERE user_id = ?
            ''', (user_id,))
            test_stats = cursor.fetchone()
            
            # Статистика по темам
            cursor.execute('''
                SELECT topic, 
                       COUNT(*) as tests_count,
                       AVG(percentage) as avg_score,
                       MAX(timestamp) as last_attempt
                FROM test_results 
                WHERE user_id = ?
                GROUP BY topic
                ORDER BY last_attempt DESC
            ''', (user_id,))
            topic_stats = cursor.fetchall()
            
            # Статистика по ошибкам
            cursor.execute('''
                SELECT topic,
                       COUNT(DISTINCT question_text) as unique_errors,
                       SUM(error_count) as total_errors,
                       MAX(timestamp) as last_error
                FROM user_errors 
                WHERE user_id = ?
                GROUP BY topic
                ORDER BY total_errors DESC
            ''', (user_id,))
            error_stats = cursor.fetchall()
            
            # Последние ошибки (топ-10)
            cursor.execute('''
                SELECT question_text, topic, error_count, timestamp
                FROM user_errors 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (user_id,))
            recent_errors = cursor.fetchall()
            
            # Прогресс по дням (последние 30 дней)
            cursor.execute('''
                SELECT DATE(timestamp) as test_date,
                       COUNT(*) as tests_count,
                       AVG(percentage) as avg_score
                FROM test_results 
                WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY test_date DESC
            ''', (user_id,))
            daily_progress = cursor.fetchall()
            
            return {
                'user_info': {
                    'user_id': user_info[0],
                    'username': user_info[1],
                    'full_name': user_info[2] or user_info[6],  # Приоритет текущему имени
                    'grade': user_info[3] or user_info[7],      # Приоритет текущему классу
                    'language': user_info[4],
                    'last_activity': user_info[5],
                    'added_to_whitelist': user_info[8]
                },
                'test_statistics': {
                    'total_tests': test_stats[0] if test_stats else 0,
                    'avg_score': round(test_stats[1] or 0, 1),
                    'min_score': test_stats[2] or 0,
                    'max_score': test_stats[3] or 0,
                    'first_test': test_stats[4],
                    'last_test': test_stats[5]
                },
                'topic_performance': [
                    {
                        'topic': row[0],
                        'tests_count': row[1],
                        'avg_score': round(row[2], 1),
                        'last_attempt': row[3]
                    }
                    for row in topic_stats
                ],
                'error_analysis': [
                    {
                        'topic': row[0],
                        'unique_errors': row[1],
                        'total_errors': row[2],
                        'last_error': row[3]
                    }
                    for row in error_stats
                ],
                'recent_errors': [
                    {
                        'question': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                        'topic': row[1],
                        'error_count': row[2],
                        'timestamp': row[3]
                    }
                    for row in recent_errors
                ],
                'daily_progress': [
                    {
                        'date': row[0],
                        'tests_count': row[1],
                        'avg_score': round(row[2], 1)
                    }
                    for row in daily_progress
                ]
            }

    def get_all_students_summary(self) -> List[Dict[str, Any]]:
        """Получить краткую сводку по всем ученикам для админов."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем всех учеников из whitelist с их статистикой
            cursor.execute('''
                SELECT au.user_id, au.username, au.full_name, au.grade, au.is_active, au.added_at,
                       u.last_activity,
                       COUNT(tr.id) as total_tests,
                       AVG(tr.percentage) as avg_score,
                       COUNT(DISTINCT ue.question_text) as unique_errors,
                       MAX(tr.timestamp) as last_test
                FROM allowed_users au
                LEFT JOIN users u ON (au.user_id = u.user_id OR au.username = u.username)
                LEFT JOIN test_results tr ON u.user_id = tr.user_id
                LEFT JOIN user_errors ue ON u.user_id = ue.user_id
                GROUP BY au.id, au.user_id, au.username, au.full_name, au.grade, au.is_active, au.added_at, u.last_activity
                ORDER BY au.added_at DESC
            ''')
            
            results = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'grade': row[3],
                    'is_active': bool(row[4]),
                    'added_at': row[5],
                    'last_activity': row[6],
                    'total_tests': row[7] or 0,
                    'avg_score': round(row[8] or 0, 1),
                    'unique_errors': row[9] or 0,
                    'last_test': row[10],
                    'status': 'Активен' if row[6] and row[10] else 'Неактивен'
                }
                for row in results
            ]

    def get_class_statistics(self, grade: int = None) -> Dict[str, Any]:
        """Получить статистику по классу или всем классам."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if grade:
                # Статистика по конкретному классу
                cursor.execute('''
                    SELECT au.grade,
                           COUNT(DISTINCT au.id) as students_count,
                           COUNT(DISTINCT tr.user_id) as active_students,
                           COUNT(tr.id) as total_tests,
                           AVG(tr.percentage) as avg_score
                    FROM allowed_users au
                    LEFT JOIN users u ON (au.user_id = u.user_id OR au.username = u.username)
                    LEFT JOIN test_results tr ON u.user_id = tr.user_id
                    WHERE au.grade = ? AND au.is_active = 1
                    GROUP BY au.grade
                ''', (grade,))
            else:
                # Статистика по всем классам
                cursor.execute('''
                    SELECT au.grade,
                           COUNT(DISTINCT au.id) as students_count,
                           COUNT(DISTINCT tr.user_id) as active_students,
                           COUNT(tr.id) as total_tests,
                           AVG(tr.percentage) as avg_score
                    FROM allowed_users au
                    LEFT JOIN users u ON (au.user_id = u.user_id OR au.username = u.username)
                    LEFT JOIN test_results tr ON u.user_id = tr.user_id
                    WHERE au.is_active = 1
                    GROUP BY au.grade
                    ORDER BY au.grade
                ''')
            
            results = cursor.fetchall()
            return {
                'class_stats': [
                    {
                        'grade': row[0],
                        'students_count': row[1],
                        'active_students': row[2],
                        'total_tests': row[3] or 0,
                        'avg_score': round(row[4] or 0, 1),
                        'activity_rate': round((row[2] / row[1] * 100) if row[1] > 0 else 0, 1)
                    }
                    for row in results
                ]
            }

    def update_allowed_user_by_id(self, user_id: int, full_name: str = None, grade: int = None, is_active: bool = None) -> bool:
        """Обновить информацию об ученике по user_id."""
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
                    params.append(user_id)
                    cursor.execute(f'''
                        UPDATE allowed_users 
                        SET {", ".join(updates)}
                        WHERE user_id = ?
                    ''', params)
                    conn.commit()
                    return cursor.rowcount > 0
                return False
        except Exception:
            return False

    def add_allowed_user_with_phone(self, user_id: int = None, username: str = None, 
                                   full_name: str = None, grade: int = None, 
                                   phone_number: str = None, added_by: int = None) -> bool:
        """Добавить пользователя в whitelist с поддержкой номера телефона."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, что есть хотя бы один идентификатор
                if not user_id and not username:
                    return False
                
                cursor.execute('''
                    INSERT INTO allowed_users (user_id, username, full_name, grade, phone_number, added_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, full_name, grade, phone_number, added_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_allowed_user_phone(self, user_id: int = None, username: str = None, 
                                 phone_number: str = None) -> bool:
        """Обновить номер телефона пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute('''
                        UPDATE allowed_users 
                        SET phone_number = ?
                        WHERE user_id = ?
                    ''', (phone_number, user_id))
                elif username:
                    cursor.execute('''
                        UPDATE allowed_users 
                        SET phone_number = ?
                        WHERE username = ?
                    ''', (phone_number, username))
                else:
                    return False
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_student_contact_info(self, user_id: int) -> Dict[str, Any]:
        """Получить контактную информацию ученика."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT au.user_id, au.username, au.full_name, au.grade, au.phone_number,
                       u.username as current_username, u.full_name as current_full_name
                FROM allowed_users au
                LEFT JOIN users u ON au.user_id = u.user_id
                WHERE au.user_id = ? OR au.username = (
                    SELECT username FROM users WHERE user_id = ?
                )
            ''', (user_id, user_id))
            
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'whitelist_username': result[1],
                    'whitelist_full_name': result[2],
                    'grade': result[3],
                    'phone_number': result[4],
                    'current_username': result[5],
                    'current_full_name': result[6],
                    'display_name': result[6] or result[2] or 'Неизвестен',
                    'display_username': result[5] or result[1] or 'не указан'
                }
            return None

    def find_student_by_identifier(self, identifier: str) -> Dict[str, Any]:
        """Найти ученика по любому идентификатору (user_id, username)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Пробуем найти по user_id (если identifier - число)
            try:
                user_id = int(identifier)
                cursor.execute('''
                    SELECT user_id, username, full_name, grade, is_active
                    FROM allowed_users 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'full_name': result[2],
                        'grade': result[3],
                        'is_active': bool(result[4]),
                        'found_by': 'user_id'
                    }
            except ValueError:
                pass
            
            # Пробуем найти по username
            cursor.execute('''
                SELECT user_id, username, full_name, grade, is_active
                FROM allowed_users 
                WHERE username = ? OR username = ?
            ''', (identifier, identifier.lstrip('@')))
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'full_name': result[2],
                    'grade': result[3],
                    'is_active': bool(result[4]),
                    'found_by': 'username'
                }
            
            return None

    def get_comprehensive_user_access_check(self, user_id: int, username: str = None) -> Dict[str, Any]:
        """Комплексная проверка доступа пользователя с детальной информацией."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем админские права
            is_admin = self.is_admin(user_id)
            is_super_admin = self.is_super_admin(user_id)
            
            # Ищем в whitelist по user_id
            whitelist_by_id = None
            cursor.execute('''
                SELECT user_id, username, full_name, grade, is_active, added_at
                FROM allowed_users WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                whitelist_by_id = {
                    'user_id': result[0],
                    'username': result[1],
                    'full_name': result[2],
                    'grade': result[3],
                    'is_active': bool(result[4]),
                    'added_at': result[5]
                }
            
            # Ищем в whitelist по username
            whitelist_by_username = None
            if username:
                cursor.execute('''
                    SELECT user_id, username, full_name, grade, is_active, added_at
                    FROM allowed_users WHERE username = ?
                ''', (username,))
                result = cursor.fetchone()
                if result:
                    whitelist_by_username = {
                        'user_id': result[0],
                        'username': result[1],
                        'full_name': result[2],
                        'grade': result[3],
                        'is_active': bool(result[4]),
                        'added_at': result[5]
                    }
            
            return {
                'user_id': user_id,
                'username': username,
                'is_admin': is_admin,
                'is_super_admin': is_super_admin,
                'has_access': is_admin or (whitelist_by_id and whitelist_by_id['is_active']) or (whitelist_by_username and whitelist_by_username['is_active']),
                'whitelist_by_id': whitelist_by_id,
                'whitelist_by_username': whitelist_by_username,
                'needs_sync': whitelist_by_id and whitelist_by_username and whitelist_by_id['user_id'] != whitelist_by_username['user_id']
            }

    def update_user_phone(self, user_id: int, phone_number: str) -> bool:
        """Обновить номер телефона пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET phone_number = ?
                    WHERE user_id = ?
                ''', (phone_number, user_id))
                
                # Также обновляем в allowed_users если есть
                cursor.execute('''
                    UPDATE allowed_users 
                    SET phone_number = ?
                    WHERE user_id = ?
                ''', (phone_number, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] Ошибка обновления номера телефона: {e}")
            return False
    
    def get_user_phone(self, user_id: int) -> Optional[str]:
        """Получить номер телефона пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT phone_number FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def find_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Найти пользователя по номеру телефона."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, grade, phone_number
                FROM users 
                WHERE phone_number = ?
            ''', (phone_number,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'full_name': result[2],
                    'grade': result[3],
                    'phone_number': result[4]
                }
            return None

    def auto_setup_user_from_whitelist(self, user_id: int, username: str) -> Dict[str, Any]:
        """
        Автоматическая настройка пользователя из whitelist при первом входе.
        Возвращает информацию о том, что было настроено.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Ищем пользователя в whitelist по user_id или username
                cursor.execute('''
                    SELECT user_id, username, full_name, grade, phone_number, is_active, added_at
                    FROM allowed_users 
                    WHERE (user_id = ? OR username = ?) AND is_active = 1
                    ORDER BY user_id IS NOT NULL DESC, added_at DESC
                    LIMIT 1
                ''', (user_id, username))
                
                whitelist_data = cursor.fetchone()
                
                if not whitelist_data:
                    return {
                        'success': False,
                        'reason': 'not_in_whitelist',
                        'message': 'Пользователь не найден в списке разрешенных'
                    }
                
                wl_user_id, wl_username, wl_full_name, wl_grade, wl_phone, wl_active, wl_added_at = whitelist_data
                
                # Проверяем, есть ли уже запись в users
                cursor.execute('SELECT user_id, full_name, grade, phone_number FROM users WHERE user_id = ?', (user_id,))
                existing_user = cursor.fetchone()
                
                # Определяем, что нужно обновить
                updates_made = []
                
                if existing_user:
                    # Обновляем существующую запись
                    current_name, current_grade, current_phone = existing_user[1], existing_user[2], existing_user[3]
                    
                    update_fields = []
                    update_params = []
                    
                    if wl_full_name and wl_full_name != current_name:
                        update_fields.append("full_name = ?")
                        update_params.append(wl_full_name)
                        updates_made.append(f"ФИО: {wl_full_name}")
                    
                    if wl_grade and wl_grade != current_grade:
                        update_fields.append("grade = ?")
                        update_params.append(wl_grade)
                        updates_made.append(f"Класс: {wl_grade}")
                    
                    if wl_phone and wl_phone != current_phone:
                        update_fields.append("phone_number = ?")
                        update_params.append(wl_phone)
                        updates_made.append(f"Телефон: {wl_phone}")
                    
                    # Всегда обновляем username и last_activity
                    update_fields.extend(["username = ?", "last_activity = CURRENT_TIMESTAMP"])
                    update_params.extend([username])
                    
                    if update_fields:
                        update_params.append(user_id)
                        cursor.execute(f'''
                            UPDATE users 
                            SET {", ".join(update_fields)}
                            WHERE user_id = ?
                        ''', update_params)
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO users (user_id, username, full_name, grade, phone_number, last_activity)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (user_id, username, wl_full_name, wl_grade, wl_phone))
                    
                    if wl_full_name:
                        updates_made.append(f"ФИО: {wl_full_name}")
                    if wl_grade:
                        updates_made.append(f"Класс: {wl_grade}")
                    if wl_phone:
                        updates_made.append(f"Телефон: {wl_phone}")
                
                # Обновляем user_id в whitelist если его не было
                if not wl_user_id or wl_user_id != user_id:
                    cursor.execute('''
                        UPDATE allowed_users 
                        SET user_id = ?
                        WHERE username = ? AND (user_id IS NULL OR user_id != ?)
                    ''', (user_id, username, user_id))
                    updates_made.append("Синхронизирован user_id в whitelist")
                
                conn.commit()
                
                return {
                    'success': True,
                    'auto_configured': len(updates_made) > 0,
                    'updates_made': updates_made,
                    'user_data': {
                        'full_name': wl_full_name,
                        'grade': wl_grade,
                        'phone_number': wl_phone,
                        'username': wl_username or username
                    },
                    'message': f"Автоматически настроено: {', '.join(updates_made)}" if updates_made else "Данные уже актуальны"
                }
                
        except Exception as e:
            print(f"[ERROR] Ошибка автоматической настройки пользователя {user_id}: {e}")
            return {
                'success': False,
                'reason': 'database_error',
                'message': f'Ошибка базы данных: {str(e)}'
            } 

    def get_admin_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin information by user_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, is_super_admin, created_at, created_by
                FROM admins 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'is_super_admin': bool(row[3]),
                    'created_at': row[4],
                    'created_by': row[5]
                }
            return None

    def update_admin_info(self, user_id: int, full_name: str) -> bool:
        """Update admin's full name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE admins 
                    SET full_name = ? 
                    WHERE user_id = ?
                ''', (full_name, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logging.error(f"Error updating admin info: {e}")
            return False

    def get_all_admins(self) -> List[Dict]:
        """Get list of all admins."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, is_super_admin, created_at
                FROM admins
                ORDER BY is_super_admin DESC, created_at ASC
            ''')
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'is_super': bool(row[3]),
                    'added_at': row[4]
                }
                for row in rows
            ]
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ЯЗЫКАМИ =====
    
    def clear_user_data_on_language_change(self, user_id: int) -> None:
        """Очищает user_errors и test_results при смене языка пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Очищаем ошибки пользователя
                cursor.execute('DELETE FROM user_errors WHERE user_id = ?', (user_id,))
                deleted_errors = cursor.rowcount
                
                # Очищаем результаты тестов
                cursor.execute('DELETE FROM test_results WHERE user_id = ?', (user_id,))
                deleted_results = cursor.rowcount
                
                conn.commit()
                print(f"[LOG] Очищены данные пользователя {user_id}: {deleted_errors} ошибок, {deleted_results} результатов")
                
        except Exception as e:
            print(f"[ERROR] Ошибка очистки данных пользователя {user_id}: {e}")
    
    def get_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Получает темы для конкретного языка через main_topics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT mt.name as main_topic, st.name as subtopic, st.id
                    FROM main_topics mt
                    JOIN subtopics st ON mt.id = st.main_topic_id
                    WHERE mt.language = ?
                '''
                params = [language]
                
                if active_only:
                    query += ' AND mt.is_active = 1 AND st.is_active = 1'
                
                query += ' ORDER BY mt.order_index, st.order_index'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Группируем по основным темам
                topics_dict = {}
                for main_topic, subtopic, subtopic_id in rows:
                    if main_topic not in topics_dict:
                        topics_dict[main_topic] = []
                    topics_dict[main_topic].append({
                        'id': subtopic_id,
                        'name': subtopic,
                        'language': language  # Наследуется от main_topic
                    })
                
                return topics_dict
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения тем по языку {language}: {e}")
            return {}
    
    def get_questions_by_user_language(self, user_id: int, topic: str = None) -> List[Dict]:
        """Получает вопросы на языке пользователя через связь с main_topics."""
        try:
            user_language = self.get_user_language(user_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем вопросы через связь с темами по языку main_topics
                query = '''
                    SELECT DISTINCT q.id, q.topic, q.question, q.answer, q.explanation, 
                           q.incorrect_options, q.question_type, q.source, q.image_path
                    FROM questions q
                    JOIN subtopics st ON q.topic = st.name
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    WHERE mt.language = ?
                '''
                params = [user_language]
                
                if topic:
                    query += ' AND q.topic = ?'
                    params.append(topic)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'topic': row[1],
                        'question': row[2],
                        'answer': row[3],
                        'explanation': row[4],
                        'incorrect_options': row[5],
                        'question_type': row[6],
                        'source': row[7],
                        'image_path': row[8]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения вопросов по языку пользователя {user_id}: {e}")
            return []
    
    def add_topic_with_language(self, name: str, language: str, main_topic_name: str, created_by: int = None) -> bool:
        """Добавляет новую тему. Язык наследуется от main_topic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Находим ID основной темы с нужным языком
                cursor.execute('SELECT id FROM main_topics WHERE name = ? AND language = ?', (main_topic_name, language))
                main_topic_result = cursor.fetchone()
                
                if not main_topic_result:
                    print(f"[ERROR] Основная тема '{main_topic_name}' с языком '{language}' не найдена")
                    return False
                
                main_topic_id = main_topic_result[0]
                
                # Добавляем подтему (язык наследуется от main_topic)
                cursor.execute('''
                    INSERT INTO subtopics (main_topic_id, name, is_active)
                    VALUES (?, ?, 1)
                ''', (main_topic_id, name))
                
                conn.commit()
                print(f"[LOG] Добавлена тема '{name}' в раздел '{main_topic_name}' ({language})")
                return True
                
        except sqlite3.IntegrityError:
            print(f"[ERROR] Тема '{name}' уже существует в разделе '{main_topic_name}'")
            return False
        except Exception as e:
            print(f"[ERROR] Ошибка добавления темы: {e}")
            return False
    
    def get_topics_with_language_info(self, active_only: bool = True, for_admin: bool = False) -> List[Dict[str, Any]]:
        """Получает темы с информацией о языке для админов или учеников."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT mt.name as main_topic, st.name as subtopic, mt.language, 
                           COUNT(q.id) as question_count, st.id
                    FROM main_topics mt
                    JOIN subtopics st ON mt.id = st.main_topic_id
                    LEFT JOIN questions q ON st.name = q.topic
                '''
                
                if active_only:
                    query += ' WHERE mt.is_active = 1 AND st.is_active = 1'
                
                query += '''
                    GROUP BY mt.name, st.name, mt.language, st.id
                    ORDER BY mt.order_index, st.order_index
                '''
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                topics_dict = {}
                for main_topic, subtopic, language, question_count, subtopic_id in rows:
                    if main_topic not in topics_dict:
                        topics_dict[main_topic] = []
                    
                    # Формируем название в зависимости от роли
                    if for_admin:
                        # Для админов: показываем количество вопросов и язык
                        display_name = f"{subtopic} ({question_count}) [{language}]"
                    else:
                        # Для учеников: только название темы
                        display_name = subtopic
                    
                    topics_dict[main_topic].append({
                        'id': subtopic_id,
                        'name': subtopic,
                        'display_name': display_name,
                        'language': language,
                        'question_count': question_count
                    })
                
                return topics_dict
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения тем с информацией о языке: {e}")
            return {}

    def create_kazakh_main_topics(self) -> bool:
        """Создает казахские версии основных разделов."""
        try:
            try:
                from config.constants_kk import MAIN_TOPICS_KK, TOPIC_HIERARCHY_KK
            except ImportError:
                print("[ERROR] config.constants_kk не найден")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем существующие русские разделы
                cursor.execute('SELECT id, name, order_index FROM main_topics WHERE language = "ru"')
                russian_topics = cursor.fetchall()
                
                created_count = 0
                for topic_id, russian_name, order_index in russian_topics:
                    # Проверяем, есть ли перевод для этого раздела
                    if russian_name in MAIN_TOPICS_KK:
                        kazakh_name = MAIN_TOPICS_KK[russian_name]
                        
                        # Проверяем, не существует ли уже казахская версия
                        cursor.execute('SELECT id FROM main_topics WHERE name = ? AND language = "kk"', (kazakh_name,))
                        if cursor.fetchone():
                            continue  # Уже существует
                        
                        # Создаем казахскую версию основного раздела
                        cursor.execute('''
                            INSERT INTO main_topics (name, order_index, language, is_active)
                            VALUES (?, ?, "kk", 1)
                        ''', (kazakh_name, order_index))
                        
                        kazakh_main_topic_id = cursor.lastrowid
                        created_count += 1
                        
                        # Создаем казахские подтемы для этого раздела
                        if kazakh_name in TOPIC_HIERARCHY_KK:
                            kazakh_subtopics = TOPIC_HIERARCHY_KK[kazakh_name]
                            for subtopic_order, kazakh_subtopic in enumerate(kazakh_subtopics):
                                # Проверяем, не существует ли уже эта подтема
                                cursor.execute('''
                                    SELECT id FROM subtopics 
                                    WHERE main_topic_id = ? AND name = ?
                                ''', (kazakh_main_topic_id, kazakh_subtopic))
                                
                                if not cursor.fetchone():
                                    cursor.execute('''
                                        INSERT INTO subtopics (main_topic_id, name, order_index, is_active)
                                        VALUES (?, ?, ?, 1)
                                    ''', (kazakh_main_topic_id, kazakh_subtopic, subtopic_order))
                
                conn.commit()
                print(f"[LOG] Создано {created_count} казахских основных разделов")
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка создания казахских основных разделов: {e}")
            return False

    def get_main_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получает основные разделы для конкретного языка."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, name, order_index, language, is_active
                    FROM main_topics
                    WHERE language = ?
                '''
                params = [language]
                
                if active_only:
                    query += ' AND is_active = 1'
                
                query += ' ORDER BY order_index'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'order_index': row[2],
                        'language': row[3],
                        'is_active': bool(row[4])
                    }
                    for row in rows
                ]
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения основных разделов по языку {language}: {e}")
            return []

    def get_full_topic_structure_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Получает полную структуру тем (разделы + подтемы) для конкретного языка."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT mt.name as main_topic, mt.id as main_topic_id,
                           st.name as subtopic, st.id as subtopic_id, st.order_index,
                           COUNT(q.id) as question_count
                    FROM main_topics mt
                    LEFT JOIN subtopics st ON mt.id = st.main_topic_id
                    LEFT JOIN questions q ON st.name = q.topic
                    WHERE mt.language = ?
                '''
                params = [language]
                
                if active_only:
                    query += ' AND mt.is_active = 1 AND (st.is_active = 1 OR st.is_active IS NULL)'
                
                query += '''
                    GROUP BY mt.name, mt.id, st.name, st.id, st.order_index
                    ORDER BY mt.order_index, st.order_index
                '''
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                structure = {}
                for main_topic, main_topic_id, subtopic, subtopic_id, subtopic_order, question_count in rows:
                    if main_topic not in structure:
                        structure[main_topic] = []
                    
                    if subtopic:  # Если есть подтема
                        structure[main_topic].append({
                            'id': subtopic_id,
                            'name': subtopic,
                            'order_index': subtopic_order,
                            'question_count': question_count or 0,
                            'has_questions': (question_count or 0) > 0
                        })
                
                return structure
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения структуры тем по языку {language}: {e}")
            return {}

    def sync_subtopic_languages_with_main_topics(self) -> bool:
        """Синхронизирует подтемы с основными разделами (удаляет поле language из subtopics)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли поле language в subtopics
                cursor.execute("PRAGMA table_info(subtopics)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'language' in columns:
                    print("[LOG] Найдено поле language в subtopics, требуется миграция")
                    print("[LOG] Запустите скрипт remove_subtopic_language.py для удаления поля")
                    return False
                else:
                    print("[LOG] Поле language отсутствует в subtopics - структура корректна")
                    return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка проверки структуры subtopics: {e}")
            return False

    def auto_update_username_from_telegram(self, user_id: int, username: str) -> bool:
        """
        Автоматически обновляет username пользователя при каждом взаимодействии с ботом.
        Это гарантирует актуальность данных без участия админа.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем username в таблице users
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (username, user_id))
                
                # Обновляем username в allowed_users если запись существует
                cursor.execute('''
                    UPDATE allowed_users 
                    SET username = ?
                    WHERE user_id = ? AND (username IS NULL OR username != ?)
                ''', (username, user_id, username))
                
                conn.commit()
                
                # Логируем только если произошло обновление
                if cursor.rowcount > 0:
                    print(f"[LOG] Автоматически обновлен username для user_id {user_id}: @{username}")
                
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка автоматического обновления username для {user_id}: {e}")
            return False

    def get_user_display_info(self, user_id: int) -> Dict[str, Any]:
        """
        Получает отображаемую информацию о пользователе из всех источников.
        Приоритет: текущие данные users -> whitelist -> базовые данные Telegram.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем данные из users
            cursor.execute('''
                SELECT username, full_name, grade, phone_number, language
                FROM users WHERE user_id = ?
            ''', (user_id,))
            user_data = cursor.fetchone()
            
            # Получаем данные из allowed_users
            cursor.execute('''
                SELECT username, full_name, grade, phone_number
                FROM allowed_users WHERE user_id = ?
            ''', (user_id,))
            whitelist_data = cursor.fetchone()
            
            # Формируем итоговую информацию с приоритетами
            result = {
                'user_id': user_id,
                'username': None,
                'full_name': None,
                'grade': None,
                'phone_number': None,
                'language': 'ru',
                'has_complete_info': False
            }
            
            # Заполняем данными из users (высший приоритет)
            if user_data:
                result.update({
                    'username': user_data[0],
                    'full_name': user_data[1],
                    'grade': user_data[2],
                    'phone_number': user_data[3],
                    'language': user_data[4] or 'ru'
                })
            
            # Дополняем данными из whitelist если чего-то не хватает
            if whitelist_data:
                if not result['username'] and whitelist_data[0]:
                    result['username'] = whitelist_data[0]
                if not result['full_name'] and whitelist_data[1]:
                    result['full_name'] = whitelist_data[1]
                if not result['grade'] and whitelist_data[2]:
                    result['grade'] = whitelist_data[2]
                if not result['phone_number'] and whitelist_data[3]:
                    result['phone_number'] = whitelist_data[3]
            
            # Проверяем полноту информации
            result['has_complete_info'] = bool(
                result['full_name'] and 
                result['grade'] and 
                result['username']
            )
            
            return result