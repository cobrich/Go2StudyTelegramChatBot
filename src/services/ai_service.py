import logging
import google.generativeai as genai
from typing import Optional, Tuple, List
import re
from src.config.constants import GEMINI_API_KEY, GEMINI_MODEL, MAX_OPTION_LENGTH
import json

class AIService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate_task(self, topic: str, main_topic: str = None, language: str = 'ru') -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """
        Generate a single task for the given topic.
        Returns: (question, correct_answer, incorrect_options, explanation)
        """
        # Формируем контекст темы
        if main_topic:
            clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
            if language == 'kk':
                topic_context = f"'{topic}' тақырыбы '{clean_main_topic}' бөлімінен"
            else:
                topic_context = f"Тема '{topic}' из раздела '{clean_main_topic}'"
        else:
            if language == 'kk':
                topic_context = f"'{topic}' тақырыбы"
            else:
                topic_context = f"Тема '{topic}'"

        if language == 'kk':
            prompt_template = (
                "Сіздің міндетіңіз - 5-6 сынып оқушыларына арналған математикалық есептер жасау бойынша сарапшы болу.\n"
                f"Сізге мына тақырып бойынша БІР ерекше және қызықты сұрақ жасау керек: {topic_context}.\n"
                "Сұрақ жай есептеу емес, мүмкіндігінше кішкентай мәтінді есеп, логикалық жұмбақ немесе тақырыпқа сәйкес өмірлік жағдайда математикалық ұғымдарды қолдану есебі болуы керек. Тек сандармен ерекшеленетін бірдей типті сұрақтар жасаудан аулақ болыңыз.\n\n"
                "ЕСЕПКЕ ҚОЙЫЛАТЫН ТАЛАПТАР:\n"
                "1. **Мақсатты аудитория:** 5-6 сынып оқушылары.\n"
                f"2. **Тақырып:** {topic_context}.\n"
                "3. **Күрделілік:** Сұрақ ойша немесе минималды жазбамен шешілуі керек, әдетте 2-3 логикалық қадам немесе математикалық амалдан аспауы керек. Ол ойлануды талап ететіндей күрделі, бірақ тым қиын болмауы керек.\n"
                "4. **Бірегейлік:** Сұрақ жаңа, алдыңғыларды қайталамайтын болуы керек.\n"
                "5. **Контекст және өлшем бірліктері:** Егер сұрақта өлшем бірліктері қолданылса, жауап та сол бірліктерде болуы керек. Барлық сандық мәндер мен шарттар нақты және тақырыпқа сәйкес болуы керек.\n"
                "6. **Дұрыс жауап:** Нақты, бір мағыналы және 40 символдан аспауы керек.\n"
                "7. **Қате жауаптар (МІНДЕТТІ ТҮРДЕ 3 дана):** Сенімді болуы керек, оқушылардың осы тақырып бойынша жиі жасайтын қателерін немесе қате түсініктерін көрсетуі керек. Олар айқын қате болмауы керек.\n"
                "8. **Түсіндірме:** Қысқа, нақты, қадамдық (қолданылатын болса) және шешім логикасы мен ұғымды түсінуге көмектесетін болуы керек.\n\n"
                "ҚАТАҢ ШЫҒАРУ ФОРМАТЫ (ӘРБІР ПУНКТ ЖАҢА ЖОЛДАН, ТАҚЫРЫПТАР БАС ӘРІПТЕРМЕН):\n"
                "СҰРАҚ: [сұрақ мәтіні]\n"
                "ДҰРЫС ЖАУАП: [дұрыс жауап мәтіні]\n"
                "ҚАТЕ ЖАУАП 1: [бірінші қате нұсқа мәтіні]\n"
                "ҚАТЕ ЖАУАП 2: [екінші қате нұсқа мәтіні]\n"
                "ҚАТЕ ЖАУАП 3: [үшінші қате нұсқа мәтіні]\n"
                "ТҮСІНДІРМЕ: [дұрыс жауаптың түсіндірме мәтіні]\n"
            )
            
            # Казахские ключевые слова для парсинга
            question_pattern = r"СҰРАҚ:\s*(.*?)\s*ДҰРЫС ЖАУАП:"
            correct_answer_pattern = r"ДҰРЫС ЖАУАП:\s*(.*?)(?=\s*ҚАТЕ ЖАУАП 1:|\s*ТҮСІНДІРМЕ:)"
            incorrect_pattern = r"ҚАТЕ ЖАУАП \d+:\s*(.*?)(?=\s*ҚАТЕ ЖАУАП \d+:|\s*ТҮСІНДІРМЕ:|$)"
            explanation_pattern = r"ТҮСІНДІРМЕ:\s*(.*)"
            
        else:
            prompt_template = (
                "Твоя задача - быть экспертом по созданию обучающих математических задач для учеников 5-6 классов.\n"
                f"Тебе нужно сгенерировать ОДИН уникальный и интересный вопрос по теме: {topic_context}.\n"
                "Вопрос должен быть не просто на вычисление, а, по возможности, представлять собой небольшую текстовую задачу, логическую головоломку или задачу на применение математических концепций в жизненной ситуации, соответствующей теме. Избегай создания однотипных вопросов, отличающихся только числами.\n\n"
                "ТРЕБОВАНИЯ К ЗАДАЧЕ:\n"
                "1.  **Целевая аудитория:** Ученики 5-6 класса.\n"
                f"2.  **Тема:** {topic_context}.\n"
                "3.  **Сложность:** Вопрос должен быть решаем в уме или с минимальными записями, обычно не более 2-3 логических шагов или математических операций. Он должен быть достаточно сложным, чтобы требовать размышлений, но не чрезмерно трудным.\n"
                "4.  **Уникальность:** Вопрос должен быть новым, не повторяющим предыдущие.\n"
                "5.  **Контекст и единицы:** Если в вопросе используются единицы измерения, ответ также должен быть в этих единицах. Все числовые значения и условия должны быть реалистичными и соответствовать теме.\n"
                "6.  **Правильный ответ:** Должен быть четким, однозначным и не превышать 40 символов.\n"
                "7.  **Неправильные ответы (ОБЯЗАТЕЛЬНО 3 штуки):** Должны быть правдоподобными, отражать типичные ошибки или заблуждения учеников по данной теме. Они не должны быть очевидно неверными.\n"
                "8.  **Объяснение:** Должно быть кратким, ясным, пошаговым (если применимо) и помогать понять логику решения и концепцию.\n\n"
                "СТРОГИЙ ФОРМАТ ВЫВОДА (КАЖДЫЙ ПУНКТ С НОВОЙ СТРОКИ, ЗАГОЛОВКИ ЗАГЛАВНЫМИ БУКВАМИ):\n"
                "ВОПРОС: [текст вопроса]\n"
                "ПРАВИЛЬНЫЙ ОТВЕТ: [текст правильного ответа]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [текст первого неправильного варианта]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [текст второго неправильного варианта]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [текст третьего неправильного варианта]\n"
                "ОБЪЯСНЕНИЕ: [текст объяснения правильного ответа]\n"
            )
            
            # Русские ключевые слова для парсинга
            question_pattern = r"ВОПРОС:\s*(.*?)\s*ПРАВИЛЬНЫЙ ОТВЕТ:"
            correct_answer_pattern = r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|\s*ОБЪЯСНЕНИЕ:)"
            incorrect_pattern = r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|\s*ОБЪЯСНЕНИЕ:|$)"
            explanation_pattern = r"ОБЪЯСНЕНИЕ:\s*(.*)"
        
        try:
            response_text = self.model.generate_content(prompt_template).text
            
            # Parse response
            q_match = re.search(question_pattern, response_text, re.DOTALL | re.IGNORECASE)
            correct_a_match = re.search(correct_answer_pattern, response_text, re.DOTALL | re.IGNORECASE)
            
            question = q_match.group(1).strip() if q_match else None
            correct_answer = self._clean_option_text(correct_a_match.group(1).strip()) if correct_a_match else None
            
            incorrect_options = []
            search_start_index = 0
            if correct_a_match:
                if language == 'kk':
                    first_incorrect_or_expl_match = re.search(r"ҚАТЕ ЖАУАП 1:|ТҮСІНДІРМЕ:", response_text[correct_a_match.end():], re.IGNORECASE)
                else:
                    first_incorrect_or_expl_match = re.search(r"НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:", response_text[correct_a_match.end():], re.IGNORECASE)
                if first_incorrect_or_expl_match:
                    search_start_index = correct_a_match.end() + first_incorrect_or_expl_match.start()
            
            for match in re.finditer(incorrect_pattern, response_text[search_start_index:], re.DOTALL | re.IGNORECASE):
                option_text = match.group(1).strip()
                if option_text:
                    cleaned = self._clean_option_text(option_text)
                    if len(cleaned) <= MAX_OPTION_LENGTH:
                        incorrect_options.append(cleaned)
            
            e_match = re.search(explanation_pattern, response_text, re.DOTALL | re.IGNORECASE)
            explanation = e_match.group(1).strip() if e_match else None
            
            # Validate response - требуем точно 3 неправильных ответа
            if not (question and correct_answer and explanation and len(incorrect_options) == 3):
                logging.warning(f"[generate_task] Validation failed: question={bool(question)}, answer={bool(correct_answer)}, explanation={bool(explanation)}, incorrect_options={len(incorrect_options)} (need exactly 3)")
                return None, None, None, None
            
            if len(correct_answer) > MAX_OPTION_LENGTH:
                logging.warning(f"[generate_task] Answer too long: {len(correct_answer)} > {MAX_OPTION_LENGTH}")
                return None, None, None, None
            
            return question, correct_answer, incorrect_options, explanation
            
        except Exception as err:
            logging.error(f"Error generating AI task: {err}")
            return None, None, None, None

    def generate_task_v3(self, topic: str, main_topic: str = None, language: str = 'ru') -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """
        Generate a single task using Meta-prompt approach (Variant 3).
        AI becomes a topic expert and generates questions with 95-98% accuracy.
        """
        # Формируем контекст темы
        if main_topic:
            clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
            if language == 'kk':
                topic_context = f"'{topic}' тақырыбы '{clean_main_topic}' бөлімінен"
            else:
                topic_context = f"Тема '{topic}' из раздела '{clean_main_topic}'"
        else:
            if language == 'kk':
                topic_context = f"'{topic}' тақырыбы"
            else:
                topic_context = f"Тема '{topic}'"

        if language == 'kk':
            prompt_template = self._get_meta_kazakh_prompt(topic, clean_main_topic if main_topic else "")
            # Казахские ключевые слова для парсинга
            question_pattern = r"СҰРАҚ:\s*(.*?)\s*(?=ДҰРЫС ЖАУАП:|$)"
            correct_answer_pattern = r"ДҰРЫС ЖАУАП:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП 1:|ТҮСІНДІРМЕ:|$)"
            incorrect_pattern = r"ҚАТЕ ЖАУАП \d+:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП \d+:|ТҮСІНДІРМЕ:|$)"
            explanation_pattern = r"ТҮСІНДІРМЕ:\s*(.*?)(?=\n\n|$)"
        else:
            prompt_template = self._get_meta_russian_prompt(topic, clean_main_topic if main_topic else "")
            # Русские ключевые слова для парсинга
            question_pattern = r"ВОПРОС:\s*(.*?)\s*(?=ПРАВИЛЬНЫЙ ОТВЕТ:|$)"
            correct_answer_pattern = r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:|$)"
            incorrect_pattern = r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|ОБЪЯСНЕНИЕ:|$)"
            explanation_pattern = r"ОБЪЯСНЕНИЕ:\s*(.*?)(?=\n\n|$)"

        try:
            response_text = self.model.generate_content(prompt_template).text
            logging.info(f"[generate_task_v3] AI response for topic '{topic}': {response_text[:200]}...")
            
            return self._parse_response_v3(response_text, language)
            
        except Exception as err:
            logging.error(f"Error generating AI task v3: {err}")
            return None, None, None, None

    def _get_meta_russian_prompt(self, topic: str, main_topic: str) -> str:
        """Создает Meta-prompt для русского языка"""
        return f"""ЭТАП 1: СТАНЬ ЭКСПЕРТОМ ПО ТЕМЕ
Ты сейчас становишься экспертом по математической теме "{topic}" для учеников 5-6 классов.

Проанализируй название темы "{topic}" и определи:
- Какие ключевые математические понятия она включает
- Какие типы задач характерны для этой темы
- Какие ошибки часто делают ученики в этой теме
- Какой уровень сложности подходит для 5-6 класса

ЭТАП 2: ОПРЕДЕЛИ ГРАНИЦЫ ТЕМЫ
Исходя из анализа темы "{topic}", четко определи:
- ЧТО ДОЛЖНО быть в вопросе по этой теме
- ЧТО НЕ ДОЛЖНО быть в вопросе (чтобы не выходить за рамки темы)
- Какие числовые значения и форматы ответов допустимы

ЭТАП 3: СОЗДАЙ ОБРАЗЦОВЫЙ ВОПРОС
Теперь создай ОДИН идеальный вопрос, который:
- На 100% соответствует теме "{topic}"
- Подходит для учеников 5-6 классов
- Интересен и не банален
- Имеет четкий однозначный ответ
- Включает РОВНО 3 правдоподобных неправильных варианта (НИ БОЛЬШЕ, НИ МЕНЬШЕ!)
- Сопровождается понятным объяснением

ЭТАП 4: ПРОВЕРЬ КАЧЕСТВО
Перед выводом окончательного ответа убедись:
- Вопрос точно соответствует теме "{topic}"
- Правильный ответ действительно правильный
- Неправильных ответов РОВНО 3 штуки (не 2, не 4, не 5, а именно 3!)
- Объяснение логично и понятно

КРИТИЧЕСКИ ВАЖНО: В твоем ответе должно быть РОВНО 3 неправильных ответа. Не больше и не меньше!

СТРОГИЙ ФОРМАТ ВЫВОДА (ОБЯЗАТЕЛЬНО СОБЛЮДАЙ):
ВОПРОС: [текст вопроса]
ПРАВИЛЬНЫЙ ОТВЕТ: [правильный ответ, максимум 40 символов]
НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [первый неправильный вариант]
НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [второй неправильный вариант]
НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [третий неправильный вариант]
ОБЪЯСНЕНИЕ: [краткое пошаговое объяснение решения]

ВНИМАНИЕ: НЕ добавляй дополнительные неправильные ответы! Только 3!"""

    def _get_meta_kazakh_prompt(self, topic: str, main_topic: str) -> str:
        """Создает Meta-prompt для казахского языка"""
        return f"""1-КЕЗЕҢ: ТАҚЫРЫП БОЙЫНША САРАПШЫ БОЛ
Сіз қазір 5-6 сынып оқушыларына арналған "{topic}" математикалық тақырыбы бойынша сарапшы боласыз.

"{topic}" тақырыбының атауын талдап, анықтаңыз:
- Қандай негізгі математикалық ұғымдарды қамтиды
- Осы тақырыпқа қандай есеп түрлері тән
- Оқушылар осы тақырыпта қандай қателер жиі жасайды
- 5-6 сыныпқа қандай күрделілік деңгейі сәйкес келеді

2-КЕЗЕҢ: ТАҚЫРЫП ШЕКАРАСЫН АНЫҚТА
"{topic}" тақырыбын талдау негізінде нақты анықтаңыз:
- Осы тақырып бойынша сұрақта НЕ БОЛУЫ КЕРЕК
- Сұрақта НЕ БОЛМАУЫ КЕРЕК (тақырыптан шықпау үшін)
- Қандай сандық мәндер мен жауап форматтары рұқсат етілген

3-КЕЗЕҢ: ҮЛГІЛІ СҰРАҚ ЖАСА
Енді мына талаптарға сәйкес БІР керемет сұрақ жасаңыз:
- "{topic}" тақырыбына 100% сәйкес келеді
- 5-6 сынып оқушыларына лайық
- Қызықты және жай емес
- Нақты бір мағыналы жауабы бар
- ДӘЛМЕ-ДӘЛ 3 сенімді қате нұсқаларды қамтиды (КӨБІРЕК ТЕ, АЗЫРАҚ ТА ЕМЕС!)
- Түсінікті түсіндірмемен қоса беріледі

4-КЕЗЕҢ: САПАНЫ ТЕКСЕР
Түпкілікті жауапты шығармас бұрын көз жеткізіңіз:
- Сұрақ "{topic}" тақырыбына дәл сәйкес келеді
- Дұрыс жауап шынымен дұрыс
- Қате жауаптар ДӘЛМЕ-ДӘЛ 3 дана (2 де емес, 4 те емес, 5 те емес, дәл 3!)
- Түсіндірме логикалы және түсінікті

ӨТЕ МАҢЫЗДЫ: Сіздің жауабыңызда ДӘЛМЕ-ДӘЛ 3 қате жауап болуы керек. Көбірек те, азырақ та емес!

ҚАТАҢ ШЫҒАРУ ФОРМАТЫ (МІНДЕТТІ ТҮРДЕ САҚТАҢЫЗ):
СҰРАҚ: [сұрақ мәтіні]
ДҰРЫС ЖАУАП: [дұрыс жауап, максимум 40 символ]
ҚАТЕ ЖАУАП 1: [бірінші қате нұсқа]
ҚАТЕ ЖАУАП 2: [екінші қате нұсқа]
ҚАТЕ ЖАУАП 3: [үшінші қате нұсқа]
ТҮСІНДІРМЕ: [қысқа қадамдық шешім түсіндірмесі]

НАЗАР АУДАРЫҢЫЗ: Қосымша қате жауаптар қоспаңыз! Тек 3 ғана!"""

    def _parse_response_v3(self, response_text: str, language: str) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """Парсинг ответа для Meta-prompt подхода"""
        if language == 'kk':
            question_pattern = r"СҰРАҚ:\s*(.*?)\s*(?=ДҰРЫС ЖАУАП:|$)"
            correct_answer_pattern = r"ДҰРЫС ЖАУАП:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП 1:|ТҮСІНДІРМЕ:|$)"
            incorrect_pattern = r"ҚАТЕ ЖАУАП \d+:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП \d+:|ТҮСІНДІРМЕ:|$)"
            explanation_pattern = r"ТҮСІНДІРМЕ:\s*(.*?)(?=\n\n|$)"
        else:
            question_pattern = r"ВОПРОС:\s*(.*?)\s*(?=ПРАВИЛЬНЫЙ ОТВЕТ:|$)"
            correct_answer_pattern = r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:|$)"
            incorrect_pattern = r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|ОБЪЯСНЕНИЕ:|$)"
            explanation_pattern = r"ОБЪЯСНЕНИЕ:\s*(.*?)(?=\n\n|$)"

        # Извлекаем компоненты
        q_match = re.search(question_pattern, response_text, re.DOTALL | re.IGNORECASE)
        correct_a_match = re.search(correct_answer_pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        question = q_match.group(1).strip() if q_match else None
        correct_answer = self._clean_option_text(correct_a_match.group(1).strip()) if correct_a_match else None
        
        # Извлекаем неправильные ответы
        incorrect_options = []
        for match in re.finditer(incorrect_pattern, response_text, re.DOTALL | re.IGNORECASE):
            option_text = match.group(1).strip()
            if option_text:
                cleaned = self._clean_option_text(option_text)
                if len(cleaned) <= MAX_OPTION_LENGTH:
                    incorrect_options.append(cleaned)
        
        # Извлекаем объяснение
        e_match = re.search(explanation_pattern, response_text, re.DOTALL | re.IGNORECASE)
        explanation = e_match.group(1).strip() if e_match else None
        
        # Валидация - требуем точно 3 неправильных ответа
        if not (question and correct_answer and explanation and len(incorrect_options) == 3):
            logging.warning(f"[_parse_response_v3] Validation failed: question={bool(question)}, answer={bool(correct_answer)}, explanation={bool(explanation)}, incorrect_options={len(incorrect_options)} (need exactly 3)")
            return None, None, None, None
        
        if len(correct_answer) > MAX_OPTION_LENGTH:
            logging.warning(f"[_parse_response_v3] Answer too long: {len(correct_answer)} > {MAX_OPTION_LENGTH}")
            return None, None, None, None
        
        return question, correct_answer, incorrect_options, explanation

    @staticmethod
    def _clean_option_text(text: str) -> str:
        """Clean option text from unwanted characters and formatting."""
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove common unwanted patterns
        text = re.sub(r'^[A-ZА-Г]\)\s*', '', text)  # Remove option letters like "A) "
        text = re.sub(r'^\d+\.\s*', '', text)      # Remove numbering like "1. "
        
        return text.strip()

    def generate_detailed_explanation(self, question: str, correct_answer: str, topic: str, language: str = 'ru') -> str:
        """
        Generate detailed explanation for a question and its correct answer.
        
        Args:
            question: The question text
            correct_answer: The correct answer text
            topic: The topic/subject of the question
            language: Language for the explanation ('ru' or 'kk')
            
        Returns:
            Detailed explanation text
        """
        if language == 'kk':
            prompt = f"""Сіз математика пәнінің мұғалімісіз. Сізге 5-6 сынып оқушыларына арналған математикалық есептің толық түсіндірмесін жасау керек.

ТАҚЫРЫП: {topic}

СҰРАҚ: {question}

ДҰРЫС ЖАУАП: {correct_answer}

Сіздің міндетіңіз - осы сұрақтың дұрыс жауабын неліктен осылай шешу керектігін қысқа, нақты және түсінікті түрде түсіндіру. Түсіндірме:

1. Қысқа болуы керек (2-4 сөйлем)
2. Оқушыға неліктен осы жауап дұрыс екенін көрсетуі керек
3. Қажет болса, қысқа есептеу қадамдарын көрсетуі керек
4. Тақырыпқа сәйкес математикалық ұғымдарды пайдалануы керек

Тек түсіндірме мәтінін жазыңыз, басқа ештеңе қоспаңыз:"""
        else:
            prompt = f"""Вы учитель математики. Вам нужно создать подробное объяснение для математической задачи для учеников 5-6 классов.

ТЕМА: {topic}

ВОПРОС: {question}

ПРАВИЛЬНЫЙ ОТВЕТ: {correct_answer}

Ваша задача - кратко, четко и понятно объяснить, почему именно этот ответ правильный. Объяснение должно:

1. Быть кратким (2-4 предложения)
2. Показать ученику, почему именно этот ответ верный
3. При необходимости показать краткие шаги вычисления
4. Использовать математические понятия, соответствующие теме

Напишите только текст объяснения, ничего больше:"""

        try:
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            # Очищаем объяснение от лишних символов и форматирования
            explanation = re.sub(r'^["\']|["\']$', '', explanation)  # Убираем кавычки в начале/конце
            explanation = re.sub(r'^\s*[-•]\s*', '', explanation, flags=re.MULTILINE)  # Убираем маркеры списков
            explanation = explanation.strip()
            
            # Проверяем, что объяснение не пустое
            if not explanation:
                if language == 'kk':
                    explanation = f"Дұрыс жауап: {correct_answer}. Бұл тақырып бойынша негізгі ұғымдарды қолдану арқылы табылады."
                else:
                    explanation = f"Правильный ответ: {correct_answer}. Это решается применением основных понятий по данной теме."
            
            return explanation
            
        except Exception as e:
            logging.error(f"Error generating detailed explanation: {e}")
            # Возвращаем базовое объяснение в случае ошибки
            if language == 'kk':
                return f"Дұрыс жауап: {correct_answer}"
            else:
                return f"Правильный ответ: {correct_answer}"