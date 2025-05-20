import sqlite3
from datetime import datetime
import json
import logging

# Настройка логирования (если еще не настроено в этом файле)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self, db_name="math_bot.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            grade INTEGER
        )''')
        
        # Таблица активных пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_users (
            user_id INTEGER PRIMARY KEY,
            current_topic TEXT,
            current_question INTEGER,
            start_time TIMESTAMP,
            last_activity TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''')
        
        # Таблица истории тестов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            date TIMESTAMP,
            result INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''')
        
        # Таблица ошибок (summary per topic)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            error_count INTEGER,
            UNIQUE(user_id, topic),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''')
        
        # Новая таблица для детальных ошибок по вопросам
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_question_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            question_text TEXT,
            user_answer_text TEXT,
            correct_answer_text TEXT,
            explanation_text TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''')
        
        # Обновленная таблица задач с поддержкой изображений и количественных характеристик
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            explanation TEXT,
            topic TEXT,
            level INTEGER,
            incorrect_options TEXT DEFAULT NULL,
            question_type TEXT DEFAULT 'standard',  -- 'standard' или 'quantitative'
            image_path TEXT DEFAULT NULL,  -- путь к изображению вопроса
            characteristic_a TEXT DEFAULT NULL,  -- для количественных характеристик
            characteristic_b TEXT DEFAULT NULL,  -- для количественных характеристик
            source_file TEXT DEFAULT NULL  -- исходный файл, откуда взят вопрос
        )''')
        
        self.conn.commit()

    def add_user(self, user_id, name, grade):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, name, grade) VALUES (?, ?, ?)',
                      (user_id, name, grade))
        self.conn.commit()

    def add_test_result(self, user_id, topic, result):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO test_history (user_id, topic, date, result) VALUES (?, ?, ?, ?)',
                      (user_id, topic, datetime.now(), result))
        self.conn.commit()

    def add_error(self, user_id, topic):
        """
        Increments the error count for a given user and topic in the 'errors' summary table.
        This method is called by add_user_error.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO errors (user_id, topic, error_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, topic) DO UPDATE SET error_count = error_count + 1
        ''', (user_id, topic))
        self.conn.commit()

    def add_user_error(self, user_id: int, topic: str, question_text: str, user_answer_text: str, correct_answer_text: str, explanation_text: str = None):
        """
        Logs a detailed user error into the user_question_errors table
        and updates the summary error count in the 'errors' table.
        """
        cursor = self.conn.cursor()
        try:
            # 1. Log the detailed error
            cursor.execute('''
                INSERT INTO user_question_errors (user_id, topic, question_text, user_answer_text, correct_answer_text, explanation_text, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, topic, question_text, user_answer_text, correct_answer_text, explanation_text, datetime.now()))
            
            # 2. Update the topic-level error count in the 'errors' table
            cursor.execute('''
                INSERT INTO errors (user_id, topic, error_count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, topic) DO UPDATE SET error_count = error_count + 1
            ''', (user_id, topic))
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in add_user_error: {e}")
            self.conn.rollback()

    def get_user_progress(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) as total_tests, AVG(result) as avg_result
        FROM test_history
        WHERE user_id = ?
        ''', (user_id,))
        return cursor.fetchone()

    def get_recent_topics(self, user_id, limit=3):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT topic, result, date
        FROM test_history
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()

    def get_error_topics(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT topic, error_count
        FROM errors
        WHERE user_id = ?
        ORDER BY error_count DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_tasks_for_topic(self, topic, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT question, answer, explanation, incorrect_options, question_type, image_path, characteristic_a, characteristic_b
        FROM tasks
        WHERE topic = ?
        ORDER BY RANDOM()
        LIMIT ?
        ''', (topic, limit))
        
        tasks_with_options = []
        for row in cursor.fetchall():
            question, answer, explanation, incorrect_options_json, question_type, image_path, characteristic_a, characteristic_b = row
            incorrect_options_list = None
            if incorrect_options_json:
                try:
                    incorrect_options_list = json.loads(incorrect_options_json)
                except json.JSONDecodeError:
                    incorrect_options_list = []
            
            task_data = {
                'question': question,
                'answer': answer,
                'explanation': explanation,
                'incorrect_options': incorrect_options_list,
                'question_type': question_type,
                'image_path': image_path,
                'characteristic_a': characteristic_a,
                'characteristic_b': characteristic_b
            }
            tasks_with_options.append(task_data)
        return tasks_with_options

    def add_task(self, question, answer, explanation, topic, level=1):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO tasks (question, answer, explanation, topic, level) VALUES (?, ?, ?, ?, ?)',
            (question, answer, explanation, topic, level)
        )
        self.conn.commit()

    def add_task_from_ai(self, topic: str, question: str, correct_answer: str, incorrect_options_list: list, explanation: str, level: int = 1):
        """
        Добавляет задачу, сгенерированную ИИ, в базу данных.
        Неправильные варианты сохраняются как JSON-строка.
        """
        cursor = self.conn.cursor()
        incorrect_options_json = json.dumps(incorrect_options_list) if incorrect_options_list else None
        
        try:
            cursor.execute(
                '''INSERT INTO tasks (question, answer, explanation, topic, level, incorrect_options) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (question, correct_answer, explanation, topic, level, incorrect_options_json)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in add_task_from_ai: {e}")

    def get_error_tasks_for_user(self, user_id, topic, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.question, t.answer, t.explanation, t.incorrect_options
            FROM tasks t
            JOIN (SELECT DISTINCT question_text FROM user_question_errors WHERE user_id = ? AND topic = ?) uqe
            ON t.question = uqe.question_text
            WHERE t.topic = ?
            LIMIT ?
        ''', (user_id, topic, topic, limit))
        return cursor.fetchall()

    def delete_all_user_data(self, user_id: int) -> bool:
        """
        Удаляет все данные, связанные с указанным user_id, из всех таблиц.
        """
        # Обновленный список таблиц, содержащих user_id.
        # Порядок важен, если есть внешние ключи и их строгое соблюдение включено.
        # Сначала удаляем из таблиц, которые ссылаются на 'users', затем из самой 'users'.
        tables_to_clear_for_user = [
            "test_history", 
            "errors", 
            "user_question_errors", 
            "users"  # Таблицу users удаляем последней, если на нее есть ссылки
        ]

        try:
            for table_name in tables_to_clear_for_user:
                # Убедимся, что таблица существует, прежде чем пытаться из нее удалить
                self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                if self.cursor.fetchone():
                    # Для таблицы users, user_id является первичным ключом.
                    # Для других таблиц, user_id является внешним ключом или просто полем.
                    self.cursor.execute(f"DELETE FROM {table_name} WHERE user_id = ?", (user_id,))
                    logging.info(f"Данные для пользователя {user_id} удалены из таблицы {table_name}.")
                else:
                    # Эта ситуация не должна возникать, если create_tables отработал корректно
                    logging.warning(f"Таблица {table_name} не найдена при попытке удаления данных пользователя {user_id}.")
            self.conn.commit()
            logging.info(f"Все данные для пользователя {user_id} успешно удалены из базы данных.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка SQLite при удалении данных пользователя {user_id}: {e}")
            self.conn.rollback() # Откатываем изменения в случае ошибки
            return False
        except Exception as e:
            logging.error(f"Неожиданная ошибка при удалении данных пользователя {user_id}: {e}")
            self.conn.rollback() # Откатываем изменения в случае ошибки
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Соединение с базой данных закрыто.")

    def set_user_active(self, user_id: int, topic: str, question_num: int = 0):
        """Устанавливает пользователя как активного и обновляет его состояние"""
        cursor = self.conn.cursor()
        now = datetime.now()
        cursor.execute('''
        INSERT INTO active_users (user_id, current_topic, current_question, start_time, last_activity)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            current_topic = ?,
            current_question = ?,
            last_activity = ?
        ''', (user_id, topic, question_num, now, now, topic, question_num, now))
        self.conn.commit()

    def update_user_activity(self, user_id: int, question_num: int = None):
        """Обновляет время последней активности пользователя и текущий вопрос"""
        cursor = self.conn.cursor()
        now = datetime.now()
        if question_num is not None:
            cursor.execute('''
            UPDATE active_users 
            SET last_activity = ?, current_question = ?
            WHERE user_id = ?
            ''', (now, question_num, user_id))
        else:
            cursor.execute('''
            UPDATE active_users 
            SET last_activity = ?
            WHERE user_id = ?
            ''', (now, user_id))
        self.conn.commit()

    def set_user_inactive(self, user_id: int):
        """Удаляет пользователя из списка активных"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def get_active_users(self):
        """Возвращает список активных пользователей"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT user_id, current_topic, current_question, start_time, last_activity
        FROM active_users
        ORDER BY last_activity DESC
        ''')
        return cursor.fetchall()

    def is_user_active(self, user_id: int) -> bool:
        """Проверяет, активен ли пользователь"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM active_users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None

    def get_user_current_state(self, user_id: int):
        """Возвращает текущее состояние пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT current_topic, current_question, start_time, last_activity
        FROM active_users
        WHERE user_id = ?
        ''', (user_id,))
        return cursor.fetchone()

    def get_explanation_by_question_text(self, question_text):
        cursor = self.conn.cursor()
        cursor.execute('SELECT explanation FROM tasks WHERE question = ?', (question_text,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_explanation_fuzzy_by_question_text(self, question_text):
        cursor = self.conn.cursor()
        # Сначала пробуем точное совпадение
        cursor.execute('SELECT explanation FROM tasks WHERE question = ?', (question_text,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        # Если не найдено, ищем по началу вопроса (первые 50 символов)
        prefix = question_text[:50]
        cursor.execute('SELECT explanation FROM tasks WHERE question LIKE ? AND explanation IS NOT NULL AND explanation != "" LIMIT 1', (prefix + '%',))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_task_with_image(self, question, answer, explanation, topic, level, image_path, question_type='standard', characteristic_a=None, characteristic_b=None, source_file=None):
        """Добавляет задачу с изображением в базу данных"""
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO tasks 
               (question, answer, explanation, topic, level, image_path, question_type, characteristic_a, characteristic_b, source_file) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (question, answer, explanation, topic, level, image_path, question_type, characteristic_a, characteristic_b, source_file)
        )
        self.conn.commit()