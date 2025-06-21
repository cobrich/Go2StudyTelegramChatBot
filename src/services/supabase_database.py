import asyncio
import asyncpg
import logging
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

# Добавляем корневую директорию проекта в sys.path для импортов
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Глобальный синглтон для SupabaseDatabase
_supabase_database_instance = None

def get_supabase_database_instance():
    """Получить глобальный экземпляр SupabaseDatabase (синглтон)."""
    global _supabase_database_instance
    if _supabase_database_instance is None:
        _supabase_database_instance = SupabaseDatabase()
    return _supabase_database_instance

class SupabaseDatabase:
    def __init__(self, connection_string: str = None):
        """Инициализация подключения к Supabase PostgreSQL"""
        if connection_string is None:
            # Получаем строку подключения из переменных окружения
            connection_string = os.getenv('SUPABASE_DATABASE_URL')
            if not connection_string:
                raise ValueError("SUPABASE_DATABASE_URL не установлена в переменных окружения")
        
        self.connection_string = connection_string
        self.pool = None
        print(f"[LOG] Используется Supabase PostgreSQL: {connection_string.split('@')[1] if '@' in connection_string else 'скрыто'}")
        
        # Инициализируем базу данных синхронно
        self._init_database_sync()

    def _init_database_sync(self):
        """Синхронная инициализация базы данных"""
        try:
            # Создаем новый event loop для инициализации
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._init_db())
                print("[LOG] База данных успешно инициализирована")
            finally:
                loop.close()
        except Exception as e:
            print(f"[ERROR] Ошибка инициализации БД: {e}")
            raise

    async def _init_db(self):
        """Initialize database with all required tables."""
        conn = await asyncpg.connect(self.connection_string)
        try:
            print("[LOG] Создание таблиц...")
            
            # Create admins table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create allowed_users table
            await conn.execute('''
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
            ''')
            
            # Create unique index for user_id
            await conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_allowed_users_user_id 
                ON allowed_users(user_id) WHERE user_id IS NOT NULL
            ''')
            
            # Create main_topics table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    language TEXT DEFAULT 'ru',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0
                )
            ''')
            
            # Create subtopics table
            await conn.execute('''
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
            ''')
            
            # Create questions table with correct structure (topic_id instead of topic)
            await conn.execute('''
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
            ''')
            
            # Create test_results table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    topic TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create user_errors table with correct structure
            await conn.execute('''
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
            ''')
            
            print("[LOG] Таблицы созданы успешно")
            
            # Initialize base topic structure if empty
            count = await conn.fetchval('SELECT COUNT(*) FROM main_topics')
            if count == 0:
                print("[LOG] Инициализация базовых тем...")
                await self._initialize_main_topics_async(conn)
                print("[LOG] Базовые темы созданы")
            else:
                print(f"[LOG] Найдено {count} основных тем, инициализация не требуется")
                
        except Exception as e:
            print(f"[ERROR] Ошибка при создании таблиц: {e}")
            raise
        finally:
            await conn.close()

    def _sync_call(self, coro):
        """Синхронный вызов асинхронной функции"""
        try:
            # Создаем новый event loop для каждого вызова
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            print(f"[ERROR] Ошибка в _sync_call: {e}")
            raise

    # ============== USER ACTIVITY METHODS ==============
    
    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active with current topic."""
        async def _set_user_active():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    UPDATE allowed_users 
                    SET is_active = TRUE, current_topic = $1, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = $2
                ''', topic, user_id)
            finally:
                await conn.close()
        
        self._sync_call(_set_user_active())

    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive and clear current topic."""
        async def _set_user_inactive():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    UPDATE allowed_users 
                    SET is_active = FALSE, current_topic = NULL, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = $1
                ''', user_id)
            finally:
                await conn.close()
        
        self._sync_call(_set_user_inactive())

    def is_user_active(self, user_id: int) -> bool:
        """Check if user is currently active (taking a test)."""
        async def _is_user_active():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('SELECT is_active FROM allowed_users WHERE user_id = $1', user_id)
                return bool(result)
            finally:
                await conn.close()
        
        return self._sync_call(_is_user_active())

    def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp."""
        async def _update_user_activity():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    UPDATE allowed_users 
                    SET last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = $1
                ''', user_id)
            finally:
                await conn.close()
        
        self._sync_call(_update_user_activity())

    # ============== TEST RESULTS METHODS ==============
    
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result for user."""
        async def _add_test_result():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    INSERT INTO test_results (user_id, topic, percentage, date, timestamp)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', user_id, topic, percentage)
            finally:
                await conn.close()
        
        self._sync_call(_add_test_result())

    def get_user_test_results(self, user_id: int) -> List[Dict[str, Any]]:
        """Get test results for user."""
        async def _get_user_test_results():
            conn = await asyncpg.connect(self.connection_string)
            try:
                rows = await conn.fetch('''
                    SELECT topic, percentage, date, timestamp
                    FROM test_results 
                    WHERE user_id = $1 
                    ORDER BY timestamp DESC
                ''', user_id)
                
                results = []
                for row in rows:
                    results.append({
                        'topic': row['topic'],
                        'percentage': row['percentage'],
                        'date': row['date'],
                        'timestamp': row['timestamp']
                    })
                return results
            finally:
                await conn.close()
        
        return self._sync_call(_get_user_test_results())

    def get_user_progress(self, user_id: int) -> Tuple[int, float]:
        """Get user's overall progress (test count, average score)."""
        async def _get_user_progress():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchrow('''
                    SELECT COUNT(*) as test_count, COALESCE(AVG(percentage), 0) as avg_score
                    FROM test_results 
                    WHERE user_id = $1
                ''', user_id)
                
                return (result['test_count'], result['avg_score'])
            finally:
                await conn.close()
        
        return self._sync_call(_get_user_progress())

    # ============== ADMIN METHODS ==============
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin."""
        async def _is_super_admin():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('''
                    SELECT is_super_admin FROM admins WHERE user_id = $1
                ''', user_id)
                return bool(result)
            finally:
                await conn.close()
        
        return self._sync_call(_is_super_admin())

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        async def _is_admin():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('SELECT 1 FROM admins WHERE user_id = $1', user_id)
                return result is not None
            finally:
                await conn.close()
        
        return self._sync_call(_is_admin())

    def add_admin(self, user_id: int, username: str, full_name: str, is_super: bool = False, added_by: int = None) -> bool:
        """Add new admin."""
        async def _add_admin():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        full_name = EXCLUDED.full_name,
                        is_super_admin = EXCLUDED.is_super_admin
                ''', user_id, username, full_name, is_super, added_by)
                return True
            except Exception as e:
                logging.error(f"Error adding admin: {e}")
                return False
            finally:
                await conn.close()
        
        return self._sync_call(_add_admin())

    # ============== USER ACCESS METHODS ==============
    
    def is_user_allowed(self, username: str) -> bool:
        """Check if user is in allowed list by username."""
        async def _is_user_allowed():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('''
                    SELECT has_access FROM allowed_users 
                    WHERE username = $1 AND has_access = TRUE
                ''', username)
                return result is not None
            finally:
                await conn.close()
        
        return self._sync_call(_is_user_allowed())

    def is_user_allowed_by_id(self, user_id: int) -> bool:
        """Check if user is allowed by user_id."""
        async def _is_user_allowed_by_id():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('''
                    SELECT has_access FROM allowed_users 
                    WHERE user_id = $1 AND has_access = TRUE
                ''', user_id)
                return result is not None
            finally:
                await conn.close()
        
        return self._sync_call(_is_user_allowed_by_id())

    # ============== TOPICS METHODS ==============
    
    def get_all_topics(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all topics/subtopics."""
        async def _get_all_topics():
            conn = await asyncpg.connect(self.connection_string)
            try:
                query = '''
                    SELECT st.id, st.name, st.description, st.is_active,
                           mt.name as main_topic_name, mt.language
                    FROM subtopics st
                    LEFT JOIN main_topics mt ON st.main_topic_id = mt.id
                '''
                if active_only:
                    query += ' WHERE st.is_active = TRUE'
                query += ' ORDER BY mt.order_index, st.order_index, st.name'
                
                rows = await conn.fetch(query)
                
                topics = []
                for row in rows:
                    topics.append({
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'is_active': row['is_active'],
                        'main_topic': row['main_topic_name'],
                        'language': row['language']
                    })
                return topics
            finally:
                await conn.close()
        
        return self._sync_call(_get_all_topics())

    def get_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Get topics by language."""
        async def _get_topics_by_language():
            conn = await asyncpg.connect(self.connection_string)
            try:
                query = '''
                    SELECT st.id, st.name, st.description, st.is_active,
                           mt.name as main_topic_name, mt.language
                    FROM subtopics st
                    LEFT JOIN main_topics mt ON st.main_topic_id = mt.id
                    WHERE mt.language = $1
                '''
                if active_only:
                    query += ' AND st.is_active = TRUE'
                query += ' ORDER BY mt.order_index, st.order_index, st.name'
                
                rows = await conn.fetch(query, language)
                
                topics = []
                for row in rows:
                    topics.append({
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'is_active': row['is_active'],
                        'main_topic': row['main_topic_name'],
                        'language': row['language']
                    })
                return topics
            finally:
                await conn.close()
        
        return self._sync_call(_get_topics_by_language())

    # ============== QUESTIONS METHODS ==============
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for specific topic."""
        async def _get_tasks_for_topic():
            conn = await asyncpg.connect(self.connection_string)
            try:
                rows = await conn.fetch('''
                    SELECT q.id, q.question, q.answer, q.explanation, 
                           q.incorrect_options, q.source, q.image_path,
                           st.name as topic
                    FROM questions q
                    LEFT JOIN subtopics st ON q.topic_id = st.id
                    WHERE st.name = $1
                    ORDER BY RANDOM()
                    LIMIT $2
                ''', topic, limit)
                
                tasks = []
                for row in rows:
                    # Parse incorrect_options if it's JSON string
                    incorrect_options = row['incorrect_options']
                    if isinstance(incorrect_options, str):
                        try:
                            incorrect_options = json.loads(incorrect_options)
                        except:
                            incorrect_options = incorrect_options.split('\n') if incorrect_options else []
                    
                    tasks.append({
                        'id': row['id'],
                        'question': row['question'],
                        'answer': row['answer'],
                        'explanation': row['explanation'],
                        'incorrect_options': incorrect_options,
                        'source': row['source'],
                        'image_path': row['image_path'],
                        'topic': row['topic']
                    })
                return tasks
            finally:
                await conn.close()
        
        return self._sync_call(_get_tasks_for_topic())

    def add_question(self, question: dict) -> None:
        """Add new question to database."""
        async def _add_question():
            conn = await asyncpg.connect(self.connection_string)
            try:
                # Get topic_id by topic name
                topic_id = await conn.fetchval('''
                    SELECT id FROM subtopics WHERE name = $1
                ''', question.get('topic'))
                
                if not topic_id:
                    # Create topic if it doesn't exist
                    # First, try to find or create main topic
                    main_topic_id = await conn.fetchval('''
                        SELECT id FROM main_topics WHERE name = 'Общие' AND language = 'ru'
                    ''')
                    
                    if not main_topic_id:
                        main_topic_id = await conn.fetchval('''
                            INSERT INTO main_topics (name, language) 
                            VALUES ('Общие', 'ru') 
                            RETURNING id
                        ''')
                    
                    # Create subtopic
                    topic_id = await conn.fetchval('''
                        INSERT INTO subtopics (name, main_topic_id) 
                        VALUES ($1, $2) 
                        RETURNING id
                    ''', question.get('topic'), main_topic_id)
                
                # Prepare incorrect_options
                incorrect_options = question.get('incorrect_options', [])
                if isinstance(incorrect_options, list):
                    incorrect_options = json.dumps(incorrect_options)
                
                await conn.execute('''
                    INSERT INTO questions (topic_id, question, answer, explanation, 
                                         incorrect_options, source, question_type)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', topic_id, question.get('question'), question.get('answer'),
                     question.get('explanation'), incorrect_options,
                     question.get('source', 'db'), question.get('question_type', 'standard'))
                
            finally:
                await conn.close()
        
        self._sync_call(_add_question())

    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions from database."""
        async def _get_all_questions():
            conn = await asyncpg.connect(self.connection_string)
            try:
                rows = await conn.fetch('''
                    SELECT q.id, q.question, q.answer, q.explanation, 
                           q.incorrect_options, q.source, q.image_path,
                           st.name as topic, q.created_at
                    FROM questions q
                    LEFT JOIN subtopics st ON q.topic_id = st.id
                    ORDER BY q.created_at DESC
                ''')
                
                questions = []
                for row in rows:
                    # Parse incorrect_options if it's JSON string
                    incorrect_options = row['incorrect_options']
                    if isinstance(incorrect_options, str):
                        try:
                            incorrect_options = json.loads(incorrect_options)
                        except:
                            incorrect_options = incorrect_options.split('\n') if incorrect_options else []
                    
                    questions.append({
                        'id': row['id'],
                        'question': row['question'],
                        'answer': row['answer'],
                        'explanation': row['explanation'],
                        'incorrect_options': incorrect_options,
                        'source': row['source'],
                        'image_path': row['image_path'],
                        'topic': row['topic'],
                        'created_at': row['created_at']
                    })
                return questions
            finally:
                await conn.close()
        
        return self._sync_call(_get_all_questions())

    # ============== USER LANGUAGE METHODS ==============
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's language preference."""
        async def _get_user_language():
            conn = await asyncpg.connect(self.connection_string)
            try:
                result = await conn.fetchval('''
                    SELECT language FROM allowed_users WHERE user_id = $1
                ''', user_id)
                return result or 'ru'
            finally:
                await conn.close()
        
        return self._sync_call(_get_user_language())

    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language preference."""
        async def _update_user_language():
            conn = await asyncpg.connect(self.connection_string)
            try:
                await conn.execute('''
                    UPDATE allowed_users 
                    SET language = $1 
                    WHERE user_id = $2
                ''', language, user_id)
            finally:
                await conn.close()
        
        self._sync_call(_update_user_language())

    # ============== INITIALIZATION METHODS ==============
    
    async def _initialize_main_topics_async(self, conn) -> bool:
        """Initialize main topics structure with existing connection."""
        try:
            # Create Russian main topics
            russian_topics = [
                ("Арифметика", ["Арифметические задачи", "Пропорции", "Проценты"]),
                ("Алгебра", ["Уравнения", "Неравенства", "Функции"]),
                ("Геометрия", ["Планиметрия", "Стереометрия", "Тригонометрия"]),
                ("Логика", ["Логические задачи", "Числовые последовательности", "Вероятность"])
            ]
            
            for i, (main_topic, subtopics) in enumerate(russian_topics):
                main_topic_id = await conn.fetchval('''
                    INSERT INTO main_topics (name, language, order_index) 
                    VALUES ($1, 'ru', $2) 
                    RETURNING id
                ''', main_topic, i)
                
                for j, subtopic in enumerate(subtopics):
                    await conn.execute('''
                        INSERT INTO subtopics (name, main_topic_id, order_index) 
                        VALUES ($1, $2, $3)
                    ''', subtopic, main_topic_id, j)
            
            # Create Kazakh main topics
            kazakh_topics = [
                ("Арифметика", ["Арифметикалық есептер", "Пропорция", "Пайыз есептеулері"]),
                ("Алгебра", ["Теңдеулер", "Теңсіздіктер", "Функциялар"]),
                ("Геометрия", ["Планиметрия", "Стереометрия", "Тригонометрия"]),
                ("Логика", ["Логикалық сұрақтар", "Сандық тізбектер", "Ықтималдық"])
            ]
            
            for i, (main_topic, subtopics) in enumerate(kazakh_topics):
                main_topic_id = await conn.fetchval('''
                    INSERT INTO main_topics (name, language, order_index) 
                    VALUES ($1, 'kk', $2) 
                    RETURNING id
                ''', main_topic, i)
                
                for j, subtopic in enumerate(subtopics):
                    await conn.execute('''
                        INSERT INTO subtopics (name, main_topic_id, order_index) 
                        VALUES ($1, $2, $3)
                    ''', subtopic, main_topic_id, j)
            
            return True
        except Exception as e:
            logging.error(f"Error initializing main topics: {e}")
            return False

    # ============== PLACEHOLDER METHODS ==============
    # Эти методы нужно будет реализовать для полной совместимости
    
    def register_user(self, user_id: int, username: str) -> None:
        """Register new user - placeholder."""
        pass
    
    def get_user_info(self, user_id: int):
        """Get user info - placeholder."""
        return None
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user info - placeholder."""
        pass
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get error tasks for user - placeholder."""
        return []
    
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add user error - placeholder."""
        pass
    
    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count - placeholder."""
        pass 