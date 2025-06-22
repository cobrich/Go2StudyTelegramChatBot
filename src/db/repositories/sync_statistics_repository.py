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
            query = """
                INSERT INTO test_results (user_id, topic, percentage, completed_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            self.execute_query(query, (user_id, topic, percentage))
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
                SELECT topic, percentage, completed_at
                FROM test_results
                WHERE user_id = %s
                ORDER BY completed_at DESC
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
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add user error (sync) - ONLY for students, NOT for admins"""
        logger.info(f"❌ Adding error for user {user_id}, topic: {topic}")
        
        # ✅ ПРОВЕРКА: Админы НЕ должны попадать в статистику ошибок студентов
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - error NOT recorded in student statistics")
            return
        
        try:
            query = """
                INSERT INTO user_errors (user_id, topic, question_text, user_answer_text,
                                       correct_answer_text, explanation_text, error_date)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            self.execute_query(query, (
                user_id, topic, question_text, user_answer_text,
                correct_answer_text, explanation_text
            ))
            logger.info(f"✅ Error added successfully for student {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error adding user error: {e}")
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID (sync) - ONLY for students"""
        logger.info(f"❌ Adding error by question ID for user {user_id}, question_id: {question_id}")
        
        # ✅ ПРОВЕРКА: Админы НЕ должны попадать в статистику ошибок
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - error NOT recorded in student statistics")
            return
        
        try:
            # Сначала получаем текст вопроса и объяснение
            question_query = """
                SELECT question_text, explanation
                FROM questions
                WHERE id = %s
            """
            question_data = self.fetch_one(question_query, (question_id,))
            
            if not question_data:
                logger.error(f"❌ Question {question_id} not found")
                return
            
            # Добавляем ошибку
            self.add_user_error(
                user_id=user_id,
                topic=topic,
                question_text=question_data['question_text'],
                user_answer_text=user_answer_text,
                correct_answer_text=correct_answer_text,
                explanation_text=question_data['explanation']
            )
            
        except Exception as e:
            logger.error(f"❌ Error adding user error by question ID: {e}")
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        """Get error tasks for user (sync) - ONLY for students"""
        logger.info(f"🔍 Getting error tasks for user {user_id}, topic: {topic}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student error tasks")
            return []
        
        try:
            query = """
                SELECT DISTINCT question_text as question, correct_answer_text as answer,
                       explanation_text as explanation, topic,
                       '' as incorrect_options, NULL as image_path
                FROM user_errors
                WHERE user_id = %s AND topic = %s
                ORDER BY error_date DESC
                LIMIT %s
            """
            result = self.fetch_all(query, (user_id, topic, limit))
            
            error_tasks = []
            for row in result:
                task = {
                    'question': row['question'],
                    'answer': row['answer'],
                    'explanation': row['explanation'],
                    'topic': row['topic'],
                    'incorrect_options': row['incorrect_options'],
                    'image_path': row['image_path']
                }
                error_tasks.append(task)
            
            logger.info(f"📊 Found {len(error_tasks)} error tasks")
            return error_tasks
            
        except Exception as e:
            logger.error(f"❌ Error getting error tasks: {e}")
            return []
    
    def get_error_topics(self, user_id: int) -> List[Tuple[str, int]]:
        """Get topics with error counts for user (sync) - ONLY for students"""
        logger.info(f"📊 Getting error topics for user: {user_id}")
        
        # ✅ ПРОВЕРКА: Админы не имеют студенческих ошибок
        if self._is_admin(user_id):
            logger.info(f"🔒 Admin {user_id} - no student error topics")
            return []
        
        try:
            query = """
                SELECT topic, COUNT(*) as error_count
                FROM user_errors
                WHERE user_id = %s
                GROUP BY topic
                ORDER BY error_count DESC
                LIMIT 10
            """
            result = self.fetch_all(query, (user_id,))
            
            error_topics = []
            for row in result:
                error_topics.append((row['topic'], row['error_count']))
            
            logger.info(f"📊 Found {len(error_topics)} topics with errors")
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
            # Удаляем одну ошибку для данного вопроса
            query = """
                DELETE FROM user_errors
                WHERE user_id = %s AND question_text = %s
                AND id = (
                    SELECT id FROM user_errors
                    WHERE user_id = %s AND question_text = %s
                    ORDER BY error_date DESC
                    LIMIT 1
                )
            """
            self.execute_query(query, (user_id, question_text, user_id, question_text))
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
            # Сначала получаем текст вопроса
            question_query = "SELECT question_text FROM questions WHERE id = %s"
            question_data = self.fetch_one(question_query, (question_id,))
            
            if question_data:
                self.decrement_error_count(user_id, question_data['question_text'])
            else:
                logger.warning(f"⚠️ Question {question_id} not found for error decrement")
                
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
            # Основная статистика
            total_tests, avg_score = self.get_user_progress(user_id)
            
            # Последние результаты
            recent_results = self.get_user_test_results(user_id)
            
            # Темы с ошибками
            error_topics = self.get_error_topics(user_id)
            
            # Общее количество ошибок
            total_errors_query = "SELECT COUNT(*) as total_errors FROM user_errors WHERE user_id = %s"
            total_errors_result = self.fetch_one(total_errors_query, (user_id,))
            total_errors = total_errors_result['total_errors'] if total_errors_result else 0
            
            statistics = {
                'user_id': user_id,
                'total_tests': total_tests,
                'average_score': avg_score,
                'total_errors': total_errors,
                'recent_results': recent_results[:10],  # Последние 10 результатов
                'error_topics': error_topics[:5],  # Топ-5 проблемных тем
                'improvement_trend': self._calculate_improvement_trend(recent_results)
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