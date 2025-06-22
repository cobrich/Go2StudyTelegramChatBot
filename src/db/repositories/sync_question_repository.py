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
            
            topic_query = "SELECT id FROM subtopics WHERE subtopic_name = %s LIMIT 1"
            topic_result = self.fetch_val(topic_query, (topic_name,))
            
            if not topic_result:
                logger.error(f"❌ Topic '{topic_name}' not found")
                return False
            
            topic_id = topic_result
            
            # Обрабатываем варианты ответов
            correct_answer_text = question.get('answer', '')
            incorrect_options = question.get('incorrect_options', '').split('\n')
            
            # Убираем пустые строки
            incorrect_options = [opt.strip() for opt in incorrect_options if opt.strip()]
            
            # Создаем список всех вариантов (правильный + неправильные)
            all_options = [correct_answer_text] + incorrect_options
            
            # Дополняем до 4 вариантов если нужно
            while len(all_options) < 4:
                all_options.append(f"Вариант {len(all_options) + 1}")
            
            # Берем только первые 4 варианта
            all_options = all_options[:4]
            
            # Перемешиваем варианты и запоминаем позицию правильного ответа
            import random
            correct_position = 0  # Правильный ответ всегда на первой позиции изначально
            random.shuffle(all_options)
            
            # Находим новую позицию правильного ответа после перемешивания
            try:
                correct_position = all_options.index(correct_answer_text)
            except ValueError:
                # Если не нашли, ставим на первое место
                all_options[0] = correct_answer_text
                correct_position = 0
            
            # Назначаем варианты на позициях A, B, C, D
            option_a, option_b, option_c, option_d = all_options
            
            # Определяем букву правильного ответа
            correct_answer_letter = ['A', 'B', 'C', 'D'][correct_position]
            
            # Добавляем вопрос
            query = """
                INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d,
                                     correct_answer, explanation, incorrect_options, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(query, (
                topic_id,
                question.get('question'),
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer_letter,  # Сохраняем букву правильного ответа (A, B, C, D)
                question.get('explanation'),
                question.get('incorrect_options', ''),
                question.get('source', 'manual')
            ))
            
            logger.info(f"✅ Question added successfully: {correct_answer_letter}) {all_options[correct_position][:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding question: {e}")
            return False
    
    def get_all_questions(self) -> List[Dict]:
        """Get all questions (sync)"""
        logger.info("📋 Getting all questions")
        
        try:
            query = """
                SELECT q.id, q.question_text as question, 
                       CASE q.correct_answer
                           WHEN 'A' THEN q.option_a
                           WHEN 'B' THEN q.option_b
                           WHEN 'C' THEN q.option_c
                           WHEN 'D' THEN q.option_d
                           ELSE q.correct_answer
                       END as answer,
                       q.explanation, q.incorrect_options, q.source,
                       s.subtopic_name as topic, q.created_at, q.topic_id,
                       q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer as correct_letter
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
                    'answer': row['answer'],  # Текст правильного ответа
                    'explanation': row['explanation'],
                    'incorrect_options': row['incorrect_options'],
                    'source': row['source'],
                    'topic': row['topic'],
                    'topic_id': row['topic_id'],
                    'created_at': row['created_at'],
                    'option_a': row['option_a'],
                    'option_b': row['option_b'],
                    'option_c': row['option_c'],
                    'option_d': row['option_d'],
                    'correct_letter': row['correct_letter']  # Буква правильного ответа
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
                       q.explanation, q.incorrect_options, q.source,
                       s.subtopic_name as topic
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
        """Get all AI questions (sync)"""
        logger.info("📋 Getting all AI questions")
        
        try:
            query = """
                SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.correct_answer, s.subtopic_name as topic, q.source, q.created_at
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE q.source = %s
                ORDER BY q.created_at DESC
            """
            result = self.fetch_all(query, ('ai',))
            logger.info(f"📊 Found {len(result)} AI questions")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting AI questions: {e}")
            return []
    
    # Additional methods from main branch
    def get_explanation_fuzzy_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation using fuzzy matching"""
        try:
            # Try exact match first
            exact_result = self.get_explanation_by_question_text(question_text)
            if exact_result:
                return exact_result
            
            # Try fuzzy match using ILIKE
            query = """
                SELECT e.explanation_text
                FROM questions q
                LEFT JOIN explanations e ON q.id = e.question_id
                WHERE q.question_text ILIKE %s
                LIMIT 1
            """
            result = self.fetch_one(query, (f"%{question_text}%",))
            return result['explanation_text'] if result and result['explanation_text'] else None
            
        except Exception as e:
            logger.error(f"Error getting fuzzy explanation for question: {e}")
            return None
    
    def update_question(self, question_text: str, new_answer: str, new_explanation: str) -> None:
        """Update a question's answer and explanation"""
        try:
            # Update question
            query = """
                UPDATE questions 
                SET correct_answer = %s, updated_at = CURRENT_TIMESTAMP
                WHERE question_text = %s
            """
            self.execute_query(query, (new_answer, question_text))
            
            # Update explanation if exists
            if new_explanation:
                # First try to update existing explanation
                query = """
                    UPDATE explanations 
                    SET explanation_text = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE question_id = (SELECT id FROM questions WHERE question_text = %s)
                """
                self.execute_query(query, (new_explanation, question_text))
                
                # If no rows were affected, insert new explanation
                query = """
                    INSERT INTO explanations (question_id, explanation_text)
                    SELECT id, %s FROM questions WHERE question_text = %s
                    ON CONFLICT (question_id) DO UPDATE SET
                        explanation_text = EXCLUDED.explanation_text,
                        updated_at = CURRENT_TIMESTAMP
                """
                self.execute_query(query, (new_explanation, question_text))
            
            logger.info(f"✅ Updated question: {question_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error updating question: {e}")
    
    def get_tasks_for_topic_id(self, topic_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for topic by ID"""
        try:
            query = """
                SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.correct_answer, s.subtopic_name as topic, q.source, q.created_at
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE q.topic_id = %s AND s.is_active = %s
                ORDER BY RANDOM()
                LIMIT %s
            """
            result = self.fetch_all(query, (topic_id, True, limit))
            logger.info(f"📊 Found {len(result)} questions for topic_id {topic_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting tasks for topic_id {topic_id}: {e}")
            return []
    
    def add_question_with_topic_id(self, question: dict, topic_id: int) -> bool:
        """Add question with topic ID"""
        try:
            query = """
                INSERT INTO questions (question_text, option_a, option_b, option_c, option_d,
                                     correct_answer, topic_id, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(query, (
                question.get('question_text'),
                question.get('option_a'),
                question.get('option_b'),
                question.get('option_c'),
                question.get('option_d'),
                question.get('correct_answer'),
                topic_id,
                question.get('source', 'manual')
            ))
            
            logger.info(f"✅ Added question with topic_id {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding question with topic_id {topic_id}: {e}")
            return False
    
    def get_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Get topics by language"""
        try:
            query = """
                SELECT DISTINCT s.subtopic_name as topic_name, m.language
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE m.language = %s
            """
            params = [language]
            
            if active_only:
                query += " AND s.is_active = %s AND m.is_active = %s"
                params.extend([True, True])
            
            query += " ORDER BY s.subtopic_name"
            
            result = self.fetch_all(query, params)
            logger.info(f"📊 Found {len(result)} topics for language {language}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting topics by language {language}: {e}")
            return []
    
    def get_questions_by_user_language(self, user_id: int, topic: str = None) -> List[Dict]:
        """Get questions by user language"""
        try:
            # First get user's language
            user_query = "SELECT language FROM allowed_users WHERE user_id = %s"
            user_result = self.fetch_one(user_query, (user_id,))
            user_language = user_result['language'] if user_result else 'ru'
            
            # Get questions for that language
            query = """
                SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.correct_answer, s.subtopic_name as topic, q.source, q.created_at
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE m.language = %s AND s.is_active = %s AND m.is_active = %s
            """
            params = [user_language, True, True]
            
            if topic:
                query += " AND s.subtopic_name = %s"
                params.append(topic)
            
            query += " ORDER BY q.created_at DESC"
            
            result = self.fetch_all(query, params)
            logger.info(f"📊 Found {len(result)} questions for user {user_id} language {user_language}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting questions by user language for {user_id}: {e}")
            return []
    
    def get_topics_with_language_info(self, active_only: bool = True, for_admin: bool = False) -> List[Dict[str, Any]]:
        """Get topics with language info"""
        try:
            query = """
                SELECT s.id, s.subtopic_name as name, m.topic_name as main_topic,
                       m.language, s.is_active, COUNT(q.id) as question_count,
                       s.created_at, s.updated_at
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                LEFT JOIN questions q ON s.id = q.topic_id
            """
            params = []
            
            if active_only and not for_admin:
                query += " WHERE s.is_active = %s AND m.is_active = %s"
                params = [True, True]
            
            query += """
                GROUP BY s.id, s.subtopic_name, m.topic_name, m.language, s.is_active, s.created_at, s.updated_at
                ORDER BY m.language, m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, params)
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'main_topic': row['main_topic'],
                    'language': row['language'],
                    'is_active': row['is_active'],
                    'question_count': row['question_count'],
                    'has_questions': row['question_count'] > 0,
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'display_name': f"{row['main_topic']} → {row['name']} ({row['language'].upper()})"
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting topics with language info: {e}")
            return [] 