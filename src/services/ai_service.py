import logging
import google.generativeai as genai
from typing import Optional, Tuple, List
import re
from config.constants import GEMINI_API_KEY, GEMINI_MODEL, MAX_OPTION_LENGTH
import json

class AIService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate_task(self, topic: str, main_topic: str = None) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """Generate a single task for the given topic."""
        # Формируем контекст темы
        if main_topic:
            # Убираем эмодзи из основной темы для чистоты
            clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
            topic_context = f"Тема '{topic}' из раздела '{clean_main_topic}'"
            specific_requirements = self._get_topic_specific_requirements(topic, clean_main_topic)
        else:
            topic_context = f"Тема '{topic}'"
            specific_requirements = ""
        
        prompt_template = (
            "Твоя задача - быть экспертом по созданию обучающих математических задач для учеников 5-6 классов.\n"
            f"Тебе нужно сгенерировать ОДИН уникальный и интересный вопрос по теме: {topic_context}.\n"
            f"{specific_requirements}\n"
            "Вопрос должен быть не просто на вычисление, а, по возможности, представлять собой небольшую текстовую задачу, логическую головоломку или задачу на применение математических концепций в жизненной ситуации, соответствующей теме. Избегай создания однотипных вопросов, отличающихся только числами.\n\n"
            "ТРЕБОВАНИЯ К ЗАДАЧЕ:\n"
            "1.  **Целевая аудитория:** Ученики 5-6 класса.\n"
            f"2.  **Тема:** {topic_context}.\n"
            "3.  **Сложность:** Вопрос должен быть решаем в уме или с минимальными записями, обычно не более 2-3 логических шагов или математических операций. Он должен быть достаточно сложным, чтобы требовать размышлений, но не чрезмерно трудным.\n"
            "4.  **Уникальность:** Вопрос должен быть новым, не повторяющим предыдущие.\n"
            "5.  **Контекст и единицы:** Если в вопросе используются единицы измерения, ответ также должен быть в этих единицах. Все числовые значения и условия должны быть реалистичными и соответствовать теме.\n"
            "6.  **Правильный ответ:** Должен быть четким, однозначным и не превышать 60 символов.\n"
            "7.  **Неправильные ответы (3 шт.):** Должны быть правдоподобными, отражать типичные ошибки или заблуждения учеников по данной теме. Они не должны быть очевидно неверными.\n"
            "8.  **Объяснение:** Должно быть кратким, ясным, пошаговым (если применимо) и помогать понять логику решения и концепцию.\n\n"
            "СТРОГИЙ ФОРМАТ ВЫВОДА (КАЖДЫЙ ПУНКТ С НОВОЙ СТРОКИ, ЗАГОЛОВКИ ЗАГЛАВНЫМИ БУКВАМИ):\n"
            "ВОПРОС: [текст вопроса]\n"
            "ПРАВИЛЬНЫЙ ОТВЕТ: [текст правильного ответа]\n"
            "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [текст первого неправильного варианта]\n"
            "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [текст второго неправильного варианта]\n"
            "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [текст третьего неправильного варианта]\n"
            "ОБЪЯСНЕНИЕ: [текст объяснения правильного ответа]\n"
        )
        
        try:
            response_text = self.model.generate_content(prompt_template).text
            
            # Parse response
            q_match = re.search(r"ВОПРОС:\s*(.*?)\s*ПРАВИЛЬНЫЙ ОТВЕТ:", response_text, re.DOTALL | re.IGNORECASE)
            correct_a_match = re.search(r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|\s*ОБЪЯСНЕНИЕ:)", response_text, re.DOTALL | re.IGNORECASE)
            
            question = q_match.group(1).strip() if q_match else None
            correct_answer = self._clean_option_text(correct_a_match.group(1).strip()) if correct_a_match else None
            
            incorrect_options = []
            search_start_index = 0
            if correct_a_match:
                first_incorrect_or_expl_match = re.search(r"НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:", response_text[correct_a_match.end():], re.IGNORECASE)
                if first_incorrect_or_expl_match:
                    search_start_index = correct_a_match.end() + first_incorrect_or_expl_match.start()
            
            for match in re.finditer(r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|\s*ОБЪЯСНЕНИЕ:|$)", 
                                   response_text[search_start_index:], re.DOTALL | re.IGNORECASE):
                option_text = match.group(1).strip()
                if option_text:
                    cleaned = self._clean_option_text(option_text)
                    if len(cleaned) <= MAX_OPTION_LENGTH:
                        incorrect_options.append(cleaned)
            
            e_match = re.search(r"ОБЪЯСНЕНИЕ:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
            explanation = e_match.group(1).strip() if e_match else None
            
            # Validate response
            if not (question and correct_answer and explanation and len(incorrect_options) >= 1):
                return None, None, None, None
            
            if len(correct_answer) > MAX_OPTION_LENGTH:
                return None, None, None, None
            
            return question, correct_answer, incorrect_options, explanation
            
        except Exception as err:
            logging.error(f"Error generating AI task: {err}")
            return None, None, None, None

    @staticmethod
    def _clean_option_text(text: str) -> str:
        """Clean option text by removing unnecessary words and extra spaces."""
        # Remove words like "ANSWER", "CORRECT", "INCORRECT", etc.
        text = re.sub(r'(ОТВЕТ|ПРАВИЛЬНЫЙ|НЕПРАВИЛЬНЫЙ|ВЕРНО|НЕВЕРНО|НЕВОЗМОЖНО ОПРЕДЕЛИТЬ|НЕВОЗМОЖНО СКАЗАТЬ|НЕ МОГУ ОПРЕДЕЛИТЬ|НЕ МОГУ СКАЗАТЬ|НЕ УВЕРЕН|НЕ ЗНАЮ|ЗАТРУДНЯЮСЬ ОТВЕТИТЬ|СЛОЖНО СКАЗАТЬ|НУЖНО ПОДУМАТЬ|ПРОВЕРЮ ЕЩЕ РАЗ|ДРУГОЙ ВАРИАНТ|ЭТО НЕВЕРНО|НЕПРАВИЛЬНЫЙ ВАРИАНТ|ПРАВИЛЬНЫЙ ВАРИАНТ|ВЕРНЫЙ ОТВЕТ|НЕВЕРНЫЙ ОТВЕТ|\\s*\\(.*?\\))', '', text, flags=re.IGNORECASE)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove leading and trailing spaces
        return text.strip() 

    def _get_topic_specific_requirements(self, topic: str, main_topic: str) -> str:
        """Получить специфические требования для темы на основе раздела."""
        topic_lower = topic.lower()
        main_topic_lower = main_topic.lower()
        
        # Специфические требования для разных разделов
        if "единиц" in main_topic_lower or "измерения" in main_topic_lower:
            if "перевод" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть СТРОГО о переводе одних единиц измерения в другие. "
                    "Например: перевод метров в сантиметры, килограммов в граммы, часов в минуты и т.д. "
                    "НЕ создавай задачи на скорость, время в пути, дроби или другие темы!"
                )
            elif "время" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть о единицах времени: секунды, минуты, часы, дни, недели, месяцы, годы. "
                    "Например: сколько минут в 2 часах 30 минутах, сколько дней в 3 неделях и т.д."
                )
            elif "длин" in topic_lower or "масс" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть о единицах длины (мм, см, м, км) или массы (г, кг, т). "
                    "Например: сколько сантиметров в 2 метрах 50 сантиметрах."
                )
            elif "масштаб" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть о масштабе карт, планов или моделей. "
                    "Например: если масштаб карты 1:1000, то сколько метров на местности соответствует 5 см на карте."
                )
        
        elif "дроб" in main_topic_lower:
            if "обыкновенн" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть СТРОГО об обыкновенных дробях (1/2, 3/4, 2/5 и т.д.). "
                    "Операции: сложение, вычитание, умножение, деление обыкновенных дробей. "
                    "НЕ используй десятичные дроби или проценты!"
                )
            elif "десятичн" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть СТРОГО о десятичных дробях (0.5, 1.25, 3.14 и т.д.). "
                    "Операции: сложение, вычитание, умножение, деление десятичных дробей. "
                    "НЕ используй обыкновенные дроби!"
                )
            elif "смешанн" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть о смешанных числах (1½, 2¾, 3⅖ и т.д.). "
                    "Перевод между смешанными числами и неправильными дробями."
                )
        
        elif "процент" in main_topic_lower:
            return (
                "ВАЖНО: Вопрос должен быть СТРОГО о процентах. "
                "Например: найти процент от числа, найти число по его проценту, найти процентное отношение. "
                "НЕ создавай задачи на дроби без процентов!"
            )
        
        elif "геометр" in main_topic_lower:
            if "периметр" in topic_lower or "площад" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть о вычислении периметра или площади геометрических фигур. "
                    "Фигуры: прямоугольник, квадрат, треугольник, круг. "
                    "Используй простые целые числа для размеров."
                )
            elif "угл" in topic_lower:
                return (
                    "ВАЖНО: Вопрос должен быть об углах: острые, тупые, прямые, развернутые. "
                    "Измерение углов, сумма углов треугольника, смежные углы."
                )
        
        elif "уравнен" in main_topic_lower or "алгебр" in main_topic_lower:
            return (
                "ВАЖНО: Вопрос должен быть о решении простых уравнений с одной переменной. "
                "Например: x + 5 = 12, 3x = 15, x - 7 = 10. "
                "Используй простые числа, решение должно быть целым числом."
            )
        
        return ""

    def normalize_question_via_gemini(self, raw_text: str) -> Optional[dict]:
        """
        Отправляет сырой текст вопроса в Gemini и возвращает структурированный результат (dict) с полями:
        question, options, answer, explanation
        """
        prompt = (
            "Ты — эксперт по математике и педагогике. Тебе дан текст вопроса, извлечённый из PDF, который может содержать ошибки, мусорные символы, обрывки формул или некорректные обозначения (например, вместо x — !, вместо знаков — непонятные символы).\n"
            "\n"
            "Твоя задача:\n"
            "1. Если вопрос нечитабелен, не содержит смысла, не содержит переменных или чисел, или не может быть понят школьнику — верни пустой JSON: {}\n"
            "2. Если вопрос можно восстановить (например, заменить ! на x, убрать мусор, восстановить формулу), сделай это и сформулируй вопрос так, чтобы он был полностью понятен ученику 5-6 класса.\n"
            "3. Сформируй 4 варианта ответа (A, B, C, D), где только один правильный, остальные — типичные ошибки или правдоподобные варианты.\n"
            "4. Укажи правильный вариант (буква).\n"
            "5. Дай краткое, пошаговое объяснение решения.\n"
            "6. Все числа и переменные должны быть реальными, без мусора.\n"
            "7. Не используй технические фразы типа 'невозможно определить', 'не могу сказать' и т.п.\n"
            "\n"
            "Верни результат в формате JSON строго такого вида:\n"
            "{\n  \"question\": \"Чистый, понятный текст вопроса\",\n  \"options\": [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\"],\n  \"answer\": \"B\",\n  \"explanation\": \"Краткое объяснение\"\n}\n"
            "\nТекст вопроса:\n" + raw_text
        )
        try:
            response = self.model.generate_content(prompt).text
            # Попробуем найти JSON в ответе
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if not match:
                return None
            json_str = match.group(0)
            # Заменим одинарные кавычки на двойные для парсинга
            json_str = json_str.replace("'", '"')
            data = json.loads(json_str)
            # Проверим наличие всех ключей
            if not all(k in data for k in ("question", "options", "answer", "explanation")):
                return None
            return data
        except Exception as e:
            logging.error(f"Gemini normalization error: {e}")
            return None 

    def generate_similar_task(self, topic: str, similar_to_question: str, main_topic: str = None) -> Optional[tuple]:
        """Generate a question similar to the given question."""
        try:
            # Формируем контекст темы
            if main_topic:
                clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
                topic_context = f"Тема '{topic}' из раздела '{clean_main_topic}'"
                specific_requirements = self._get_topic_specific_requirements(topic, clean_main_topic)
            else:
                topic_context = f"Тема '{topic}'"
                specific_requirements = ""
            
            prompt = f"""Сгенерируй вопрос по теме '{topic_context}', который похож на следующий вопрос, но с другими числами/переменными:
            {similar_to_question}
            
            {specific_requirements}
            
            В ответе должен быть JSON в формате:
            {{
                "question": "текст вопроса",
                "correct_answer": "правильный ответ",
                "incorrect_options": ["вариант1", "вариант2", "вариант3"],
                "explanation": "объяснение решения"
            }}
            
            Вопрос должен быть:
            1. По той же теме и того же типа
            2. С похожей структурой и сложностью
            3. С другими числами/переменными
            4. С понятным объяснением решения
            5. Строго соответствовать указанной теме и разделу
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            data = json.loads(json_str)
            
            return (
                data['question'],
                data['correct_answer'],
                data['incorrect_options'],
                data['explanation']
            )
        except Exception as e:
            logging.error(f"Error generating similar task: {e}")
            return None 

    def validate_question_answer(self, question: str, answer: str, explanation: str) -> Optional[tuple]:
        """Validate a question's answer and explanation using AI."""
        try:
            prompt = f"""Проверь правильность ответа на следующий вопрос:
            Вопрос: {question}
            Ответ: {answer}
            Объяснение: {explanation}
            
            Верни результат в формате JSON:
            {{
                "is_correct": true/false,
                "correct_answer": "правильный ответ",
                "explanation": "правильное объяснение"
            }}
            
            Если ответ верный, верни тот же ответ и объяснение.
            Если ответ неверный, укажи правильный ответ и объяснение.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            data = json.loads(json_str)
            
            if data['is_correct']:
                return None  # No changes needed
            else:
                return (data['correct_answer'], data['explanation'])
                
        except Exception as e:
            logging.error(f"Error validating question: {e}")
            return None 

    def generate_detailed_explanation(self, question: str, correct_answer: str, topic: str) -> str:
        """Генерирует подробное объяснение решения математической задачи."""
        try:
            prompt = f"""Ты - опытный учитель математики для учеников 5-6 классов. 
            Тебе нужно объяснить решение задачи простым и понятным языком.

            Тема: {topic}
            Вопрос: {question}
            Правильный ответ: {correct_answer}

            Создай подробное объяснение, которое поможет ученику понять:
            1. Что дано в задаче
            2. Что нужно найти
            3. Какие формулы или правила использовать
            4. Пошаговое решение
            5. Почему именно такой ответ

            Требования к объяснению:
            - Используй простой язык, понятный ученику 5-6 класса
            - Покажи все шаги решения
            - Объясни логику каждого шага
            - Если есть формулы, объясни их применение
            - Длина объяснения: 3-5 предложений
            - Избегай сложных математических терминов

            Пример хорошего объяснения:
            "Сначала найдем общий знаменатель для дробей 2/7 и 3/5. Затем вычислим, сколько теста использовали утром и вечером. После этого определим, какая часть осталась, и найдем изначальное количество."

            Объяснение:"""
            
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            # Очищаем объяснение от лишних фраз
            explanation = re.sub(r'^(Объяснение:|Решение:)\s*', '', explanation, flags=re.IGNORECASE)
            explanation = explanation.strip()
            
            return explanation
            
        except Exception as e:
            logging.error(f"Ошибка генерации объяснения: {e}")
            return f"Правильный ответ: {correct_answer}. Для решения этой задачи нужно применить знания по теме '{topic}'." 