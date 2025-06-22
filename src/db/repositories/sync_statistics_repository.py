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
    
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result (sync)"""
        logger.info(f"📊 Adding test result: user_id={user_id}, topic={topic}, percentage={percentage}")
        
        try:
            query = """
                INSERT INTO test_results (user_id, topic, percentage, completed_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            self.execute_query(query, (user_id, topic, percentage))
            logger.info(f"✅ Test result added successfully")
            
        except Exception as e:
            logger.error(f"❌ Error adding test result: {e}")
    
    def get_user_test_results(self, user_id: int) -> List[Dict]:
        """Get user test results (sync)"""
        logger.info(f"📋 Getting test results for user: {user_id}")
        
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
        """Get user progress summary (sync)"""
        logger.info(f"📈 Getting progress for user: {user_id}")
        
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
        """Add user error (sync)"""
        logger.info(f"❌ Adding error for user {user_id}, topic: {topic}")
        
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
            logger.info(f"✅ Error added successfully")
            
        except Exception as e:
            logger.error(f"❌ Error adding user error: {e}")
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID (sync)"""
        logger.info(f"❌ Adding error by question ID for user {user_id}, question_id: {question_id}")
        
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
        """Get error tasks for user (sync)"""
        logger.info(f"🔍 Getting error tasks for user {user_id}, topic: {topic}")
        
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
        """Get topics with error counts for user (sync)"""
        logger.info(f"📊 Getting error topics for user: {user_id}")
        
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
        """Get recent topics with scores (sync)"""
        logger.info(f"🕒 Getting recent topics for user: {user_id}")
        
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
        """Get recent unique topics with attempt counts (sync)"""
        logger.info(f"🔄 Getting recent unique topics for user: {user_id}")
        
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
        """Decrement error count for a question (sync)"""
        logger.info(f"⬇️ Decrementing error count for user {user_id}")
        
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
            logger.info(f"✅ Error count decremented")
            
        except Exception as e:
            logger.error(f"❌ Error decrementing error count: {e}")
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question ID (sync)"""
        logger.info(f"⬇️ Decrementing error count by question ID for user {user_id}")
        
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
        """Get detailed statistics for a student (sync)"""
        logger.info(f"📊 Getting detailed statistics for user: {user_id}")
        
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
            
            logger.info(f"📊 Detailed statistics calculated for user {user_id}")
            return statistics
            
        except Exception as e:
            logger.error(f"❌ Error getting detailed statistics: {e}")
            return None
    
    def _calculate_improvement_trend(self, recent_results: List[Dict]) -> str:
        """Calculate improvement trend based on recent results"""
        if len(recent_results) < 3:
            return "insufficient_data"
        
        # Берем последние 5 результатов для анализа тренда
        last_5 = recent_results[:5]
        scores = [result['percentage'] for result in last_5]
        
        # Простой анализ тренда
        if len(scores) >= 3:
            recent_avg = sum(scores[:3]) / 3  # Последние 3 теста
            older_avg = sum(scores[2:]) / len(scores[2:])  # Более старые тесты
            
            if recent_avg > older_avg + 5:
                return "improving"
            elif recent_avg < older_avg - 5:
                return "declining"
            else:
                return "stable"
        
        return "stable" 