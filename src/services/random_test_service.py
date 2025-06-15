"""
Сервис для генерации случайных тестов из 10 вопросов.
Поддерживает фильтрацию по языку пользователя и равномерное распределение вопросов по темам.
"""

import random
from typing import List, Dict, Any, Optional
from .database import Database
import logging

logger = logging.getLogger(__name__)

class RandomTestService:
    def __init__(self, db: Database):
        self.db = db
    
    def generate_random_test(self, user_id: int, question_count: int = 10) -> List[Dict[str, Any]]:
        """
        Генерирует случайный тест из указанного количества вопросов.
        Вопросы равномерно распределяются по доступным темам на языке пользователя.
        
        Args:
            user_id: ID пользователя
            question_count: Количество вопросов в тесте (по умолчанию 10)
            
        Returns:
            Список вопросов для теста
        """
        try:
            # Получаем язык пользователя
            user_language = self.db.get_user_language(user_id)
            
            # Получаем все доступные темы на языке пользователя
            available_topics = self.db.get_topics_by_language(user_language, active_only=True)
            
            if not available_topics:
                logger.warning(f"No topics available for user {user_id} with language {user_language}")
                return []
            
            # Получаем все вопросы на языке пользователя
            all_questions = self.db.get_questions_by_user_language(user_id)
            
            if not all_questions:
                logger.warning(f"No questions available for user {user_id} with language {user_language}")
                return []
            
            # Группируем вопросы по темам
            questions_by_topic = {}
            for question in all_questions:
                topic = question['topic']
                if topic not in questions_by_topic:
                    questions_by_topic[topic] = []
                questions_by_topic[topic].append(question)
            
            # Генерируем сбалансированный тест
            selected_questions = self._get_balanced_questions_from_topics(
                questions_by_topic, question_count
            )
            
            # Перемешиваем вопросы для случайного порядка
            random.shuffle(selected_questions)
            
            logger.info(f"Generated random test for user {user_id}: {len(selected_questions)} questions from {len(questions_by_topic)} topics")
            
            return selected_questions
            
        except Exception as e:
            logger.error(f"Error generating random test for user {user_id}: {e}")
            return []
    
    def generate_retry_test(self, user_id: int, question_count: int = 10) -> List[Dict[str, Any]]:
        """
        Генерирует тест на основе ошибок пользователя.
        Если ошибок недостаточно, добавляет случайные вопросы.
        
        Args:
            user_id: ID пользователя
            question_count: Количество вопросов в тесте
            
        Returns:
            Список вопросов для теста
        """
        try:
            # Получаем темы с ошибками
            error_topics = self.db.get_error_topics(user_id)
            
            if not error_topics:
                # Если нет ошибок, генерируем обычный случайный тест
                return self.generate_random_test(user_id, question_count)
            
            # Получаем вопросы по проблемным темам
            retry_questions = []
            for topic_name, error_count in error_topics:
                topic_questions = self.db.get_error_tasks_for_user(user_id, topic_name, limit=10)
                retry_questions.extend(topic_questions)
            
            # Если вопросов с ошибками недостаточно, добавляем случайные
            if len(retry_questions) < question_count:
                additional_needed = question_count - len(retry_questions)
                random_questions = self.generate_random_test(user_id, additional_needed)
                
                # Убираем дубликаты
                existing_ids = {q['id'] for q in retry_questions if 'id' in q}
                for q in random_questions:
                    if q.get('id') not in existing_ids:
                        retry_questions.append(q)
                        if len(retry_questions) >= question_count:
                            break
            
            # Ограничиваем количество вопросов
            retry_questions = retry_questions[:question_count]
            
            # Перемешиваем
            random.shuffle(retry_questions)
            
            logger.info(f"Generated retry test for user {user_id}: {len(retry_questions)} questions")
            
            return retry_questions
            
        except Exception as e:
            logger.error(f"Error generating retry test for user {user_id}: {e}")
            return self.generate_random_test(user_id, question_count)
    
    def _get_balanced_questions_from_topics(self, questions_by_topic: Dict[str, List[Dict]], 
                                          total_count: int) -> List[Dict[str, Any]]:
        """
        Равномерно распределяет вопросы по темам, но если вопросов недостаточно,
        добирает из доступных тем.
        
        Args:
            questions_by_topic: Словарь {тема: [вопросы]}
            total_count: Общее количество вопросов
            
        Returns:
            Список выбранных вопросов
        """
        if not questions_by_topic:
            return []
        
        # Фильтруем темы, в которых есть вопросы
        topics_with_questions = {topic: questions for topic, questions in questions_by_topic.items() 
                               if questions}
        
        if not topics_with_questions:
            return []
        
        topics = list(topics_with_questions.keys())
        selected_questions = []
        
        # Если тем мало, используем простую стратегию
        if len(topics) <= 3:
            # Берем вопросы из всех доступных тем пропорционально
            all_available_questions = []
            for questions in topics_with_questions.values():
                all_available_questions.extend(questions)
            
            # Если доступных вопросов меньше чем нужно, берем все
            if len(all_available_questions) <= total_count:
                return all_available_questions
            else:
                # Выбираем случайные вопросы
                return random.sample(all_available_questions, total_count)
        
        # Для большого количества тем используем сбалансированное распределение
        # Базовое количество вопросов на тему
        base_per_topic = total_count // len(topics)
        remainder = total_count % len(topics)
        
        # Первый проход - берем базовое количество из каждой темы
        for i, topic in enumerate(topics):
            topic_questions = topics_with_questions[topic]
            
            # Количество вопросов для этой темы
            questions_for_topic = base_per_topic
            if i < remainder:  # Распределяем остаток
                questions_for_topic += 1
            
            # Выбираем случайные вопросы из темы
            if len(topic_questions) <= questions_for_topic:
                # Если вопросов в теме меньше чем нужно, берем все
                selected_questions.extend(topic_questions)
            else:
                # Выбираем случайные вопросы
                selected = random.sample(topic_questions, questions_for_topic)
                selected_questions.extend(selected)
        
        # Если не набрали нужное количество, добираем из оставшихся вопросов
        if len(selected_questions) < total_count:
            # Собираем все неиспользованные вопросы
            used_question_ids = {q.get('id') for q in selected_questions if q.get('id')}
            remaining_questions = []
            
            for questions in topics_with_questions.values():
                for q in questions:
                    if q.get('id') not in used_question_ids:
                        remaining_questions.append(q)
            
            # Добираем недостающие вопросы
            needed = total_count - len(selected_questions)
            if remaining_questions:
                if len(remaining_questions) <= needed:
                    selected_questions.extend(remaining_questions)
                else:
                    additional = random.sample(remaining_questions, needed)
                    selected_questions.extend(additional)
        
        return selected_questions[:total_count]  # Гарантируем точное количество
    
    def get_test_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику тестов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        try:
            # Получаем общую статистику
            total_tests, avg_score = self.db.get_user_progress(user_id)
            
            # Получаем результаты тестов
            test_results = self.db.get_user_test_results(user_id)
            
            # Получаем темы с ошибками
            error_topics = self.db.get_error_topics(user_id)
            
            return {
                'total_tests': total_tests,
                'average_score': avg_score,
                'recent_results': test_results[-10:] if test_results else [],  # Последние 10 результатов
                'error_topics': error_topics[:5] if error_topics else [],  # Топ-5 проблемных тем
                'total_errors': sum(count for _, count in error_topics) if error_topics else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting test statistics for user {user_id}: {e}")
            return {
                'total_tests': 0,
                'average_score': 0.0,
                'recent_results': [],
                'error_topics': [],
                'total_errors': 0
            }
    
    def save_random_test_result(self, user_id: int, score_percentage: float, 
                               questions_data: List[Dict]) -> None:
        """
        Сохраняет результат случайного теста.
        
        Args:
            user_id: ID пользователя
            score_percentage: Процент правильных ответов
            questions_data: Данные о вопросах и ответах
        """
        try:
            # Получаем язык пользователя для правильного названия теста
            user_language = self.db.get_user_language(user_id)
            random_test_topic_name = "Случайный тест" if user_language == 'ru' else "Кездейсоқ тест"
            
            # Сохраняем общий результат теста
            self.db.add_test_result(user_id, random_test_topic_name, score_percentage)
            
            # Сохраняем ошибки по темам
            for question_data in questions_data:
                if not question_data.get('is_correct', True):  # Если ответ неправильный
                    self.db.add_user_error(
                        user_id=user_id,
                        topic=question_data.get('topic', 'Неизвестная тема'),
                        question_text=question_data.get('question_text', ''),
                        user_answer_text=question_data.get('user_answer', ''),
                        correct_answer_text=question_data.get('correct_answer', ''),
                        explanation_text=question_data.get('explanation', '')
                    )
            
            logger.info(f"Saved random test result for user {user_id}: {score_percentage}%")
            
        except Exception as e:
            logger.error(f"Error saving random test result for user {user_id}: {e}") 