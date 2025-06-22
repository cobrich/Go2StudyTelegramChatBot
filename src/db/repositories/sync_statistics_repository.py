"""
Synchronous Statistics Repository for Neon PostgreSQL

Handles statistics and error tracking database operations synchronously.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncStatisticsRepository(SyncBaseRepository):
    """Synchronous repository for statistics and error tracking operations"""
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin (to exclude from student statistics)"""
        try:
            query = "SELECT 1 FROM admins WHERE user_id = %s"
            result = self.fetch_val(query, (user_id,))
            return result is not None
        except Exception as e:
            logger.error(f"Error checking admin status for {user_id}: {e}")
            return False
    
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result (sync) - ONLY for students, NOT for admins"""
        logger.info(f"📊 Adding test result: user_id={user_id}, topic={topic}, percentage={percentage}")
        
        # ✅ ПРОВЕРКА: Админы НЕ должны попадать в статистику студентов
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - test result NOT recorded in student statistics")
            return
        
        try:
            # Найти topic_id по названию темы
            topic_query = """
                SELECT id FROM subtopics 
                WHERE subtopic_name = %s AND is_active = true
                LIMIT 1
            """
            topic_result = self.fetch_one(topic_query, (topic,))
            
            if not topic_result:
                logger.error(f"❌ Topic '{topic}' not found in subtopics table")
                return
            
            topic_id = topic_result['id']
            
            query = """
                INSERT INTO test_results (user_id, topic_id, percentage, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            self.execute_query(query, (user_id, topic_id, percentage))
            logger.info(f"✅ Test result added successfully for student {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error adding test result: {e}")
    
    def get_user_test_results(self, user_id: int) -> List[Dict]:
        """Get user test results (sync) - ONLY for students"""
        logger.info(f"📋 Getting test results for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих результатов
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student test results")
            return []
        
        try:
            query = """
                SELECT s.subtopic_name as topic, tr.percentage, tr.created_at as completed_at
                FROM test_results tr
                JOIN subtopics s ON tr.topic_id = s.id
                WHERE tr.user_id = %s
                ORDER BY tr.created_at DESC
                LIMIT 50
            """
            result = self.fetch_all(query, (user_id,))
            
            test_results = []
            for row in result:
                test_result = {
                    'topic': row['topic'],
                    'percentage': row['percentage'],
                    'completed_at': row['completed_at']
                }
                test_results.append(test_result)
            
            logger.info(f"📊 Found {len(test_results)} test results")
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Error getting test results: {e}")
            return []
    
    def get_user_progress(self, user_id: int) -> Tuple[int, float]:
        """Get user progress summary (sync) - ONLY for students"""
        logger.info(f"📈 Getting progress for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческого прогресса
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student progress")
            return 0, 0.0
        
        try:
            query = """
                SELECT COUNT(*) as total_tests, AVG(percentage) as avg_score
                FROM test_results
                WHERE user_id = %s
            """
            result = self.fetch_one(query, (user_id,))
            
            if result:
                total_tests = result['total_tests'] or 0
                avg_score = float(result['avg_score']) if result['avg_score'] else 0.0
                logger.info(f"📊 User progress: {total_tests} tests, {avg_score:.1f}% average")
                return total_tests, avg_score
            else:
                return 0, 0.0
                
        except Exception as e:
            logger.error(f"❌ Error getting user progress: {e}")
            return 0, 0.0
    
    def add_user_error(self, user_id: int, topic: str, question_text: str, 
                      user_answer_text: str, correct_answer_text: str, explanation_text: str) -> bool:
        """Add user error (sync) - OPTIMIZED"""
        try:
            # Сначала найдем question_id по тексту вопроса
            find_question_query = """
                SELECT q.id 
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE q.question_text = %s AND s.subtopic_name = %s
                LIMIT 1
            """
            question_result = self.fetch_one(find_question_query, (question_text, topic))
            
            if not question_result:
                logger.warning(f"Question not found for text: {question_text[:50]}...")
                return False
            
            question_id = question_result['id']
            
            # Быстрая вставка без дополнительных проверок
            query = """
                INSERT INTO user_errors (user_id, question_id, user_answer, correct_answer, error_count)
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (user_id, question_id) 
                DO UPDATE SET 
                    error_count = user_errors.error_count + 1,
                    user_answer = EXCLUDED.user_answer,
                    last_error_date = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, question_id, user_answer_text, correct_answer_text))
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding user error: {e}")
            return False
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str, 
                                      user_answer_text: str, correct_answer_text: str) -> bool:
        """Add user error by question ID (sync) - OPTIMIZED"""
        try:
            # Быстрая вставка без дополнительных проверок
            query = """
                INSERT INTO user_errors (user_id, question_id, user_answer, correct_answer, error_count)
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (user_id, question_id) 
                DO UPDATE SET 
                    error_count = user_errors.error_count + 1,
                    user_answer = EXCLUDED.user_answer,
                    last_error_date = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, question_id, user_answer_text, correct_answer_text))
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding error by question ID: {e}")
            return False
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        """Get error tasks for user (sync) - ONLY for students"""
        logger.info(f"🔍 Getting error tasks for user {user_id}, topic: {topic}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student error tasks")
            return []
        
        try:
            query = """
                SELECT DISTINCT q.question_text as question, 
                       CASE q.correct_answer
                           WHEN 'A' THEN q.option_a
                           WHEN 'B' THEN q.option_b
                           WHEN 'C' THEN q.option_c
                           WHEN 'D' THEN q.option_d
                           ELSE q.correct_answer
                       END as answer,
                       q.explanation as explanation, s.subtopic_name as topic,
                       q.incorrect_options, NULL as image_path, ue.last_error_date,
                       ue.error_count, q.id,
                       q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer as correct_letter
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                WHERE ue.user_id = %s AND s.subtopic_name = %s
                ORDER BY ue.last_error_date DESC
                LIMIT %s
            """
            result = self.fetch_all(query, (user_id, topic, limit))
            
            error_tasks = []
            for row in result:
                # Создаем список всех вариантов ответов
                all_options = [row['option_a'], row['option_b'], row['option_c'], row['option_d']]
                # Убираем пустые варианты
                all_options = [opt for opt in all_options if opt and opt.strip()]
                
                task = {
                    'id': row['id'],
                    'question': row['question'],
                    'answer': row['answer'],  # Теперь это текст правильного ответа
                    'explanation': row['explanation'],
                    'topic': row['topic'],
                    'incorrect_options': row['incorrect_options'],
                    'image_path': row['image_path'],
                    'error_count': row['error_count'],
                    'all_options': all_options,  # Все варианты ответов для формирования теста
                    'correct_letter': row['correct_letter']  # Буква правильного ответа (A, B, C, D)
                }
                error_tasks.append(task)
            
            logger.info(f"📊 Found {len(error_tasks)} error tasks")
            return error_tasks
            
        except Exception as e:
            logger.error(f"❌ Error getting error tasks: {e}")
            return []
    
    def get_error_topics(self, user_id: int) -> List[Tuple[str, int]]:
        """Get error topics for user (sync) - ONLY for students"""
        logger.info(f"📊 Getting error topics for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student error topics")
            return []
        
        try:
            query = """
                SELECT s.subtopic_name as topic, SUM(ue.error_count) as error_count
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                WHERE ue.user_id = %s
                GROUP BY s.subtopic_name
                ORDER BY error_count DESC
                LIMIT 10
            """
            result = self.fetch_all(query, (user_id,))
            
            error_topics = []
            for row in result:
                error_topics.append((row['topic'], row['error_count']))
            
            logger.info(f"📊 Found {len(error_topics)} error topics")
            return error_topics
            
        except Exception as e:
            logger.error(f"❌ Error getting error topics: {e}")
            return []
    
    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[Tuple[str, float, str]]:
        """Get recent topics with scores (sync) - ONLY for students"""
        logger.info(f"🕒 Getting recent topics for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих результатов
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student recent topics")
            return []
        
        try:
            query = """
                SELECT topic, percentage, completed_at
                FROM test_results
                WHERE user_id = %s
                ORDER BY completed_at DESC
                LIMIT %s
            """
            result = self.fetch_all(query, (user_id, limit))
            
            recent_topics = []
            for row in result:
                recent_topics.append((
                    row['topic'],
                    row['percentage'],
                    str(row['completed_at'])
                ))
            
            logger.info(f"📊 Found {len(recent_topics)} recent topics")
            return recent_topics
            
        except Exception as e:
            logger.error(f"❌ Error getting recent topics: {e}")
            return []
    
    def get_recent_unique_topics(self, user_id: int, unique_limit: int = 5, 
                                history_limit: int = 20) -> List[Tuple[str, int]]:
        """Get recent unique topics with attempt counts (sync) - ONLY for students"""
        logger.info(f"🔄 Getting recent unique topics for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих результатов
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student unique topics")
            return []
        
        try:
            query = """
                SELECT topic, COUNT(*) as attempt_count
                FROM (
                    SELECT topic
                    FROM test_results
                    WHERE user_id = %s
                    ORDER BY completed_at DESC
                    LIMIT %s
                ) recent_tests
                GROUP BY topic
                ORDER BY MAX(completed_at) DESC
                LIMIT %s
            """
            result = self.fetch_all(query, (user_id, history_limit, unique_limit))
            
            unique_topics = []
            for row in result:
                unique_topics.append((row['topic'], row['attempt_count']))
            
            logger.info(f"📊 Found {len(unique_topics)} unique recent topics")
            return unique_topics
            
        except Exception as e:
            logger.error(f"❌ Error getting recent unique topics: {e}")
            return []
    
    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count for a question (sync) - ONLY for students"""
        logger.info(f"⬇️ Decrementing error count for user {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок для декремента
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student errors to decrement")
            return
        
        try:
            # Сначала найдем question_id по тексту вопроса
            find_question_query = """
                SELECT id FROM questions WHERE question_text = %s LIMIT 1
            """
            question_result = self.fetch_one(find_question_query, (question_text,))
            
            if not question_result:
                logger.warning(f"Question not found for decrement: {question_text[:50]}...")
                return
            
            question_id = question_result['id']
            
            # Уменьшаем счетчик ошибок или удаляем запись если count = 1
            query = """
                UPDATE user_errors 
                SET error_count = error_count - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND question_id = %s AND error_count > 1
            """
            self.execute_query(query, (user_id, question_id))
            
            # Удаляем записи с error_count = 0
            delete_query = """
                DELETE FROM user_errors 
                WHERE user_id = %s AND question_id = %s AND error_count <= 1
            """
            self.execute_query(delete_query, (user_id, question_id))
            
            logger.info(f"✅ Error count decremented for student {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error decrementing error count: {e}")
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question ID (sync) - ONLY for students"""
        logger.info(f"⬇️ Decrementing error count by question ID for user {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок для декремента
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student errors to decrement")
            return
        
        try:
            # Уменьшаем счетчик ошибок или удаляем запись если count = 1
            query = """
                UPDATE user_errors 
                SET error_count = error_count - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND question_id = %s AND error_count > 1
            """
            self.execute_query(query, (user_id, question_id))
            
            # Удаляем записи с error_count = 0
            delete_query = """
                DELETE FROM user_errors 
                WHERE user_id = %s AND question_id = %s AND error_count <= 1
            """
            self.execute_query(delete_query, (user_id, question_id))
            
            logger.info(f"✅ Error count decremented for student {user_id}")
                
        except Exception as e:
            logger.error(f"❌ Error decrementing error count by question ID: {e}")
    
    def get_student_detailed_statistics(self, user_id: int) -> Optional[Dict]:
        """Get detailed statistics for a student (sync) - ONLY for students"""
        logger.info(f"📊 Getting detailed statistics for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческой статистики
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student detailed statistics")
            return None
        
        try:
            # 1. Получаем информацию о пользователе
            user_query = """
                SELECT user_id, username, full_name, grade, language, 
                       last_activity, added_at
                FROM allowed_users
                WHERE user_id = %s
            """
            user_data = self.fetch_one(user_query, (user_id,))
            
            if not user_data:
                logger.warning(f"User {user_id} not found")
                return None
            
            # 2. Статистика тестов
            test_stats_query = """
                SELECT 
                    COUNT(*) as total_tests,
                    AVG(percentage) as avg_score,
                    MAX(percentage) as max_score,
                    MIN(percentage) as min_score,
                    MIN(created_at) as first_test,
                    MAX(created_at) as last_test
                FROM test_results
                WHERE user_id = %s
            """
            test_stats = self.fetch_one(test_stats_query, (user_id,))
            
            # 3. Активность по дням (последние 10 дней)
            daily_query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as tests_count,
                    AVG(percentage) as avg_score
                FROM test_results
                WHERE user_id = %s AND created_at >= CURRENT_DATE - INTERVAL '10 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 10
            """
            daily_progress = self.fetch_all(daily_query, (user_id,))
            
            # 4. Результаты по темам
            topic_performance_query = """
                SELECT 
                    s.subtopic_name as topic,
                    COUNT(*) as tests_count,
                    AVG(tr.percentage) as avg_score,
                    MAX(tr.created_at) as last_attempt
                FROM test_results tr
                JOIN subtopics s ON tr.topic_id = s.id
                WHERE tr.user_id = %s
                GROUP BY s.subtopic_name
                ORDER BY avg_score DESC
            """
            topic_performance = self.fetch_all(topic_performance_query, (user_id,))
            
            # 5. Анализ ошибок по темам
            error_analysis_query = """
                SELECT 
                    s.subtopic_name as topic,
                    COUNT(DISTINCT ue.question_id) as unique_errors,
                    SUM(ue.error_count) as total_errors,
                    MAX(ue.last_error_date) as last_error
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                WHERE ue.user_id = %s
                GROUP BY s.subtopic_name
                ORDER BY total_errors DESC
                LIMIT 10
            """
            error_analysis = self.fetch_all(error_analysis_query, (user_id,))
            
            # 6. Последние ошибки
            recent_errors_query = """
                SELECT 
                    s.subtopic_name as topic,
                    q.question_text as question,
                    ue.error_count,
                    ue.last_error_date as timestamp
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                WHERE ue.user_id = %s
                ORDER BY ue.last_error_date DESC
                LIMIT 10
            """
            recent_errors = self.fetch_all(recent_errors_query, (user_id,))
            
            # Формируем результат
            statistics = {
                'user_info': {
                    'user_id': user_data['user_id'],
                    'username': user_data['username'],
                    'full_name': user_data['full_name'],
                    'grade': user_data['grade'],
                    'language': user_data['language'],
                    'last_activity': user_data['last_activity'].isoformat() if user_data['last_activity'] else None,
                    'added_to_whitelist': user_data['added_at'].isoformat() if user_data['added_at'] else None
                },
                'test_statistics': {
                    'total_tests': test_stats['total_tests'] if test_stats else 0,
                    'avg_score': round(test_stats['avg_score'] or 0, 1) if test_stats else 0,
                    'max_score': round(test_stats['max_score'] or 0, 1) if test_stats else 0,
                    'min_score': round(test_stats['min_score'] or 0, 1) if test_stats else 0,
                    'first_test': test_stats['first_test'].isoformat() if test_stats and test_stats['first_test'] else None,
                    'last_test': test_stats['last_test'].isoformat() if test_stats and test_stats['last_test'] else None
                },
                'daily_progress': [
                    {
                        'date': str(day['date']),
                        'tests_count': day['tests_count'],
                        'avg_score': round(day['avg_score'] or 0, 1)
                    }
                    for day in daily_progress
                ],
                'topic_performance': [
                    {
                        'topic': topic['topic'],
                        'tests_count': topic['tests_count'],
                        'avg_score': round(topic['avg_score'] or 0, 1),
                        'last_attempt': topic['last_attempt'].isoformat() if topic['last_attempt'] else None
                    }
                    for topic in topic_performance
                ],
                'error_analysis': [
                    {
                        'topic': error['topic'],
                        'unique_errors': error['unique_errors'],
                        'total_errors': error['total_errors'],
                        'last_error': error['last_error'].isoformat() if error['last_error'] else None
                    }
                    for error in error_analysis
                ],
                'recent_errors': [
                    {
                        'topic': error['topic'],
                        'question': error['question'],
                        'error_count': error['error_count'],
                        'timestamp': error['timestamp'].isoformat() if error['timestamp'] else None
                    }
                    for error in recent_errors
                ]
            }
            
            logger.info(f"📊 Detailed statistics calculated for student {user_id}")
            return statistics
            
        except Exception as e:
            logger.error(f"❌ Error getting detailed statistics: {e}")
            return None
    
    def _calculate_improvement_trend(self, recent_results: List[Dict]) -> str:
        """Calculate improvement trend from recent results"""
        if len(recent_results) < 2:
            return "insufficient_data"
        
        # Sort by date
        sorted_results = sorted(recent_results, key=lambda x: x['completed_at'])
        
        # Compare first half with second half
        mid_point = len(sorted_results) // 2
        first_half_avg = sum(r['percentage'] for r in sorted_results[:mid_point]) / mid_point
        second_half_avg = sum(r['percentage'] for r in sorted_results[mid_point:]) / (len(sorted_results) - mid_point)
        
        difference = second_half_avg - first_half_avg
        
        if difference > 5:
            return "improving"
        elif difference < -5:
            return "declining"
        else:
            return "stable"
    
    # Additional methods from main branch
    def get_error_tasks_for_user_by_topic_id(self, user_id: int, topic_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get error tasks for user by topic ID"""
        try:
            query = """
                SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.correct_answer, ue.user_answer, ue.error_count, ue.last_error_date,
                       s.subtopic_name as topic
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                WHERE ue.user_id = %s AND q.topic_id = %s AND ue.error_count > 0
                ORDER BY ue.error_count DESC, ue.last_error_date DESC
                LIMIT %s
            """
            
            result = self.fetch_all(query, (user_id, topic_id, limit))
            logger.info(f"📊 Found {len(result)} error tasks for user {user_id}, topic_id {topic_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting error tasks for user {user_id}, topic_id {topic_id}: {e}")
            return []
    
    def get_user_display_info(self, user_id: int) -> Dict[str, Any]:
        """Get user display info with statistics"""
        try:
            # Get basic user info
            user_query = """
                SELECT user_id, username, full_name, grade, language, has_access
                FROM allowed_users
                WHERE user_id = %s
            """
            user = self.fetch_one(user_query, (user_id,))
            
            if not user:
                return {
                    'user_id': user_id,
                    'username': None,
                    'full_name': None,
                    'grade': None,
                    'language': 'ru',
                    'has_complete_info': False,
                    'test_count': 0,
                    'avg_score': 0
                }
            
            # Get test statistics
            stats_query = """
                SELECT COUNT(*) as test_count, AVG(percentage) as avg_score
                FROM test_results
                WHERE user_id = %s
            """
            stats = self.fetch_one(stats_query, (user_id,))
            
            return {
                'user_id': user_id,
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'grade': user.get('grade'),
                'language': user.get('language', 'ru'),
                'has_access': user.get('has_access', False),
                'has_complete_info': bool(user.get('full_name') and user.get('grade')),
                'test_count': stats.get('test_count', 0) if stats else 0,
                'avg_score': round(stats.get('avg_score', 0) or 0, 2) if stats else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user display info {user_id}: {e}")
            return {
                'user_id': user_id,
                'username': None,
                'full_name': None,
                'grade': None,
                'language': 'ru',
                'has_complete_info': False,
                'test_count': 0,
                'avg_score': 0,
                'error': str(e)
            }
    
    def get_student_contact_info(self, user_id: int) -> Dict[str, Any]:
        """Get student contact info"""
        try:
            query = """
                SELECT user_id, username, full_name, grade
                FROM allowed_users
                WHERE user_id = %s
            """
            user = self.fetch_one(query, (user_id,))
            
            if user:
                return {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'grade': user['grade'],
                    'display_name': user['full_name'] or 'Неизвестен',
                    'display_username': user['username'] or 'не указан'
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting student contact info {user_id}: {e}")
            return {}
    
    def get_comprehensive_statistics(self, user_id: int = None, grade: int = None, 
                                   language: str = None) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        try:
            base_query = """
                SELECT 
                    COUNT(DISTINCT u.user_id) as total_users,
                    COUNT(DISTINCT tr.user_id) as active_users,
                    COUNT(tr.id) as total_tests,
                    AVG(tr.percentage) as avg_score,
                    COUNT(DISTINCT ue.user_id) as users_with_errors
                FROM allowed_users u
                LEFT JOIN test_results tr ON u.user_id = tr.user_id
                LEFT JOIN user_errors ue ON u.user_id = ue.user_id
                WHERE u.has_access = %s
            """
            params = [True]
            
            if user_id:
                base_query += " AND u.user_id = %s"
                params.append(user_id)
            
            if grade:
                base_query += " AND u.grade = %s"
                params.append(grade)
            
            if language:
                base_query += " AND u.language = %s"
                params.append(language)
            
            result = self.fetch_one(base_query, params)
            
            return {
                'total_users': result['total_users'] or 0,
                'active_users': result['active_users'] or 0,
                'total_tests': result['total_tests'] or 0,
                'avg_score': round(result['avg_score'] or 0, 2),
                'users_with_errors': result['users_with_errors'] or 0,
                'filter_user_id': user_id,
                'filter_grade': grade,
                'filter_language': language
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive statistics: {e}")
            return {}
    
    def get_topic_performance_stats(self, topic_name: str = None, language: str = None) -> Dict[str, Any]:
        """Get topic performance statistics"""
        try:
            query = """
                SELECT 
                    s.subtopic_name as topic,
                    m.language,
                    COUNT(tr.id) as test_count,
                    AVG(tr.percentage) as avg_score,
                    COUNT(DISTINCT tr.user_id) as unique_users,
                    COUNT(ue.id) as error_count
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                LEFT JOIN test_results tr ON s.id = tr.topic_id
                LEFT JOIN questions q ON s.id = q.topic_id
                LEFT JOIN user_errors ue ON q.id = ue.question_id
                WHERE s.is_active = %s AND m.is_active = %s
            """
            params = [True, True]
            
            if topic_name:
                query += " AND s.subtopic_name = %s"
                params.append(topic_name)
            
            if language:
                query += " AND m.language = %s"
                params.append(language)
            
            query += """
                GROUP BY s.subtopic_name, m.language
                ORDER BY test_count DESC, avg_score DESC
            """
            
            results = self.fetch_all(query, params)
            
            return {
                'topics': [
                    {
                        'topic': row['topic'],
                        'language': row['language'],
                        'test_count': row['test_count'] or 0,
                        'avg_score': round(row['avg_score'] or 0, 2),
                        'unique_users': row['unique_users'] or 0,
                        'error_count': row['error_count'] or 0,
                        'difficulty_level': self._calculate_difficulty_level(row['avg_score'] or 0)
                    }
                    for row in results
                ],
                'filter_topic': topic_name,
                'filter_language': language
            }
            
        except Exception as e:
            logger.error(f"Error getting topic performance stats: {e}")
            return {}
    
    def _calculate_difficulty_level(self, avg_score: float) -> str:
        """Calculate difficulty level based on average score"""
        if avg_score >= 80:
            return "easy"
        elif avg_score >= 60:
            return "medium"
        elif avg_score >= 40:
            return "hard"
        else:
            return "very_hard"
    
    def get_user_activity_timeline(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get user activity timeline"""
        try:
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as test_count,
                    AVG(percentage) as avg_score
                FROM test_results
                WHERE user_id = %s AND created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            
            results = self.fetch_all(query, (user_id, days))
            
            return [
                {
                    'date': row['date'],
                    'test_count': row['test_count'],
                    'avg_score': round(row['avg_score'], 2),
                    'activity_level': self._calculate_activity_level(row['test_count'])
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting user activity timeline {user_id}: {e}")
            return []
    
    def _calculate_activity_level(self, test_count: int) -> str:
        """Calculate activity level based on test count"""
        if test_count >= 10:
            return "very_high"
        elif test_count >= 5:
            return "high"
        elif test_count >= 2:
            return "medium"
        elif test_count >= 1:
            return "low"
        else:
            return "none"
    
    def get_leaderboard(self, grade: int = None, language: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard"""
        try:
            query = """
                SELECT 
                    u.user_id,
                    u.username,
                    u.full_name,
                    u.grade,
                    u.language,
                    COUNT(tr.id) as test_count,
                    AVG(tr.percentage) as avg_score,
                    MAX(tr.created_at) as last_test_date
                FROM allowed_users u
                JOIN test_results tr ON u.user_id = tr.user_id
                WHERE u.has_access = %s
            """
            params = [True]
            
            if grade:
                query += " AND u.grade = %s"
                params.append(grade)
            
            if language:
                query += " AND u.language = %s"
                params.append(language)
            
            query += """
                GROUP BY u.user_id, u.username, u.full_name, u.grade, u.language
                HAVING COUNT(tr.id) >= 3
                ORDER BY avg_score DESC, test_count DESC
                LIMIT %s
            """
            params.append(limit)
            
            results = self.fetch_all(query, params)
            
            return [
                {
                    'rank': idx + 1,
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'full_name': row['full_name'],
                    'grade': row['grade'],
                    'language': row['language'],
                    'test_count': row['test_count'],
                    'avg_score': round(row['avg_score'], 2),
                    'last_test_date': row['last_test_date'],
                    'display_name': row['full_name'] or row['username'] or f"User {row['user_id']}"
                }
                for idx, row in enumerate(results)
            ]
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def get_error_analysis(self, user_id: int = None, topic_name: str = None) -> Dict[str, Any]:
        """Get error analysis"""
        try:
            query = """
                SELECT 
                    s.subtopic_name as topic,
                    m.language,
                    COUNT(ue.id) as total_errors,
                    COUNT(DISTINCT ue.user_id) as users_with_errors,
                    AVG(ue.error_count) as avg_errors_per_question,
                    COUNT(DISTINCT ue.question_id) as questions_with_errors
                FROM user_errors ue
                JOIN questions q ON ue.question_id = q.id
                JOIN subtopics s ON q.topic_id = s.id
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE ue.error_count > 0
            """
            params = []
            
            if user_id:
                query += " AND ue.user_id = %s"
                params.append(user_id)
            
            if topic_name:
                query += " AND s.subtopic_name = %s"
                params.append(topic_name)
            
            query += """
                GROUP BY s.subtopic_name, m.language
                ORDER BY total_errors DESC
            """
            
            results = self.fetch_all(query, params)
            
            return {
                'error_topics': [
                    {
                        'topic': row['topic'],
                        'language': row['language'],
                        'total_errors': row['total_errors'],
                        'users_with_errors': row['users_with_errors'],
                        'avg_errors_per_question': round(row['avg_errors_per_question'], 2),
                        'questions_with_errors': row['questions_with_errors'],
                        'error_rate': self._calculate_error_rate(row['total_errors'], row['users_with_errors'])
                    }
                    for row in results
                ],
                'filter_user_id': user_id,
                'filter_topic': topic_name
            }
            
        except Exception as e:
            logger.error(f"Error getting error analysis: {e}")
            return {}
    
    def _calculate_error_rate(self, total_errors: int, users_with_errors: int) -> str:
        """Calculate error rate category"""
        if users_with_errors == 0:
            return "none"
        
        avg_errors_per_user = total_errors / users_with_errors
        
        if avg_errors_per_user >= 5:
            return "very_high"
        elif avg_errors_per_user >= 3:
            return "high"
        elif avg_errors_per_user >= 1.5:
            return "medium"
        else:
            return "low" 