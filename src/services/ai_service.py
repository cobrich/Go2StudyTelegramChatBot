import logging
import google.generativeai as genai
from typing import Optional, Tuple, List
import re
from config.constants import GEMINI_API_KEY, GEMINI_MODEL, MAX_OPTION_LENGTH

class AIService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate_task(self, topic: str) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """Generate a single task for the given topic."""
        prompt_template = (
            "Твоя задача - быть экспертом по созданию обучающих математических задач для учеников 5-6 классов.\n"
            "Тебе нужно сгенерировать ОДИН уникальный и интересный вопрос по теме '{topic}'.\n"
            "Вопрос должен быть не просто на вычисление, а, по возможности, представлять собой небольшую текстовую задачу, логическую головоломку или задачу на применение математических концепций в жизненной ситуации, соответствующей теме. Избегай создания однотипных вопросов, отличающихся только числами.\n\n"
            "ТРЕБОВАНИЯ К ЗАДАЧЕ:\n"
            "1.  **Целевая аудитория:** Ученики 5-6 класса.\n"
            "2.  **Тема:** '{topic}'.\n"
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
            response_text = self.model.generate_content(prompt_template.format(topic=topic)).text
            
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