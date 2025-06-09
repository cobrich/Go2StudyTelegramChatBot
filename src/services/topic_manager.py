import logging
from typing import List, Dict, Optional
from services.database import Database
from services.ai_service import AIService

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
        
        # Если тема уже существует
        if topic_name in existing_names:
            return topic_name
        
        # Ищем похожую тему
        similar_topic = self._find_similar_topic(topic_name, existing_names)
        if similar_topic:
            logging.info(f"Используем существующую похожую тему '{similar_topic}' для '{topic_name}'")
            return similar_topic
        
        # Нормализуем название темы с помощью AI (передаем пример вопроса)
        normalized_name = self._normalize_topic_with_ai(topic_name, sample_question)
        
        # Проверяем еще раз после нормализации
        if normalized_name in existing_names:
            return normalized_name
        
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
        """Нормализует название темы с помощью AI, анализируя содержание вопросов."""
        try:
            existing_topics = self.db.get_all_topics(active_only=False)
            existing_names = [t['name'] for t in existing_topics]
            
            # Импортируем TOPIC_HIERARCHY для более точного анализа
            from config.constants import TOPIC_HIERARCHY
            
            # Создаем структурированный список тем с иерархией
            structured_topics = []
            for main_category, subtopics in TOPIC_HIERARCHY.items():
                structured_topics.append(f"\n{main_category}:")
                for i, subtopic in enumerate(subtopics, 1):
                    structured_topics.append(f"  {i}. {subtopic}")
            
            # Создаем улучшенный AI-промпт с более точными правилами
            prompt = f"""
Ты эксперт по математическому образованию для подготовки к НИШ (5-6 классы).

ЗАДАЧА: Определи ТОЧНО, к какой существующей теме относится данная тема из PDF файла.

ТЕМА ИЗ PDF: "{topic_name}"

{f'''
ПЕРВЫЙ ВОПРОС ИЗ ЭТОЙ ТЕМЫ:
"{sample_question}"
''' if sample_question else ''}

ДОСТУПНЫЕ ТЕМЫ В СИСТЕМЕ (ВЫБИРАЙ ТОЛЬКО ИЗ ЭТОГО СПИСКА):
{''.join(structured_topics)}

ПРАВИЛА АНАЛИЗА ПО СОДЕРЖАНИЮ ВОПРОСА:

🔢 АРИФМЕТИКА И ВЫЧИСЛЕНИЯ:
- Простые вычисления (2+3, 15-7, 4×6, 20÷5) → "Арифметические операции"
- Вычисления с десятичными числами (31.4 ÷ 7.9, 29.6 - 41.1) → "Натуральные числа"
- Порядок операций, скобки (2 + 3 × 4, (8 + 6) × 8) → "Порядок действий"
- Четные/нечетные числа → "Чётные и нечётные числа"
- Делимость, НОД, НОК → соответствующие темы

📊 ПРОЦЕНТЫ:
- "Найдите 25% от 80", "Найдите 15% от числа 200" → "Нахождение процента от числа"
- Общие задачи с процентами без конкретного вычисления → "Проценты"
- "Найдите число, 30% которого равно 60" → "Нахождение числа по проценту"

🔤 УРАВНЕНИЯ И ВЫРАЖЕНИЯ:
- Уравнения с переменными (3x - 7 = 17, 2(x + 3) = 24) → "Простейшие уравнения"
- Вычисление значений выражений (2x - y при x = 3) → "Арифметические выражения"
- Составление уравнений по условию → "Составление уравнений"

🍰 ДРОБИ:
- Операции с дробями (3/4 + 1/2, 1/4 × 1/5) → "Действия с дробями"
- Обыкновенные дроби (понятие, сравнение) → "Обыкновенные дроби"
- Десятичные дроби (0.5, 1.25) → "Десятичные дроби"
- Сравнение дробей → "Сравнение дробей"

📐 ГЕОМЕТРИЯ:
- Периметр и площадь фигур → "Периметр и площадь"
- Общие геометрические задачи → "Геометрические фигуры"
- Углы → "Углы"
- Координаты → "Координатная плоскость"

🔄 ПРОПОРЦИИ И ОТНОШЕНИЯ:
- "Найдите x в пропорции 2:3 = x:12" → "Простейшие уравнения" (так как это решение уравнения)
- Задачи на пропорциональность → "Арифметические выражения"

📏 ЕДИНИЦЫ ИЗМЕРЕНИЯ:
- Время (часы, минуты) → "Единицы времени"
- Длина, масса (см, м, кг) → "Единицы длины и массы"
- Перевод единиц → "Перевод единиц"

🧠 ЛОГИКА:
- Последовательности чисел → "Числовые последовательности"
- Логические головоломки → "Логические задачи"
- Поиск закономерностей → "Поиск закономерностей"

СПЕЦИАЛЬНЫЕ ПРАВИЛА СОПОСТАВЛЕНИЯ:
• "Пропорция" + вопрос с x в пропорции → "Простейшие уравнения"
• "Линейные уравнения" → "Простейшие уравнения"
• "Процентные вычисления" + "Найдите 25% от" → "Нахождение процента от числа"
• "Арифметика" + простые вычисления → "Арифметические операции"
• "Десятичные числа" → "Натуральные числа"
• "Геометрические задачи" + площадь/периметр → "Периметр и площадь"

СТРОГИЕ ПРАВИЛА:
1. ОБЯЗАТЕЛЬНО выбери тему ТОЛЬКО из списка выше
2. НЕ создавай новые темы
3. ПРИОРИТЕТ: анализируй СОДЕРЖАНИЕ первого вопроса, а не только название темы
4. Если есть пример вопроса - он главный критерий для выбора темы
5. Если сомневаешься между несколькими темами, выбери более СПЕЦИФИЧНУЮ

ПРИМЕРЫ ПРАВИЛЬНОГО СОПОСТАВЛЕНИЯ:
• "Пропорция" + "Найдите x в пропорции 2:3 = x:12" → "Простейшие уравнения"
• "Процентные вычисления" + "Найдите 25% от 80" → "Нахождение процента от числа"
• "Арифметика" + "Вычислите: 2 + 3 × 4" → "Порядок действий"
• "Линейные уравнения" + "Решите: 3x - 7 = 2x + 5" → "Простейшие уравнения"
• "Дроби" + "Вычислите: 3/4 + 1/2" → "Действия с дробями"
• "Геометрия" + "Найдите площадь прямоугольника" → "Периметр и площадь"

ОТВЕТ: Напиши ТОЛЬКО ТОЧНОЕ название темы из списка выше, без номера и дополнительных слов.
"""
            
            response = self.ai_service.model.generate_content(prompt)
            normalized = response.text.strip()
            
            # Убираем возможные префиксы, номера и лишние символы
            normalized = normalized.replace("•", "").replace("-", "").strip()
            # Убираем номера в начале (если AI добавил)
            import re
            normalized = re.sub(r'^\d+\.\s*', '', normalized)
            
            # Проверяем, что ответ разумный
            if len(normalized) > 50 or len(normalized) < 3:
                logging.warning(f"AI вернул неподходящий ответ: '{normalized}', используем исходное название")
                return topic_name
            
            # Проверяем точное совпадение с существующими темами
            for existing in existing_names:
                if normalized.lower() == existing.lower():
                    logging.info(f"AI сопоставил '{topic_name}' с существующей темой '{existing}'")
                    return existing
            
            # Проверяем частичное совпадение
            for existing in existing_names:
                if normalized.lower() in existing.lower() or existing.lower() in normalized.lower():
                    logging.info(f"AI сопоставил '{topic_name}' с похожей темой '{existing}' (частичное совпадение)")
                    return existing
            
            # Если AI предложил что-то не из списка, ищем наиболее похожую тему
            best_match = None
            max_similarity = 0
            
            for existing in existing_names:
                # Простая мера схожести по общим словам
                normalized_words = set(normalized.lower().split())
                existing_words = set(existing.lower().split())
                common_words = normalized_words.intersection(existing_words)
                similarity = len(common_words) / max(len(normalized_words), len(existing_words))
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = existing
            
            if best_match and max_similarity > 0.3:
                logging.info(f"AI предложил '{normalized}', найдено похожее: '{best_match}' (схожесть: {max_similarity:.2f})")
                return best_match
            
            # Если ничего не найдено, возвращаем первую тему из списка
            if existing_names:
                logging.warning(f"AI предложил '{normalized}', но это не из списка. Используем первую тему: '{existing_names[0]}'")
                return existing_names[0]
            
            return topic_name
            
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