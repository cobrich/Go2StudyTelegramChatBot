import logging
from typing import List, Dict, Optional
from services.database import Database
from services.ai_service import AIService

class TopicManager:
    """Сервис для управления темами."""
    
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        
        # Базовые темы для инициализации (можно расширять)
        self.base_topics = [
            "Арифметика",
            "Алгебра", 
            "Геометрия",
            "Тригонометрия",
            "Стереометрия",
            "Комбинаторика",
            "Теория вероятностей",
            "Статистика",
            "Математический анализ",
            "Логика"
        ]
    
    def ensure_topic_exists(self, topic_name: str, description: str = None) -> str:
        """
        Убеждается, что тема существует в базе данных.
        Если темы нет - создает её.
        Возвращает нормализованное название темы.
        """
        if not topic_name or not topic_name.strip():
            return "Математика"
        
        topic_name = topic_name.strip()
        
        # Проверяем, существует ли тема
        existing_topics = self.db.get_all_topics(active_only=False)
        existing_names = [t['name'] for t in existing_topics]
        
        # Если тема уже существует
        if topic_name in existing_names:
            return topic_name
        
        # Ищем похожую тему
        similar_topic = self._find_similar_topic(topic_name, existing_names)
        if similar_topic:
            logging.info(f"Используем существующую похожую тему '{similar_topic}' для '{topic_name}'")
            return similar_topic
        
        # Нормализуем название темы с помощью AI
        normalized_name = self._normalize_topic_with_ai(topic_name)
        
        # Проверяем еще раз после нормализации
        if normalized_name in existing_names:
            return normalized_name
        
        # Создаем новую тему
        description = description or f"Тема: {normalized_name}"
        success = self.db.add_topic(normalized_name, description)
        
        if success:
            logging.info(f"Создана новая тема: '{normalized_name}'")
            return normalized_name
        else:
            logging.warning(f"Не удалось создать тему '{normalized_name}', используем 'Математика'")
            return "Математика"
    
    def _find_similar_topic(self, topic_name: str, existing_names: List[str]) -> Optional[str]:
        """Ищет похожую тему среди существующих."""
        topic_lower = topic_name.lower()
        
        # Словарь синонимов и сокращений
        synonyms = {
            'алгебра': ['алгебр', 'уравнен', 'неравенств', 'функци'],
            'геометрия': ['геометр', 'площад', 'объем', 'угол', 'треугольник'],
            'арифметика': ['арифметик', 'вычислен', 'дроб', 'процент'],
            'тригонометрия': ['тригонометр', 'синус', 'косинус', 'тангенс'],
            'стереометрия': ['стереометр', 'пространств', 'многогранник'],
            'комбинаторика': ['комбинаторик', 'размещен', 'сочетан', 'перестановк'],
            'теория вероятностей': ['вероятност', 'случайн', 'событи'],
            'статистика': ['статистик', 'данн', 'график', 'диаграмм'],
            'математический анализ': ['анализ', 'производн', 'интеграл', 'предел'],
            'логика': ['логик', 'логическ', 'рассуждени']
        }
        
        # Проверяем прямые совпадения
        for existing in existing_names:
            if topic_lower in existing.lower() or existing.lower() in topic_lower:
                return existing
        
        # Проверяем синонимы
        for base_topic, keywords in synonyms.items():
            for keyword in keywords:
                if keyword in topic_lower:
                    # Ищем соответствующую тему в базе
                    for existing in existing_names:
                        if base_topic in existing.lower():
                            return existing
        
        return None
    
    def _normalize_topic_with_ai(self, topic_name: str) -> str:
        """Нормализует название темы с помощью AI."""
        try:
            existing_topics = self.db.get_all_topics(active_only=False)
            existing_names = [t['name'] for t in existing_topics]
            
            prompt = f"""
Дана тема: "{topic_name}"

Существующие темы в системе:
{chr(10).join(existing_names)}

Базовые математические темы:
{chr(10).join(self.base_topics)}

Задача: Определи наиболее подходящее название темы из существующих или предложи новое краткое и понятное название.

Требования:
1. Название должно быть кратким (1-3 слова)
2. На русском языке
3. Отражать математическую область
4. Быть понятным для учеников

Ответь только названием темы, без дополнительных объяснений.
"""
            
            response = self.ai_service.model.generate_content(prompt)
            normalized = response.text.strip()
            
            # Проверяем, что ответ разумный
            if len(normalized) > 50 or len(normalized) < 3:
                return topic_name
            
            return normalized
            
        except Exception as e:
            logging.error(f"Ошибка при нормализации темы с AI: {e}")
            return topic_name
    
    def get_topic_by_content(self, question_text: str) -> str:
        """Определяет тему по содержанию вопроса."""
        try:
            existing_topics = self.db.get_all_topics(active_only=True)
            topic_names = [t['name'] for t in existing_topics]
            
            if not topic_names:
                return "Математика"
            
            prompt = f"""
Вопрос: "{question_text}"

Доступные темы:
{chr(10).join(topic_names)}

Определи наиболее подходящую тему для этого вопроса из списка выше.
Ответь только названием темы из списка.
"""
            
            response = self.ai_service.model.generate_content(prompt)
            suggested_topic = response.text.strip()
            
            # Проверяем, что предложенная тема есть в списке
            if suggested_topic in topic_names:
                return suggested_topic
            
            # Ищем частичное совпадение
            for topic in topic_names:
                if suggested_topic.lower() in topic.lower() or topic.lower() in suggested_topic.lower():
                    return topic
            
            # Если ничего не найдено, возвращаем первую тему или создаем новую
            return topic_names[0] if topic_names else "Математика"
            
        except Exception as e:
            logging.error(f"Ошибка при определении темы по содержанию: {e}")
            return "Математика"
    
    def merge_topics(self, source_topic: str, target_topic: str) -> bool:
        """Объединяет две темы (перемещает все вопросы из source в target)."""
        try:
            # Получаем ID тем
            topics = self.db.get_all_topics(active_only=False)
            source_id = None
            target_id = None
            
            for topic in topics:
                if topic['name'] == source_topic:
                    source_id = topic['id']
                elif topic['name'] == target_topic:
                    target_id = topic['id']
            
            if not source_id or not target_id:
                return False
            
            # Перемещаем все вопросы
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE questions SET topic = ? WHERE topic = ?',
                    (target_topic, source_topic)
                )
                
                # Деактивируем исходную тему
                cursor.execute(
                    'UPDATE topics SET is_active = 0 WHERE id = ?',
                    (source_id,)
                )
                
                conn.commit()
            
            logging.info(f"Темы объединены: '{source_topic}' -> '{target_topic}'")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при объединении тем: {e}")
            return False
    
    def get_topic_statistics(self) -> Dict[str, Dict]:
        """Возвращает статистику по темам."""
        try:
            topics = self.db.get_all_topics(active_only=False)
            stats = {}
            
            for topic in topics:
                topic_name = topic['name']
                
                # Считаем количество вопросов
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT COUNT(*) FROM questions WHERE topic = ?',
                        (topic_name,)
                    )
                    question_count = cursor.fetchone()[0]
                
                stats[topic_name] = {
                    'id': topic['id'],
                    'is_active': topic['is_active'],
                    'question_count': question_count,
                    'created_at': topic['created_at']
                }
            
            return stats
            
        except Exception as e:
            logging.error(f"Ошибка при получении статистики тем: {e}")
            return {} 