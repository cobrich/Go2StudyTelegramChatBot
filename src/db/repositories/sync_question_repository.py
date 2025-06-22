"""
Synchronous Question Repository for Neon PostgreSQL

Handles question-related database operations synchronously.
"""

import logging
from typing import Optional, List, Dict, Any
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncQuestionRepository(SyncBaseRepository):
    """Synchronous repository for question operations"""
    
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get all topic names (sync)"""
        logger.info(f"🔍 Getting topic names, active_only={active_only}")
        
        try:
            if active_only:
                query = "SELECT name FROM subtopics WHERE is_active = %s ORDER BY order_index"
                result = self.fetch_all(query, (True,))
            else:
                query = "SELECT name FROM subtopics ORDER BY order_index"
                result = self.fetch_all(query)
            
            topic_names = [row['name'] for row in result]
            logger.info(f"📊 Found {len(topic_names)} topics")
            return topic_names
            
        except Exception as e:
            logger.error(f"❌ Error getting topic names: {e}")
            return []
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict]:
        """Get tasks for a specific topic (sync)"""
        logger.info(f"🔍 Getting tasks for topic: {topic}, limit: {limit}")
        
        try:
            query = """
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.incorrect_options, q.image_path, q.source,
                       s.name as topic
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE s.name = %s AND s.is_active = %s
                ORDER BY RANDOM()
                LIMIT %s
            """
            result = self.fetch_all(query, (topic, True, limit))
            
            # Преобразуем результат в нужный формат
            tasks = []
            for row in result:
                task = {
                    'id': row['id'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'explanation': row['explanation'],
                    'incorrect_options': row['incorrect_options'],
                    'image_path': row['image_path'],
                    'source': row['source'],
                    'topic': row['topic']
                }
                tasks.append(task)
            
            logger.info(f"📊 Found {len(tasks)} tasks for topic '{topic}'")
            return tasks
            
        except Exception as e:
            logger.error(f"❌ Error getting tasks for topic '{topic}': {e}")
            return []
    
    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation by question text (sync)"""
        logger.info(f"🔍 Getting explanation for question: {question_text[:50]}...")
        
        try:
            query = "SELECT explanation FROM questions WHERE question_text = %s LIMIT 1"
            result = self.fetch_val(query, (question_text,))
            
            if result:
                logger.info(f"📊 Found explanation for question")
                return result
            else:
                logger.info(f"📊 No explanation found for question")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting explanation: {e}")
            return None
    
    def add_question(self, question: dict) -> bool:
        """Add a new question (sync)"""
        logger.info(f"➕ Adding question: {question.get('question', 'Unknown')[:50]}...")
        
        try:
            # Сначала получаем topic_id по названию темы
            topic_name = question.get('topic')
            if not topic_name:
                logger.error("❌ Topic name is required")
                return False
            
            topic_query = "SELECT id FROM subtopics WHERE name = %s LIMIT 1"
            topic_result = self.fetch_val(topic_query, (topic_name,))
            
            if not topic_result:
                logger.error(f"❌ Topic '{topic_name}' not found")
                return False
            
            topic_id = topic_result
            
            # Добавляем вопрос
            query = """
                INSERT INTO questions (topic_id, question_text, correct_answer, explanation, 
                                     incorrect_options, question_type, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(query, (
                topic_id,
                question.get('question'),
                question.get('answer'),
                question.get('explanation'),
                question.get('incorrect_options', ''),
                question.get('question_type', 'standard'),
                question.get('source', 'manual')
            ))
            
            logger.info(f"✅ Question added successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding question: {e}")
            return False
    
    def get_all_questions(self) -> List[Dict]:
        """Get all questions (sync)"""
        logger.info("📋 Getting all questions")
        
        try:
            query = """
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.incorrect_options, q.image_path, q.source,
                       s.name as topic, q.created_at
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                ORDER BY q.created_at DESC
            """
            result = self.fetch_all(query)
            
            questions = []
            for row in result:
                question = {
                    'id': row['id'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'explanation': row['explanation'],
                    'incorrect_options': row['incorrect_options'],
                    'image_path': row['image_path'],
                    'source': row['source'],
                    'topic': row['topic'],
                    'created_at': row['created_at']
                }
                questions.append(question)
            
            logger.info(f"📊 Found {len(questions)} questions")
            return questions
            
        except Exception as e:
            logger.error(f"❌ Error getting all questions: {e}")
            return []
    
    def get_questions_by_language(self, language: str) -> List[Dict]:
        """Get questions by language (sync)"""
        logger.info(f"🔍 Getting questions for language: {language}")
        
        try:
            query = """
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.incorrect_options, q.image_path, q.source,
                       s.name as topic
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE m.language = %s AND s.is_active = %s AND m.is_active = %s
                ORDER BY RANDOM()
            """
            result = self.fetch_all(query, (language, True, True))
            
            questions = []
            for row in result:
                question = {
                    'id': row['id'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'explanation': row['explanation'],
                    'incorrect_options': row['incorrect_options'],
                    'image_path': row['image_path'],
                    'source': row['source'],
                    'topic': row['topic']
                }
                questions.append(question)
            
            logger.info(f"📊 Found {len(questions)} questions for language '{language}'")
            return questions
            
        except Exception as e:
            logger.error(f"❌ Error getting questions by language '{language}': {e}")
            return []
    
    def delete_question_by_id(self, question_id: int) -> bool:
        """Delete question by ID (sync)"""
        logger.info(f"🗑️ Deleting question ID: {question_id}")
        
        try:
            query = "DELETE FROM questions WHERE id = %s"
            self.execute_query(query, (question_id,))
            logger.info(f"✅ Question {question_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting question {question_id}: {e}")
            return False
    
    def get_all_ai_questions(self) -> List[Dict]:
        """Get all AI-generated questions (sync)"""
        logger.info("🤖 Getting all AI questions")
        
        try:
            query = """
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.incorrect_options, s.name as topic
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE q.source = %s OR q.source = %s
                ORDER BY q.created_at DESC
            """
            result = self.fetch_all(query, ('ai', 'ai_retake'))
            
            questions = []
            for row in result:
                question = {
                    'id': row['id'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'explanation': row['explanation'],
                    'incorrect_options': row['incorrect_options'],
                    'topic': row['topic']
                }
                questions.append(question)
            
            logger.info(f"📊 Found {len(questions)} AI questions")
            return questions
            
        except Exception as e:
            logger.error(f"❌ Error getting AI questions: {e}")
            return [] 