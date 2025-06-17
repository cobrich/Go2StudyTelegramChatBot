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
        """Initialize database with all required tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Create admins table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin BOOLEAN DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create allowed_users table
            cursor.execute('''
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
                    FOREIGN KEY (added_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Create unique index for user_id
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_allowed_users_user_id 
                ON allowed_users(user_id) WHERE user_id IS NOT NULL
            ''')
            
            # Create main_topics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    language TEXT DEFAULT "ru",
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Create subtopics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (main_topic_id) REFERENCES main_topics(id),
                    FOREIGN KEY (created_by) REFERENCES admins(user_id)
                )
            ''')
            
            # Create questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create test_results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES allowed_users(user_id)
                )
            ''')
            
            # Migrate user_errors table to new structure
            self._migrate_user_errors_table(cursor)
            
            # Migrate questions to support topic_id instead of topic name
            self._migrate_questions_topic_id(cursor)
            
            # Add missing columns to existing tables if they don't exist
            try:
                cursor.execute('ALTER TABLE allowed_users ADD COLUMN current_topic TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE allowed_users ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE allowed_users ADD COLUMN has_access BOOLEAN DEFAULT 1')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            conn.commit()
            
            # Initialize base topic structure if empty
            cursor.execute('SELECT COUNT(*) FROM main_topics')
            if cursor.fetchone()[0] == 0:
                self._initialize_base_topics()
                
            # Create Kazakh main topics if they don't exist
            self.create_kazakh_main_topics()

    def _migrate_user_errors_table(self, cursor):
        """Migrate user_errors table to new structure with question_id."""
        try:
            # Check if old user_errors table exists and has old structure
            cursor.execute("PRAGMA table_info(user_errors)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # If table doesn't exist or already has new structure, create new table
            if not columns or 'question_id' in columns:
                if not columns:  # Table doesn't exist
                    cursor.execute('''
                        CREATE TABLE user_errors (
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
                    ''')
                    logging.info("Created new user_errors table with question_id structure")
                return
            
            # Old structure exists, need to migrate
            logging.info("Starting migration of user_errors table to new structure...")
            
            # Create new table with new structure
            cursor.execute('''
                CREATE TABLE user_errors_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES allowed_users(user_id),
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    UNIQUE(user_id, question_id)
                )
            ''')
            
            # Migrate data from old table to new table
            # Old structure: user_id, topic, question_text, user_answer, correct_answer, explanation, error_count, timestamp
            # New structure: user_id, question_id, topic, user_answer, correct_answer, error_count, first_error_date, last_error_date
            cursor.execute('''
                INSERT INTO user_errors_new (user_id, question_id, topic, user_answer, correct_answer, error_count, first_error_date, last_error_date)
                SELECT 
                    ue.user_id,
                    COALESCE(q.id, -1) as question_id,  -- Use -1 for questions not found in questions table
                    ue.topic,
                    ue.user_answer,
                    ue.correct_answer,
                    ue.error_count,
                    ue.timestamp as first_error_date,
                    ue.timestamp as last_error_date
                FROM user_errors ue
                LEFT JOIN questions q ON q.question = ue.question_text
                WHERE COALESCE(q.id, -1) != -1  -- Only migrate records where we found matching question
            ''')
            
            migrated_count = cursor.rowcount
            logging.info(f"Migrated {migrated_count} user_errors records to new structure")
            
            # Drop old table and rename new table
            cursor.execute('DROP TABLE user_errors')
            cursor.execute('ALTER TABLE user_errors_new RENAME TO user_errors')
            
            logging.info("Successfully migrated user_errors table to new structure")
            
        except Exception as e:
            logging.error(f"Error during user_errors migration: {e}")
            # If migration fails, create new empty table with new structure
            try:
                cursor.execute('DROP TABLE IF EXISTS user_errors_new')
                cursor.execute('DROP TABLE IF EXISTS user_errors')
                cursor.execute('''
                    CREATE TABLE user_errors (
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
                ''')
                logging.info("Created new user_errors table after migration failure")
            except Exception as create_error:
                logging.error(f"Failed to create new user_errors table: {create_error}")

    def _migrate_questions_to_many_to_many(self, cursor):
        """Migrate questions to support many-to-many relationship."""
        try:
            # Check if old questions table exists and has old structure
            cursor.execute("PRAGMA table_info(questions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # If table doesn't exist or already has new structure, create new table
            if not columns or 'topic' in columns:
                if not columns:  # Table doesn't exist
                    cursor.execute('''
                        CREATE TABLE questions_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            topic TEXT NOT NULL,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            explanation TEXT,
                            incorrect_options TEXT,
                            question_type TEXT DEFAULT 'standard',
                            source TEXT DEFAULT 'db',
                            image_path TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    logging.info("Created new questions table with many-to-many relationship")
                return
            
            # Old structure exists, need to migrate
            logging.info("Starting migration of questions table to new structure...")
            
            # Create new table with new structure
            cursor.execute('''
                CREATE TABLE questions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migrate data from old table to new table
            # Old structure: id, topic, question, answer, explanation, incorrect_options, question_type, source, image_path, timestamp
            # New structure: id, topic, question, answer, explanation, incorrect_options, question_type, source, image_path, timestamp
            cursor.execute('''
                INSERT INTO questions_new (id, topic, question, answer, explanation, incorrect_options, question_type, source, image_path, created_at)
                SELECT 
                    q.id,
                    q.topic,
                    q.question,
                    q.answer,
                    q.explanation,
                    q.incorrect_options,
                    q.question_type,
                    q.source,
                    q.image_path,
                    q.timestamp as created_at
                FROM questions q
            ''')
            
            migrated_count = cursor.rowcount
            logging.info(f"Migrated {migrated_count} questions records to new structure")
            
            # Drop old table and rename new table
            cursor.execute('DROP TABLE questions')
            cursor.execute('ALTER TABLE questions_new RENAME TO questions')
            
            logging.info("Successfully migrated questions table to new structure")
            
        except Exception as e:
            logging.error(f"Error during questions migration: {e}")
            # If migration fails, create new empty table with new structure
            try:
                cursor.execute('DROP TABLE IF EXISTS questions_new')
                cursor.execute('DROP TABLE IF EXISTS questions')
                cursor.execute('''
                    CREATE TABLE questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        explanation TEXT,
                        incorrect_options TEXT,
                        question_type TEXT DEFAULT 'standard',
                        source TEXT DEFAULT 'db',
                        image_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logging.info("Created new questions table after migration failure")
            except Exception as create_error:
                logging.error(f"Failed to create new questions table: {create_error}")

    def _migrate_questions_topic_id(self, cursor):
        """
        Миграция: добавление topic_id в таблицу questions и заполнение данных
        """
        try:
            # Проверяем есть ли уже колонка topic_id
            cursor.execute("PRAGMA table_info(questions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'topic_id' in columns:
                logging.info("[MIGRATE] Колонка topic_id уже существует в таблице questions")
                return True
            
            logging.info("[MIGRATE] Добавляем колонку topic_id в таблицу questions...")
            
            # Добавляем колонку topic_id
            cursor.execute('ALTER TABLE questions ADD COLUMN topic_id INTEGER')
            
            # Заполняем topic_id на основе существующих названий тем
            logging.info("[MIGRATE] Заполняем topic_id для существующих вопросов...")
            cursor.execute('''
                UPDATE questions 
                SET topic_id = (
                    SELECT id FROM subtopics 
                    WHERE subtopics.name = questions.topic
                )
                WHERE topic_id IS NULL
            ''')
            updated_questions = cursor.rowcount
            logging.info(f"[MIGRATE] Обновлено {updated_questions} вопросов с topic_id")
            
            # Найдем вопросы которые не смогли связать с темами (орфанные)
            cursor.execute('SELECT DISTINCT topic FROM questions WHERE topic_id IS NULL')
            orphan_topics = cursor.fetchall()
            
            if orphan_topics:
                logging.info(f"[MIGRATE] Найдено {len(orphan_topics)} орфанных тем, создаем их...")
                
                for (topic_name,) in orphan_topics:
                    # Создаем недостающую тему с дефолтным main_topic_id = 1
                    cursor.execute('''
                        INSERT INTO subtopics (name, main_topic_id, is_active) 
                        VALUES (?, 1, 1)
                    ''', (topic_name,))
                    
                    new_topic_id = cursor.lastrowid
                    logging.info(f"[MIGRATE] Создана тема '{topic_name}' с ID {new_topic_id}")
                    
                    # Обновляем topic_id для вопросов этой темы
                    cursor.execute('''
                        UPDATE questions 
                        SET topic_id = ? 
                        WHERE topic = ? AND topic_id IS NULL
                    ''', (new_topic_id, topic_name))
                    
                    updated = cursor.rowcount
                    logging.info(f"[MIGRATE] Связано {updated} вопросов с темой '{topic_name}'")
            
            # Добавляем FOREIGN KEY constraint (будет работать для новых записей)
            # Примечание: в SQLite нельзя добавить FK к существующей таблице,
            # но мы можем использовать его в новых операциях
            
            # Финальная проверка
            cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id IS NULL')
            remaining_orphans = cursor.fetchone()[0]
            
            if remaining_orphans > 0:
                logging.warning(f"[MIGRATE] Остались {remaining_orphans} вопросов без topic_id")
                return False
            
            logging.info("[MIGRATE] ✅ Миграция topic_id завершена успешно")
            return True
            
        except Exception as e:
            logging.error(f"[MIGRATE] Ошибка при миграции topic_id: {e}")
            return False

    def _migrate_remove_topic_column(self, cursor):
        """
        Миграция: полное удаление колонки topic из таблицы questions
        
        Эта миграция должна выполняться ПОСЛЕ _migrate_questions_topic_id
        и ПОСЛЕ обновления всего кода для использования topic_id
        """
        try:
            # Проверяем что все questions имеют topic_id
            cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id IS NULL')
            orphan_count = cursor.fetchone()[0]
            
            if orphan_count > 0:
                logging.error(f"[MIGRATE] Найдено {orphan_count} вопросов без topic_id! Миграция прервана.")
                logging.error("[MIGRATE] Сначала выполните _migrate_questions_topic_id()")
                return False
            
            # Проверяем что колонка topic_id существует
            cursor.execute("PRAGMA table_info(questions)")
            columns_info = cursor.fetchall()
            columns = [column[1] for column in columns_info]
            
            if 'topic_id' not in columns:
                logging.error("[MIGRATE] Колонка topic_id не найдена! Сначала выполните _migrate_questions_topic_id()")
                return False
            
            if 'topic' not in columns:
                logging.info("[MIGRATE] Колонка topic уже удалена")
                return True
            
            logging.info("[MIGRATE] Начинаем удаление колонки topic из таблицы questions...")
            
            # В SQLite нельзя просто DROP COLUMN, нужно пересоздать таблицу
            logging.info("[MIGRATE] Создаём новую таблицу questions без колонки topic...")
            
            # 1. Создаём новую таблицу без колонки topic (на основе реальной структуры)
            cursor.execute('''
                CREATE TABLE questions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    incorrect_options TEXT,
                    question_type TEXT DEFAULT 'standard',
                    source TEXT DEFAULT 'db',
                    image_path TEXT,
                    topic_id INTEGER NOT NULL,
                    FOREIGN KEY (topic_id) REFERENCES subtopics(id)
                )
            ''')
            
            # 2. Копируем данные БЕЗ колонки topic
            logging.info("[MIGRATE] Копируем данные без колонки topic...")
            cursor.execute('''
                INSERT INTO questions_new 
                (id, question, answer, explanation, incorrect_options, 
                 question_type, source, image_path, topic_id)
                SELECT id, question, answer, explanation, incorrect_options,
                       question_type, source, image_path, topic_id
                FROM questions
            ''')
            
            copied_count = cursor.rowcount
            logging.info(f"[MIGRATE] Скопировано {copied_count} вопросов")
            
            # 3. Удаляем старую таблицу
            logging.info("[MIGRATE] Удаляем старую таблицу questions...")
            cursor.execute('DROP TABLE questions')
            
            # 4. Переименовываем новую
            logging.info("[MIGRATE] Переименовываем новую таблицу...")
            cursor.execute('ALTER TABLE questions_new RENAME TO questions')
            
            # 5. Создаём VIEW для обратной совместимости (опционально)
            logging.info("[MIGRATE] Создаём VIEW для обратной совместимости...")
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS questions_with_topic AS
                SELECT q.*, s.name AS topic 
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
            ''')
            
            logging.info("[MIGRATE] ✅ Колонка topic успешно удалена из таблицы questions")
            logging.info("[MIGRATE] ✅ Создан VIEW questions_with_topic для обратной совместимости")
            return True
            
        except Exception as e:
            logging.error(f"[MIGRATE] Ошибка при удалении колонки topic: {e}")
            return False

    def _get_connection(self):
        """Get database connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active with current topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
                SET is_active = 1, current_topic = ?, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (topic, user_id))
            conn.commit()

    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive and clear current topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
                SET is_active = 0, current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def is_user_active(self, user_id: int) -> bool:
        """Check if user is currently active (taking a test)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])

    def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
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
            logging.info(f"[DEBUG][add_user_error] user_id={user_id}, topic={topic}, question_text={question_text[:100]}..., user_answer_text={user_answer_text}, correct_answer_text={correct_answer_text}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, find the question_id by question text
                cursor.execute('SELECT id FROM questions WHERE question = ? LIMIT 1', (question_text,))
                question_result = cursor.fetchone()
                
                if not question_result:
                    logging.warning(f"[DEBUG][add_user_error] Question not found in database: {question_text[:100]}...")
                    return
                
                question_id = question_result[0]
                
                # Check if error already exists for this user and question
                cursor.execute('''
                    SELECT id, error_count FROM user_errors 
                    WHERE user_id = ? AND question_id = ?
                ''', (user_id, question_id))
                result = cursor.fetchone()
                
                if result:
                    error_id, current_count = result
                    cursor.execute('''
                        UPDATE user_errors 
                        SET error_count = error_count + 1,
                            last_error_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (error_id,))
                    logging.info(f"[DEBUG][add_user_error] Updated error_count for id={error_id}, question_id={question_id}")
                else:
                    cursor.execute('''
                        INSERT INTO user_errors 
                        (user_id, question_id, topic, user_answer, correct_answer)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, question_id, topic, user_answer_text, correct_answer_text))
                    logging.info(f"[DEBUG][add_user_error] Inserted new error for user_id={user_id}, question_id={question_id}")
                
                conn.commit()
                
                # Логируем количество строк и последние 3 записи
                cursor.execute('SELECT COUNT(*) FROM user_errors')
                count = cursor.fetchone()[0]
                logging.info(f"[DEBUG][add_user_error] user_errors row count after commit: {count}")
                cursor.execute('SELECT id, user_id, question_id, error_count FROM user_errors ORDER BY id DESC LIMIT 3')
                last_rows = cursor.fetchall()
                logging.info(f"[DEBUG][add_user_error] last 3 rows: {last_rows}")
                
        except Exception as e:
            logging.error(f"[DEBUG][add_user_error] Exception: {e}")

    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count for a question and remove if reaches 0."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find question_id by question text
                cursor.execute('SELECT id FROM questions WHERE question = ? LIMIT 1', (question_text,))
                question_result = cursor.fetchone()
                
                if not question_result:
                    logging.warning(f"[DEBUG][decrement_error_count] Question not found: {question_text[:100]}...")
                    return
                
                question_id = question_result[0]
                
                cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_id = ?', (user_id, question_id))
                before = cursor.fetchone()
                logging.info(f"[DEBUG][decrement_error_count] before: {before}")
                
                cursor.execute('''
                    UPDATE user_errors 
                    SET error_count = error_count - 1
                    WHERE user_id = ? AND question_id = ?
                ''', (user_id, question_id))
                
                cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_id = ?', (user_id, question_id))
                after = cursor.fetchone()
                logging.info(f"[DEBUG][decrement_error_count] after: {after}")
                
                # Remove if count reaches 0
                cursor.execute('''
                    DELETE FROM user_errors 
                    WHERE user_id = ? AND question_id = ? AND error_count <= 0
                ''', (user_id, question_id))
                logging.info(f"[DEBUG][decrement_error_count] deleted if error_count <= 0 for user_id={user_id}, question_id={question_id}")
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"[DEBUG][decrement_error_count] Exception: {e}")

    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for a specific topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to use topic_id approach first (more efficient)
            cursor.execute('''
                SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                       q.question_type, q.source, q.image_path, s.name as topic_name
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE s.name = ? AND s.is_active = 1
                ORDER BY RANDOM()
                LIMIT ?
            ''', (topic, limit))
            
            results = cursor.fetchall()
            
            # If no results with topic_id, fallback to old method
            if not results:
                cursor.execute('''
                    SELECT id, question, answer, explanation, incorrect_options, question_type, source, image_path
                    FROM questions
                    WHERE topic = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (topic, limit))
                results = cursor.fetchall()
                columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 'question_type', 'source', 'image_path']
            else:
                columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 
                          'question_type', 'source', 'image_path', 'topic_name']
            
            return [dict(zip(columns, row)) for row in results]

    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get tasks that user previously answered incorrectly."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to use topic_id approach first (more efficient)
            cursor.execute('''
                SELECT DISTINCT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                       ue.error_count, q.image_path, s.name as topic_name
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                JOIN user_errors ue ON q.id = ue.question_id
                WHERE ue.user_id = ? AND s.name = ? AND s.is_active = 1
                ORDER BY ue.error_count DESC, ue.last_error_date DESC
                LIMIT ?
            ''', (user_id, topic, limit))
            
            results = cursor.fetchall()
            
            # If no results with topic_id, fallback to old method
            if not results:
                cursor.execute('''
                    SELECT DISTINCT q.id, q.question, q.answer, q.explanation, q.incorrect_options, ue.error_count, q.image_path
                    FROM questions q
                    JOIN user_errors ue ON q.id = ue.question_id
                    WHERE ue.user_id = ? AND ue.topic = ?
                    ORDER BY ue.error_count DESC, ue.last_error_date DESC
                    LIMIT ?
                ''', (user_id, topic, limit))
                results = cursor.fetchall()
                columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 'error_count', 'image_path']
            else:
                columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 'error_count', 'image_path', 'topic_name']
            
            return [dict(zip(columns, row)) for row in results]

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
                # Note: We don't delete from allowed_users as it's the main user table
                # Just clear activity and reset user state
                cursor.execute('''
                    UPDATE allowed_users 
                    SET is_active = 0, current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting user data: {e}")
            return False

    def set_all_users_inactive(self):
        """Set all users as inactive."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE allowed_users SET is_active = 0, current_topic = NULL')
            conn.commit()

    def clear_user_activity(self, user_id: int) -> None:
        """Clear user activity and set as inactive."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
                SET is_active = 0, current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def register_user(self, user_id: int, username: str) -> None:
        """Register user if they don't exist in allowed_users."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT user_id FROM allowed_users WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return  # User already exists
            
            # Only register if user is in whitelist (this should not happen normally)
            # This method is kept for backward compatibility
            cursor.execute('''
                INSERT OR IGNORE INTO allowed_users (user_id, username, last_activity)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username))
            conn.commit()

    def add_question(self, question: dict) -> None:
        """Add a new question to the database with automatic topic conversion."""
        # Validate required fields are not None or empty
        required_fields = ['question', 'answer', 'explanation']
        
        # Проверяем наличие topic или topic_id
        has_topic = question.get('topic') and question['topic'].strip()
        has_topic_id = question.get('topic_id') is not None
        
        if not has_topic and not has_topic_id:
            logging.error(f"Cannot add question: neither topic nor topic_id provided. Question data: {question}")
            return
            
        for field in required_fields:
            if not question.get(field):
                logging.error(f"Cannot add question: {field} is None or empty. Question data: {question}")
                return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем наличие колонки topic_id в таблице questions
            cursor.execute("PRAGMA table_info(questions)")
            columns = [column[1] for column in cursor.fetchall()]
            has_topic_id_column = 'topic_id' in columns
            has_topic_column = 'topic' in columns
            
            if has_topic_id_column and has_topic_id:
                # Используем topic_id напрямую (новая архитектура)
                if has_topic_column:
                    # Обе колонки есть - заполняем обе для совместимости
                    topic_name = self._get_topic_name_by_id(question['topic_id'])
                    cursor.execute('''
                        INSERT INTO questions (topic_id, topic, question, answer, explanation, incorrect_options, question_type, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        question['topic_id'],
                        topic_name,
                        question['question'],
                        question['answer'], 
                        question['explanation'],
                        question.get('incorrect_options', ''),
                        question.get('question_type', 'standard'),
                        question.get('source', 'db')
                    ))
                else:
                    # Только topic_id колонка (полная миграция)
                    cursor.execute('''
                        INSERT INTO questions (topic_id, question, answer, explanation, incorrect_options, question_type, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        question['topic_id'],
                        question['question'],
                        question['answer'],
                        question['explanation'],
                        question.get('incorrect_options', ''),
                        question.get('question_type', 'standard'),
                        question.get('source', 'db')
                    ))
            elif has_topic_id_column and has_topic:
                # Конвертируем topic в topic_id (основной сценарий миграции)
                topic_id = self._get_topic_id_by_name(question['topic'])
                if not topic_id:
                    # Создаем недостающую подтему
                    self.add_topic(question['topic'])
                    topic_id = self._get_topic_id_by_name(question['topic'])
                    
                if topic_id:
                    if has_topic_column:
                        # Обе колонки есть - заполняем обе
                        cursor.execute('''
                            INSERT INTO questions (topic_id, topic, question, answer, explanation, incorrect_options, question_type, source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            topic_id,
                            question['topic'],
                            question['question'],
                            question['answer'],
                            question['explanation'],
                            question.get('incorrect_options', ''),
                            question.get('question_type', 'standard'),
                            question.get('source', 'db')
                        ))
                    else:
                        # Только topic_id колонка
                        cursor.execute('''
                            INSERT INTO questions (topic_id, question, answer, explanation, incorrect_options, question_type, source)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            topic_id,
                            question['question'],
                            question['answer'],
                            question['explanation'],
                            question.get('incorrect_options', ''),
                            question.get('question_type', 'standard'),
                            question.get('source', 'db')
                        ))
                else:
                    logging.error(f"Failed to create topic '{question['topic']}' for question")
                    return
            else:
                # Только старая колонка topic (обратная совместимость)
                cursor.execute('''
                    INSERT INTO questions (topic, question, answer, explanation, incorrect_options, question_type, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    question['topic'],
                    question['question'],
                    question['answer'],
                    question['explanation'],
                    question.get('incorrect_options', ''),
                    question.get('question_type', 'standard'),
                    question.get('source', 'db')
                ))
            
            conn.commit()
            logging.info(f"Successfully added question with topic: {question.get('topic', 'N/A')}, topic_id: {question.get('topic_id', 'N/A')}")

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
        """Update user information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
                SET full_name = ?, grade = ?, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (full_name, grade, user_id))
            conn.commit()

    def get_user_info(self, user_id: int):
        """Get user information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT full_name, grade, language FROM allowed_users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()

    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user information (create or update)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO allowed_users (user_id, full_name, grade, last_activity)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, full_name, grade))
            conn.commit()

    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user information with language (create or update)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO allowed_users (user_id, full_name, grade, language, last_activity)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, full_name, grade, language))
            conn.commit()

    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language and clear their data if language changed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем текущий язык пользователя
            cursor.execute('SELECT language FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            current_language = result[0] if result else 'ru'
            
            # Обновляем язык в таблице allowed_users
            cursor.execute('''
                UPDATE allowed_users SET language = ?, last_activity = CURRENT_TIMESTAMP WHERE user_id = ?
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
                SELECT language FROM allowed_users WHERE user_id = ?
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
        """Check if user is in whitelist and has access."""
        # Проверяем, что username не None и не пустой
        if not username:
            return False
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT has_access FROM allowed_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def is_user_allowed_by_id(self, user_id: int) -> bool:
        """Check if user is allowed by user_id and has access."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT has_access FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int, user_id: int = None, language: str = "ru") -> bool:
        """Add user to whitelist with language support."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, что есть хотя бы один идентификатор
                if not user_id:
                    return False
                
                cursor.execute('''
                    INSERT INTO allowed_users (username, full_name, grade, user_id, added_by, language, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
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
                    INSERT INTO allowed_users (user_id, username, full_name, grade, added_by, language, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
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
                    SELECT user_id, username, full_name, grade, is_active, added_at, added_by, language
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
                SELECT st.id, st.name, mt.name as main_topic, st.is_active, st.created_at,
                       COALESCE(q.question_count, 0) as question_count
                FROM subtopics st
                JOIN main_topics mt ON st.main_topic_id = mt.id
                LEFT JOIN (
                    SELECT topic_id, COUNT(*) as question_count
                    FROM questions
                    GROUP BY topic_id
                ) q ON st.id = q.topic_id
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
                    'created_at': row[4],
                    'question_count': row[5]
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
        """Get complete user profile from allowed_users data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    user_id,
                    username,
                    full_name,
                    grade,
                    language,
                    is_active,
                    current_topic,
                    last_activity,
                    added_at
                FROM allowed_users
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                'user_id': result[0],
                'username': result[1],
                'full_name': result[2],
                'grade': result[3],
                'language': result[4],
                'is_active': bool(result[5]),
                'current_topic': result[6],
                'last_activity': result[7],
                'added_at': result[8]
            }
    
    def sync_user_with_whitelist(self, user_id: int, username: str) -> bool:
        """Синхронизировать данные пользователя в allowed_users."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем данные в allowed_users
                cursor.execute('''
                    UPDATE allowed_users 
                    SET username = ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (username, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации пользователя {user_id}: {e}")
            return False

    def get_user_historical_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user historical statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем базовую информацию пользователя
            cursor.execute('''
                SELECT full_name, grade, language, last_activity
                FROM allowed_users WHERE user_id = ?
            ''', (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return {}
            
            # Получаем статистику тестов
            cursor.execute('''
                SELECT COUNT(*) as total_tests, AVG(percentage) as avg_score,
                       MAX(timestamp) as last_test_date
                FROM test_results WHERE user_id = ?
            ''', (user_id,))
            test_stats = cursor.fetchone()
            
            # Получаем количество ошибок
            cursor.execute('''
                SELECT COUNT(DISTINCT question_id) as unique_errors,
                       SUM(error_count) as total_errors
                FROM user_errors WHERE user_id = ?
            ''', (user_id,))
            error_stats = cursor.fetchone()
            
            return {
                'user_id': user_id,
                'full_name': user_info[0],
                'grade': user_info[1],
                'language': user_info[2],
                'last_activity': user_info[3],
                'total_tests': test_stats[0] or 0,
                'avg_score': round(test_stats[1] or 0, 1),
                'last_test_date': test_stats[2],
                'unique_errors': error_stats[0] or 0,
                'total_errors': error_stats[1] or 0
            }

    def get_all_users_with_history(self) -> List[Dict[str, Any]]:
        """Get all users with their test history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT au.user_id, au.username, au.full_name, au.grade, au.language,
                       au.last_activity, au.is_active,
                       COUNT(tr.id) as total_tests,
                       AVG(tr.percentage) as avg_score,
                       MAX(tr.timestamp) as last_test,
                       COUNT(DISTINCT ue.question_id) as unique_errors
                FROM allowed_users au
                LEFT JOIN test_results tr ON au.user_id = tr.user_id
                LEFT JOIN user_errors ue ON au.user_id = ue.user_id
                WHERE au.is_active = 1
                GROUP BY au.user_id, au.username, au.full_name, au.grade, au.language, au.last_activity, au.is_active
                ORDER BY au.last_activity DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'grade': row[3],
                    'language': row[4],
                    'last_activity': row[5],
                    'is_active': bool(row[6]),
                    'total_tests': row[7] or 0,
                    'avg_score': round(row[8] or 0, 1),
                    'last_test': row[9],
                    'unique_errors': row[10] or 0
                })
            
            return results

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
            
            # Основная информация об ученике из allowed_users
            cursor.execute('''
                SELECT user_id, username, full_name, grade, language, last_activity, added_at
                FROM allowed_users
                WHERE user_id = ?
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
                SELECT ue.topic,
                       COUNT(DISTINCT ue.question_id) as unique_errors,
                       SUM(ue.error_count) as total_errors,
                       MAX(ue.last_error_date) as last_error
                FROM user_errors ue
                WHERE ue.user_id = ?
                GROUP BY ue.topic
                ORDER BY total_errors DESC
            ''', (user_id,))
            error_stats = cursor.fetchall()
            
            # Последние ошибки (топ-10)
            cursor.execute('''
                SELECT q.question, ue.topic, ue.error_count, ue.last_error_date
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                WHERE ue.user_id = ?
                ORDER BY ue.last_error_date DESC
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
                    'full_name': user_info[2],
                    'grade': user_info[3],
                    'language': user_info[4],
                    'last_activity': user_info[5],
                    'added_to_whitelist': user_info[6]
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
        """Получить краткую сводку всех учеников для админ-панели."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем всех учеников из whitelist с их статистикой
            cursor.execute('''
                SELECT au.user_id, au.username, au.full_name, au.grade, au.has_access, au.added_at,
                       au.last_activity, au.is_active,
                       COUNT(tr.id) as total_tests,
                       AVG(tr.percentage) as avg_score,
                       COUNT(DISTINCT ue.question_id) as unique_errors,
                       MAX(tr.timestamp) as last_test
                FROM allowed_users au
                LEFT JOIN test_results tr ON au.user_id = tr.user_id
                LEFT JOIN user_errors ue ON au.user_id = ue.user_id
                GROUP BY au.id, au.user_id, au.username, au.full_name, au.grade, au.has_access, au.added_at, au.last_activity, au.is_active
                ORDER BY au.added_at DESC
            ''')
            
            results = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'grade': row[3],
                    'has_access': bool(row[4]),
                    'added_at': row[5],
                    'last_activity': row[6],
                    'is_active': bool(row[7]),  # Активность в тесте
                    'total_tests': row[8] or 0,
                    'avg_score': round(row[9] or 0, 1),
                    'unique_errors': row[10] or 0,
                    'last_test': row[11],
                    'status': 'Активен' if row[4] else 'Заблокирован'  # Статус доступа
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
                    LEFT JOIN test_results tr ON au.user_id = tr.user_id
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
                    LEFT JOIN test_results tr ON au.user_id = tr.user_id
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

    def update_allowed_user_by_id(self, user_id: int, full_name: str = None, grade: int = None, has_access: bool = None) -> bool:
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
                if has_access is not None:
                    updates.append("has_access = ?")
                    params.append(has_access)
                
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

    def get_student_contact_info(self, user_id: int) -> Dict[str, Any]:
        """Получить контактную информацию ученика."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, grade
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
                    'display_name': result[2] or 'Неизвестен',
                    'display_username': result[1] or 'не указан'
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
                    SELECT user_id, username, full_name, grade, is_active, added_at
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
                
                wl_user_id, wl_username, wl_full_name, wl_grade, wl_active, wl_added_at = whitelist_data
                
                # Определяем, что нужно обновить
                updates_made = []
                
                # Обновляем user_id и username в allowed_users если нужно
                if not wl_user_id or wl_user_id != user_id:
                    cursor.execute('''
                        UPDATE allowed_users 
                        SET user_id = ?, username = ?, last_activity = CURRENT_TIMESTAMP
                        WHERE username = ? AND (user_id IS NULL OR user_id != ?)
                    ''', (user_id, username, username, user_id))
                    updates_made.append("Синхронизирован user_id в whitelist")
                
                conn.commit()
                
                return {
                    'success': True,
                    'auto_configured': len(updates_made) > 0,
                    'updates_made': updates_made,
                    'user_data': {
                        'full_name': wl_full_name,
                        'grade': wl_grade,
                        'username': wl_username or username
                    },
                    'message': f"Автоматически настроено: {', '.join(updates_made)}" if updates_made else "Данные уже актуальны"
                }
                
        except Exception as e:
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
        """Создает казахские версии основных разделов (если они еще не созданы)."""
        try:
            try:
                from config.constants_kk import TOPIC_HIERARCHY_KK
            except ImportError:
                print("[ERROR] config.constants_kk не найден")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже казахские темы
                cursor.execute('SELECT COUNT(*) FROM main_topics WHERE language = "kk"')
                existing_kk_count = cursor.fetchone()[0]
                
                if existing_kk_count > 0:
                    print(f"[LOG] Казахские темы уже существуют ({existing_kk_count} разделов), пропускаем создание")
                    return True
                
                # Создаем казахские основные разделы
                created_count = 0
                for order_index, main_topic_kk in enumerate(TOPIC_HIERARCHY_KK.keys()):
                    cursor.execute('''
                        INSERT INTO main_topics (name, order_index, language, is_active)
                        VALUES (?, ?, "kk", 1)
                    ''', (main_topic_kk, order_index))
                    
                    kazakh_main_topic_id = cursor.lastrowid
                    created_count += 1
                    
                    # Создаем казахские подтемы для этого раздела
                    if main_topic_kk in TOPIC_HIERARCHY_KK:
                        kazakh_subtopics = TOPIC_HIERARCHY_KK[main_topic_kk]
                        for subtopic_order, kazakh_subtopic in enumerate(kazakh_subtopics):
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

    def get_topic_language(self, topic_name: str) -> str:
        """Получить язык темы через связь с main_topics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT mt.language
                    FROM subtopics st
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    WHERE st.name = ? AND st.is_active = 1 AND mt.is_active = 1
                    LIMIT 1
                ''', (topic_name,))
                
                result = cursor.fetchone()
                return result[0] if result else 'ru'  # По умолчанию русский
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения языка темы '{topic_name}': {e}")
            return 'ru'  # По умолчанию русский

    def get_main_topic_and_language_for_subtopic(self, subtopic_name: str) -> Tuple[Optional[str], str]:
        """Получить главную тему И язык для подтемы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT mt.name, mt.language
                    FROM subtopics st
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    WHERE st.name = ? AND st.is_active = 1 AND mt.is_active = 1
                    LIMIT 1
                ''', (subtopic_name,))
                
                result = cursor.fetchone()
                if result:
                    return result[0], result[1]  # main_topic, language
                else:
                    return None, 'ru'  # По умолчанию русский
                
        except Exception as e:
            print(f"[ERROR] Ошибка получения главной темы и языка для '{subtopic_name}': {e}")
            return None, 'ru'

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
                
                # Обновляем username в allowed_users
                cursor.execute('''
                    UPDATE allowed_users 
                    SET username = ?, last_activity = CURRENT_TIMESTAMP
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
        Получает отображаемую информацию о пользователе из allowed_users.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем данные из allowed_users
            cursor.execute('''
                SELECT username, full_name, grade, language
                FROM allowed_users WHERE user_id = ?
            ''', (user_id,))
            user_data = cursor.fetchone()
            
            # Формируем итоговую информацию
            result = {
                'user_id': user_id,
                'username': None,
                'full_name': None,
                'grade': None,
                'language': 'ru',
                'has_complete_info': False
            }
            
            # Заполняем данными из allowed_users
            if user_data:
                result.update({
                    'username': user_data[0],
                    'full_name': user_data[1],
                    'grade': user_data[2],
                    'language': user_data[3] or 'ru'
                })
                
                # Проверяем полноту информации
                result['has_complete_info'] = bool(
                    result['full_name'] and 
                    result['grade'] and 
                    result['grade'] > 0
                )
            
            return result

    def get_subtopics_by_main_topic(self, main_topic_name: str) -> list:
        """Получить список подтем для основной темы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.name 
                    FROM subtopics s
                    JOIN main_topics m ON s.main_topic_id = m.id
                    WHERE m.name = ?
                    ORDER BY s.name
                ''', (main_topic_name,))
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] Ошибка получения подтем: {e}")
            return []

    def toggle_topic_status(self, topic_id: int) -> bool:
        """Переключить статус активности темы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущий статус
                cursor.execute('SELECT is_active FROM subtopics WHERE id = ?', (topic_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                current_status = result[0]
                new_status = not current_status
                
                # Обновляем статус
                cursor.execute('UPDATE subtopics SET is_active = ? WHERE id = ?', (new_status, topic_id))
                conn.commit()
                
                print(f"[LOG] Статус темы {topic_id} изменен на {'активна' if new_status else 'неактивна'}")
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка переключения статуса темы: {e}")
            return False

    def update_topic_name(self, topic_id: int, new_name: str) -> bool:
        """Обновить название темы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, не существует ли уже тема с таким названием
                cursor.execute('SELECT id FROM subtopics WHERE name = ? AND id != ?', (new_name, topic_id))
                if cursor.fetchone():
                    print(f"[ERROR] Тема с названием '{new_name}' уже существует")
                    return False
                
                # Обновляем название
                cursor.execute('UPDATE subtopics SET name = ? WHERE id = ?', (new_name, topic_id))
                
                # Проверяем есть ли колонка topic в questions (для совместимости)
                cursor.execute("PRAGMA table_info(questions)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'topic' in columns:
                    # Старая архитектура: также обновляем в таблице вопросов
                    old_name_query = cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
                    cursor.execute('UPDATE questions SET topic = ? WHERE topic_id = ?', 
                                 (new_name, topic_id))
                    print(f"[LOG] Обновлена таблица questions (старая архитектура)")
                else:
                    # Новая архитектура: questions автоматически получат новое название через JOIN
                    print(f"[LOG] Таблица questions обновится автоматически через topic_id (новая архитектура)")
                
                conn.commit()
                print(f"[LOG] Название темы {topic_id} обновлено на '{new_name}'")
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка обновления названия темы: {e}")
            return False

    def delete_topic_completely(self, topic_id: int) -> bool:
        """Полностью удалить тему и все связанные данные."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем название темы для логирования
                cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
                result = cursor.fetchone()
                if not result:
                    print(f"[ERROR] Тема с ID {topic_id} не найдена")
                    return False
                
                topic_name = result[0]
                
                # Удаляем все связанные данные в правильном порядке
                
                # 1. Удаляем результаты тестов
                cursor.execute('DELETE FROM test_results WHERE topic = ?', (topic_name,))
                deleted_results = cursor.rowcount
                
                # 2. Удаляем вопросы
                cursor.execute('DELETE FROM questions WHERE topic = ?', (topic_name,))
                deleted_questions = cursor.rowcount
                
                # 3. Удаляем саму тему
                cursor.execute('DELETE FROM subtopics WHERE id = ?', (topic_id,))
                
                conn.commit()
                
                print(f"[LOG] Тема '{topic_name}' полностью удалена:")
                print(f"  - Удалено вопросов: {deleted_questions}")
                print(f"  - Удалено результатов тестов: {deleted_results}")
                
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка полного удаления темы: {e}")
            return False

    def add_main_topic_with_language(self, main_topic: str, language: str, subtopics: List[str] = None, created_by: int = None) -> bool:
        """Add a new main topic with language support."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем следующий order_index для основной темы
                cursor.execute('SELECT MAX(order_index) FROM main_topics WHERE language = ?', (language,))
                max_main_order = cursor.fetchone()[0] or 0
                
                # Добавляем основную тему с языком
                cursor.execute('''
                    INSERT INTO main_topics (name, order_index, language, created_by)
                    VALUES (?, ?, ?, ?)
                ''', (main_topic, max_main_order + 1, language, created_by))
                
                main_topic_id = cursor.lastrowid
                
                # Добавляем подтемы, если они есть
                if subtopics:
                    for i, subtopic in enumerate(subtopics):
                        cursor.execute('''
                            INSERT INTO topics (name, main_topic_id, order_index, language, created_by)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (subtopic, main_topic_id, i + 1, language, created_by))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Database error in add_main_topic_with_language: {e}")
            return False
        except Exception as e:
            print(f"Error in add_main_topic_with_language: {e}")
            return False

    def toggle_main_topic_status(self, main_topic_name: str) -> bool:
        """Toggle the is_active status of a main topic by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущий статус
                cursor.execute('SELECT is_active FROM main_topics WHERE name = ?', (main_topic_name,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                current_status = result[0]
                new_status = not current_status
                
                # Обновляем статус
                cursor.execute('''
                    UPDATE main_topics 
                    SET is_active = ? 
                    WHERE name = ?
                ''', (new_status, main_topic_name))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            print(f"Database error in toggle_main_topic_status: {e}")
            return False
        except Exception as e:
            print(f"Error in toggle_main_topic_status: {e}")
            return False

    def update_topic_section(self, topic_id: int, new_main_topic_name: str) -> bool:
        """Обновить раздел темы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем ID нового основного раздела
                cursor.execute('SELECT id FROM main_topics WHERE name = ?', (new_main_topic_name,))
                result = cursor.fetchone()
                
                if not result:
                    print(f"[ERROR] Основной раздел '{new_main_topic_name}' не найден")
                    return False
                
                new_main_topic_id = result[0]
                
                # Получаем старое название темы для обновления вопросов
                cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
                topic_result = cursor.fetchone()
                
                if not topic_result:
                    print(f"[ERROR] Тема с ID {topic_id} не найдена")
                    return False
                
                topic_name = topic_result[0]
                
                # Обновляем main_topic_id в subtopics
                cursor.execute('UPDATE subtopics SET main_topic_id = ? WHERE id = ?', (new_main_topic_id, topic_id))
                
                conn.commit()
                print(f"[LOG] Раздел темы '{topic_name}' (ID: {topic_id}) изменен на '{new_main_topic_name}'")
                return True
                
        except Exception as e:
            print(f"[ERROR] Ошибка обновления раздела темы: {e}")
            return False

    def clear_user_test_activity(self, user_id: int) -> None:
        """Clear user's current test topic without changing is_active status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE allowed_users 
                SET current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

    def is_user_system_active(self, user_id: int) -> bool:
        """Check if user is active in the system (not deactivated by admin)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])

    def has_user_access(self, user_id: int) -> bool:
        """Check if user has access to the system (controlled by admin)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT has_access FROM allowed_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])

    def set_user_access(self, user_id: int, has_access: bool) -> bool:
        """Set user access status (enable/disable user)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE allowed_users 
                    SET has_access = ?, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (has_access, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def check_user_access(self, user_id: int, username: str = None) -> bool:
        """
        Comprehensive user access check.
        Returns True if user has access, False otherwise.
        """
        # First check if user is admin (admins always have access)
        if self.is_admin(user_id):
            return True
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if user exists in allowed_users and has access
            cursor.execute('''
                SELECT has_access, is_active 
                FROM allowed_users 
                WHERE user_id = ? AND has_access = 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return True
            
            # If username provided, also check by username
            if username:
                cursor.execute('''
                    SELECT has_access 
                    FROM allowed_users 
                    WHERE username = ? AND has_access = 1
                ''', (username,))
                
                result = cursor.fetchone()
                if result:
                    return True
            
            return False

    def get_all_ai_questions(self) -> List[Dict[str, Any]]:
        """
        Получает все AI-вопросы из базы данных.
        
        Returns:
            List[Dict[str, Any]]: Список всех AI-вопросов
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, question, answer, explanation, topic, source
                FROM questions 
                WHERE source = 'ai'
                ORDER BY id DESC
            ''')
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                question_dict = dict(zip(columns, row))
                results.append(question_dict)
            
            return results

    def delete_question_by_id(self, question_id: int) -> bool:
        """
        Удаляет вопрос по ID.
        
        Args:
            question_id (int): ID вопроса для удаления
            
        Returns:
            bool: True если вопрос был удален, False если не найден
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли вопрос
            cursor.execute('SELECT id FROM questions WHERE id = ?', (question_id,))
            if not cursor.fetchone():
                return False
            
            # Удаляем вопрос
            cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
            conn.commit()
            
            return cursor.rowcount > 0

    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add a user's error to the database using question_id (new method for new structure)."""
        try:
            logging.info(f"[DEBUG][add_user_error_by_question_id] user_id={user_id}, question_id={question_id}, topic={topic}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if error already exists for this user and question
                cursor.execute('''
                    SELECT id, error_count FROM user_errors 
                    WHERE user_id = ? AND question_id = ?
                ''', (user_id, question_id))
                result = cursor.fetchone()
                
                if result:
                    error_id, current_count = result
                    cursor.execute('''
                        UPDATE user_errors 
                        SET error_count = error_count + 1,
                            last_error_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (error_id,))
                    logging.info(f"[DEBUG][add_user_error_by_question_id] Updated error_count for id={error_id}, question_id={question_id}")
                else:
                    cursor.execute('''
                        INSERT INTO user_errors 
                        (user_id, question_id, topic, user_answer, correct_answer)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, question_id, topic, user_answer_text, correct_answer_text))
                    logging.info(f"[DEBUG][add_user_error_by_question_id] Inserted new error for user_id={user_id}, question_id={question_id}")
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"[DEBUG][add_user_error_by_question_id] Exception: {e}")

    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count for a question by question_id and remove if reaches 0."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_id = ?', (user_id, question_id))
                before = cursor.fetchone()
                logging.info(f"[DEBUG][decrement_error_count_by_question_id] before: {before}")
                
                cursor.execute('''
                    UPDATE user_errors 
                    SET error_count = error_count - 1
                    WHERE user_id = ? AND question_id = ?
                ''', (user_id, question_id))
                
                cursor.execute('SELECT error_count FROM user_errors WHERE user_id = ? AND question_id = ?', (user_id, question_id))
                after = cursor.fetchone()
                logging.info(f"[DEBUG][decrement_error_count_by_question_id] after: {after}")
                
                # Remove if count reaches 0
                cursor.execute('''
                    DELETE FROM user_errors 
                    WHERE user_id = ? AND question_id = ? AND error_count <= 0
                ''', (user_id, question_id))
                logging.info(f"[DEBUG][decrement_error_count_by_question_id] deleted if error_count <= 0 for user_id={user_id}, question_id={question_id}")
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"[DEBUG][decrement_error_count_by_question_id] Exception: {e}")

    # === NEW TOPIC_ID METHODS ===
    # These methods use topic_id instead of topic name for better performance and consistency
    
    def get_tasks_for_topic_id(self, topic_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for a specific topic using topic_id (new method)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                       q.question_type, q.source, q.image_path, s.name as topic_name
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE q.topic_id = ? AND s.is_active = 1
                ORDER BY RANDOM()
                LIMIT ?
            ''', (topic_id, limit))
            columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 
                      'question_type', 'source', 'image_path', 'topic_name']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_error_tasks_for_user_by_topic_id(self, user_id: int, topic_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get tasks that user previously answered incorrectly using topic_id (new method)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                       ue.error_count, q.image_path, s.name as topic_name
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                JOIN user_errors ue ON q.id = ue.question_id
                WHERE ue.user_id = ? AND q.topic_id = ? AND s.is_active = 1
                ORDER BY ue.error_count DESC, ue.last_error_date DESC
                LIMIT ?
            ''', (user_id, topic_id, limit))
            columns = ['id', 'question', 'answer', 'explanation', 'incorrect_options', 
                      'error_count', 'image_path', 'topic_name']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def add_question_with_topic_id(self, question: dict, topic_id: int) -> bool:
        """Add a new question using topic_id (new method)."""
        required_fields = ['question', 'answer', 'explanation']
        for field in required_fields:
            if not question.get(field):
                logging.error(f"Cannot add question: {field} is None or empty. Question data: {question}")
                return False
        
        # Get topic name for backward compatibility
        topic_name = self._get_topic_name_by_id(topic_id)
        if not topic_name:
            logging.error(f"Cannot add question: topic_id {topic_id} not found")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO questions (topic_id, topic, question, answer, explanation, 
                                         incorrect_options, question_type, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    topic_id,
                    topic_name,  # Keep for backward compatibility
                    question['question'],
                    question['answer'],
                    question['explanation'],
                    question.get('incorrect_options', ''),
                    question.get('question_type', 'standard'),
                    question.get('source', 'db')
                ))
                conn.commit()
                logging.info(f"Added question with topic_id {topic_id}")
                return True
        except Exception as e:
            logging.error(f"Error adding question with topic_id: {e}")
            return False
    
    def get_topic_question_counts_by_id(self) -> Dict[int, Dict[str, Any]]:
        """Get question counts for each topic using topic_id (new method)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.name, COUNT(q.id) as question_count,
                       mt.name as main_topic_name, s.is_active
                FROM subtopics s
                LEFT JOIN questions q ON s.id = q.topic_id
                LEFT JOIN main_topics mt ON s.main_topic_id = mt.id
                WHERE s.is_active = 1
                GROUP BY s.id, s.name, mt.name, s.is_active
                ORDER BY mt.name, s.name
            ''')
            
            result = {}
            for row in cursor.fetchall():
                topic_id, topic_name, count, main_topic, is_active = row
                result[topic_id] = {
                    'name': topic_name,
                    'question_count': count,
                    'main_topic': main_topic,
                    'is_active': bool(is_active)
                }
            return result
    
    def _get_topic_name_by_id(self, topic_id: int) -> Optional[str]:
        """Helper method to get topic name by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def _get_topic_id_by_name(self, topic_name: str) -> Optional[int]:
        """Helper method to get topic ID by name."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM subtopics WHERE name = ?', (topic_name,))
            result = cursor.fetchone()
            return result[0] if result else None

    # === END NEW TOPIC_ID METHODS ===

    def _get_connection(self):
        """Get database connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def rename_topic_by_id(self, topic_id: int, new_name: str) -> bool:
        """
        Переименовывает тему по ID (эффективно благодаря topic_id архитектуре).
        
        Преимущества новой архитектуры:
        - Обновляется ТОЛЬКО одна строка в subtopics
        - Все связанные вопросы автоматически используют новое название через JOIN
        - Никаких массовых UPDATE в таблице questions
        
        Args:
            topic_id: ID темы для переименования
            new_name: Новое название темы
            
        Returns:
            bool: True если переименование успешно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование темы
                cursor.execute('SELECT name FROM subtopics WHERE id = ?', (topic_id,))
                result = cursor.fetchone()
                if not result:
                    logging.warning(f"Тема с ID {topic_id} не найдена")
                    return False
                
                old_name = result[0]
                
                # Проверяем не занято ли новое название
                cursor.execute('SELECT id FROM subtopics WHERE name = ? AND id != ?', 
                              (new_name, topic_id))
                if cursor.fetchone():
                    logging.warning(f"Название '{new_name}' уже используется другой темой")
                    return False
                
                # Получаем количество связанных вопросов ДО переименования
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic_id,))
                question_count = cursor.fetchone()[0]
                
                # ЭФФЕКТИВНОЕ переименование: обновляем ТОЛЬКО subtopics
                cursor.execute('UPDATE subtopics SET name = ? WHERE id = ?', 
                              (new_name, topic_id))
                
                # Проверяем что переименование прошло успешно
                if cursor.rowcount == 1:
                    logging.info(f"✅ Тема переименована: '{old_name}' -> '{new_name}' (ID: {topic_id})")
                    logging.info(f"📊 Связанных вопросов: {question_count} (остались автоматически связаны)")
                    logging.info(f"🚀 Обновлена ТОЛЬКО 1 строка в subtopics, таблица questions НЕ ТРОНУТА!")
                    return True
                else:
                    logging.error(f"Ошибка при переименовании темы ID {topic_id}")
                    return False
                    
        except Exception as e:
            logging.error(f"Ошибка при переименовании темы: {e}")
            return False

    def rename_topic_by_name(self, old_name: str, new_name: str) -> bool:
        """
        Переименовывает тему по названию (wrapper для rename_topic_by_id).
        
        Args:
            old_name: Текущее название темы
            new_name: Новое название темы
            
        Returns:
            bool: True если переименование успешно
        """
        topic_id = self._get_topic_id_by_name(old_name)
        if topic_id is None:
            logging.warning(f"Тема '{old_name}' не найдена")
            return False
        
        return self.rename_topic_by_id(topic_id, new_name)

    def get_topic_rename_impact(self, topic_id: int) -> Dict[str, Any]:
        """
        Показывает влияние переименования темы (для предварительной оценки).
        
        Args:
            topic_id: ID темы
            
        Returns:
            Dict с информацией о влиянии переименования
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о теме
                cursor.execute('SELECT name, main_topic_id, is_active FROM subtopics WHERE id = ?', 
                              (topic_id,))
                topic_info = cursor.fetchone()
                if not topic_info:
                    return {"error": f"Тема с ID {topic_id} не найдена"}
                
                name, main_topic_id, is_active = topic_info
                
                # Считаем связанные объекты (только по topic_id, так как колонка topic удалена)
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic_id,))
                questions_with_topic_id = cursor.fetchone()[0]
                
                # Колонка topic больше не существует, поэтому questions_with_topic_name = 0
                questions_with_topic_name = 0
                
                return {
                    "topic_id": topic_id,
                    "current_name": name,
                    "main_topic_id": main_topic_id,
                    "is_active": bool(is_active),
                    "questions_linked_by_id": questions_with_topic_id,
                    "questions_linked_by_name": questions_with_topic_name,
                    "new_architecture_impact": {
                        "rows_to_update": 1,  # Только subtopics
                        "affected_questions": questions_with_topic_id,
                        "questions_stay_linked": True
                    },
                    "old_architecture_impact": {
                        "rows_to_update": 1 + questions_with_topic_name,  # subtopics + все questions (теперь 0)
                        "affected_questions": questions_with_topic_name,
                        "risk_level": "low"  # Теперь всегда низкий риск
                    }
                }
                
        except Exception as e:
            logging.error(f"Ошибка при анализе влияния переименования: {e}")
            return {"error": str(e)}