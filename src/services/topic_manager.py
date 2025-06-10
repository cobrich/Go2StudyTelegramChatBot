import logging
import sqlite3
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from services.database import Database
from services.ai_service import AIService
from config.constants import TOPIC_HIERARCHY

logger = logging.getLogger(__name__)

class TopicManager:
    """Сервис для управления темами."""
    
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        
        # Базовые темы для подготовки к НИШ (5-6 классы)
        self.base_topics = [
            # Арифметика и числа
            "Натуральные числа",
            "Чётные и нечётные числа", 
            "Делимость чисел",
            "Простые и составные числа",
            "НОК и НОД",
            "Сравнение и округление чисел",
            
            # Операции с числами
            "Арифметические операции",
            "Порядок действий",
            "Деление с остатком",
            "Свойства операций",
            
            # Дроби
            "Обыкновенные дроби",
            "Десятичные дроби",
            "Сравнение дробей",
            "Действия с дробями",
            
            # Проценты
            "Проценты",
            "Нахождение процента от числа",
            "Нахождение числа по проценту",
            
            # Уравнения и выражения
            "Простейшие уравнения",
            "Арифметические выражения",
            "Составление уравнений",
            
            # Логика и закономерности
            "Числовые последовательности",
            "Логические задачи",
            "Поиск закономерностей",
            
            # Геометрия
            "Геометрические фигуры",
            "Периметр и площадь",
            "Углы",
            "Координатная плоскость",
            
            # Единицы измерения
            "Единицы времени",
            "Единицы длины и массы",
            "Перевод единиц",
            
            # Работа с данными
            "Таблицы и диаграммы",
            "Анализ графиков",
            
            # Практические задачи
            "Задачи на практическое мышление",
            "Оптимизация",
            "Распределение по условиям"
        ]
    
    def ensure_topic_exists(self, topic_name: str, description: str = None, sample_question: str = None) -> str:
        """
        Убеждается, что тема существует в базе данных.
        Если темы нет - создает её.
        Возвращает нормализованное название темы.
        
        Args:
            topic_name: Название темы из PDF
            description: Описание темы (опционально)
            sample_question: Пример вопроса из этой темы для лучшего анализа
        """
        if not topic_name or not topic_name.strip():
            return "Математика"
        
        topic_name = topic_name.strip()
        
        # Проверяем, существует ли тема
        existing_topics = self.db.get_all_topics(active_only=False)
        existing_names = [t['name'] for t in existing_topics]
        
        # Если тема уже существует точно
        if topic_name in existing_names:
            return topic_name
        
        # СНАЧАЛА нормализуем название темы с помощью AI (анализируем вопрос)
        normalized_name = self._normalize_topic_with_ai(topic_name, sample_question)
        
        # Проверяем, существует ли нормализованная тема
        if normalized_name in existing_names:
            return normalized_name
        
        # Только ПОСЛЕ ИИ анализа ищем похожую тему для нормализованного названия
        similar_topic = self._find_similar_topic(normalized_name, existing_names)
        if similar_topic:
            logging.info(f"Используем существующую похожую тему '{similar_topic}' для нормализованной '{normalized_name}'")
            return similar_topic
        
        # Создаем новую тему только если AI действительно предложил уникальное название
        description = description or f"Тема: {normalized_name}"
        success = self.db.add_topic(normalized_name, description)
        
        if success:
            logging.info(f"Создана новая тема: '{normalized_name}' (исходное название: '{topic_name}')")
            return normalized_name
        else:
            logging.warning(f"Не удалось создать тему '{normalized_name}', используем 'Математика'")
            return "Математика"
    
    def _find_similar_topic(self, topic_name: str, existing_names: List[str]) -> Optional[str]:
        """Ищет похожую тему среди существующих."""
        topic_lower = topic_name.lower()
        
        # Словарь синонимов и сокращений для тем НИШ
        synonyms = {
            'натуральные числа': ['натуральн', 'числ', 'цифр'],
            'чётные и нечётные числа': ['чётн', 'нечётн', 'парн', 'непарн'],
            'делимость чисел': ['делимост', 'делител', 'кратн', 'остаток'],
            'простые и составные числа': ['прост', 'составн', 'разложен'],
            'нок и нод': ['нок', 'нод', 'общий кратн', 'общий делител'],
            'сравнение и округление чисел': ['сравнен', 'округлен', 'больш', 'меньш'],
            
            'арифметические операции': ['арифметик', 'сложен', 'вычитан', 'умножен', 'делен'],
            'порядок действий': ['порядок', 'скобк', 'приоритет'],
            'деление с остатком': ['остаток', 'нацело'],
            'свойства операций': ['свойств', 'переместительн', 'сочетательн', 'распределительн'],
            
            'обыкновенные дроби': ['обыкновенн', 'дроб', 'числител', 'знаменател'],
            'десятичные дроби': ['десятичн', 'запят'],
            'сравнение дробей': ['сравнен дроб'],
            'действия с дробями': ['действи', 'операци', 'дроб'],
            
            'проценты': ['процент', '%'],
            'нахождение процента от числа': ['процент от числ', 'найти процент'],
            'нахождение числа по проценту': ['числ по процент', 'обратн'],
            
            'простейшие уравнения': ['уравнен', 'неизвестн', 'x', 'y'],
            'арифметические выражения': ['выражен', 'вычислен'],
            'составление уравнений': ['составлен', 'задач'],
            
            'числовые последовательности': ['последовательност', 'ряд', 'прогресси'],
            'логические задачи': ['логик', 'логическ', 'рассуждени'],
            'поиск закономерностей': ['закономерност', 'правил', 'паттерн'],
            
            'геометрические фигуры': ['геометр', 'фигур', 'треугольник', 'квадрат', 'прямоугольник', 'круг'],
            'периметр и площадь': ['периметр', 'площад'],
            'углы': ['угол', 'градус'],
            'координатная плоскость': ['координат', 'плоскост', 'ось'],
            
            'единицы времени': ['врем', 'час', 'минут', 'секунд'],
            'единицы длины и массы': ['длин', 'масс', 'метр', 'килограмм', 'грамм'],
            'перевод единиц': ['перевод', 'единиц', 'измерен'],
            
            'таблицы и диаграммы': ['таблиц', 'диаграмм', 'данн'],
            'анализ графиков': ['график', 'анализ'],
            
            'задачи на практическое мышление': ['практическ', 'реальн', 'жизненн'],
            'оптимизация': ['оптимизаци', 'минимальн', 'максимальн'],
            'распределение по условиям': ['распределен', 'групп', 'условия']
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
    
    def _normalize_topic_with_ai(self, topic_name: str, sample_question: str = None) -> str:
        """
        Использует ИИ для определения правильной темы на основе содержания вопроса
        """
        try:
            # Создаем структурированный список тем для ИИ
            topic_list = []
            for category, topics in TOPIC_HIERARCHY.items():
                for topic in topics:
                    topic_list.append(f"- {topic}")
            
            topics_text = "\n".join(topic_list)
            
            prompt = f"""Ты эксперт по математике для учеников 5-6 классов. Определи наиболее подходящую тему для математического вопроса.

ДОСТУПНЫЕ ТЕМЫ:
{topics_text}

ЗАГОЛОВОК ТЕМЫ ИЗ PDF: "{topic_name}"
ПЕРВЫЙ ВОПРОС ТЕМЫ: "{sample_question or 'Не предоставлен'}"

ЗАДАЧА:
Определи одну конкретную тему из списка, учитывая ЗАГОЛОВОК и ПЕРВЫЙ ВОПРОС.

ПРАВИЛА АНАЛИЗА:

1. 📋 ЕСЛИ ЗАГОЛОВОК СОДЕРЖИТ ОДНУ ТЕМУ:
   Примеры: "Операции с дробями", "Площади и периметры", "Простые уравнения"
   → Выбери соответствующую тему из списка

2. 🔀 ЕСЛИ ЗАГОЛОВОК СОДЕРЖИТ НЕСКОЛЬКО ТЕМ:
   Примеры: "Дроби, проценты, уравнения", "Арифметика - разные темы"
   → Анализируй ПЕРВЫЙ ВОПРОС и выбери наиболее подходящую тему
   → ВСЕ вопросы этой темы будут иметь одинаковую классификацию

3. 🎯 ПРИОРИТЕТ АНАЛИЗА:
   - Сначала смотри на ЗАГОЛОВОК (что обещает тема)
   - Затем анализируй ПЕРВЫЙ ВОПРОС (что реально содержится)
   - Выбери наиболее точную тему из списка

КЛЮЧЕВЫЕ ПРИЗНАКИ:

🔢 ЧИСЛА И ОПЕРАЦИИ:
• Натуральные числа: работа с целыми положительными числами
• Арифметические операции: сложение, вычитание, умножение, деление
• Порядок действий: выражения со скобками

🔤 ДРОБИ:
• Десятичные дроби: числа с запятой (2,46; 0,253)
• Обыкновенные дроби: дроби вида a/b (1/2, 3/4)
• Действия с дробями: операции с любыми дробями

📊 ПРОЦЕНТЫ:
• Проценты: символ % или слова "процент"
• Нахождение процента от числа: "найти X% от Y"
• Нахождение числа по проценту: "число составляет X%"

🔍 УРАВНЕНИЯ:
• Простейшие уравнения: переменная (x, y) и знак равенства

📐 ГЕОМЕТРИЯ:
• Периметр и площадь: вычисление площади/периметра фигур
• Углы: измерение углов, виды углов
• Геометрические фигуры: свойства фигур

📏 ИЗМЕРЕНИЯ:
• Перевод единиц: масштаб, преобразование единиц
• Единицы длины и массы: метры, килограммы
• Единицы времени: часы, минуты

🎯 СПЕЦИАЛЬНЫЕ:
• Числовые последовательности: поиск закономерностей
• Логические задачи: рассуждения без вычислений

ПРИМЕРЫ ПРАВИЛЬНОГО АНАЛИЗА:

Заголовок: "Операции с дробями"
Вопрос: "Вычислите: 2/3 + 1/4"
→ Тема: "Действия с дробями"

Заголовок: "Дроби, проценты, уравнения"  
Вопрос: "Решите уравнение: x + 5 = 12"
→ Тема: "Простейшие уравнения" (по первому вопросу)

Заголовок: "Площади и периметры"
Вопрос: "Найдите площадь квадрата"
→ Тема: "Периметр и площадь"

ВАЖНО: Все вопросы данной темы получат одинаковую классификацию!

Проанализируй заголовок и первый вопрос, верни ТОЛЬКО название темы из списка."""

            response = self.ai_service.model.generate_content(prompt)
            normalized_topic = response.text.strip()
            
            # Убираем возможные кавычки или лишние символы
            normalized_topic = normalized_topic.strip('"\'')
            
            # Проверяем, что ответ содержится в списке доступных тем
            all_topics = []
            for topics in TOPIC_HIERARCHY.values():
                all_topics.extend(topics)
            
            if normalized_topic in all_topics:
                logger.info(f"AI нормализация: '{topic_name}' → '{normalized_topic}' (заголовок + первый вопрос)")
                return normalized_topic
            else:
                # Ищем частичное совпадение
                for topic in all_topics:
                    if normalized_topic.lower() in topic.lower() or topic.lower() in normalized_topic.lower():
                        logger.info(f"AI нормализация (частичное): '{topic_name}' → '{topic}' (предложено: {normalized_topic})")
                        return topic
                
                logger.warning(f"AI вернул неизвестную тему: {normalized_topic}, используем поиск похожей")
                return self._find_similar_topic(topic_name, all_topics) or topic_name
                
        except Exception as e:
            logger.error(f"Ошибка AI нормализации: {e}")
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