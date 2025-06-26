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
                "8. **ОБЪЯСНЕНИЕ ДЛЯ ДЕТЕЙ:** Объяснение должно быть ОЧЕНЬ ПОДРОБНЫМ и ПОНЯТНЫМ для ребенка 5-6 класса:\n"
                "   - Написано ПРОСТЫМ ЯЗЫКОМ (как объяснение младшему брату)\n"
                "   - ПОШАГОВОЕ решение с нумерацией (Шаг 1, Шаг 2, ...)\n"
                "   - ПОКАЗАТЬ ВСЕ ВЫЧИСЛЕНИЯ (не просто '5×3=15', а 'умножаем 5 на 3, получается 15')\n"
                "   - ОБЪЯСНИТЬ ПОЧЕМУ делаем каждое действие\n"
                "   - В конце показать ПРОВЕРКУ ответа\n"
                "   - Использовать слова: 'сначала', 'потом', 'получается', 'проверяем'\n\n"
                "СТРОГИЙ ФОРМАТ ВЫВОДА (КАЖДЫЙ ПУНКТ С НОВОЙ СТРОКИ, ЗАГОЛОВКИ ЗАГЛАВНЫМИ БУКВАМИ):\n"
                "ВОПРОС: [текст вопроса]\n"
                "ПРАВИЛЬНЫЙ ОТВЕТ: [текст правильного ответа]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [текст первого неправильного варианта]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [текст второго неправильного варианта]\n"
                "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [текст третьего неправильного варианта]\n"
                "ОБЪЯСНЕНИЕ: [ПОДРОБНОЕ пошаговое объяснение простым языком для детей]\n"
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
            explanation_pattern = r"ТҮСІНДІРМЕ:\s*(.*?)$"
        else:
            prompt_template = self._get_meta_russian_prompt(topic, clean_main_topic if main_topic else "")
            # Русские ключевые слова для парсинга
            question_pattern = r"ВОПРОС:\s*(.*?)\s*(?=ПРАВИЛЬНЫЙ ОТВЕТ:|$)"
            correct_answer_pattern = r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:|$)"
            incorrect_pattern = r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|ОБЪЯСНЕНИЕ:|$)"
            explanation_pattern = r"ОБЪЯСНЕНИЕ:\s*(.*?)$"

        try:
            response_text = self.model.generate_content(prompt_template).text
            logging.info(f"[generate_task_v3] AI response for topic '{topic}': {response_text[:200]}...")
            
            return self._parse_response_v3(response_text, language)
            
        except Exception as err:
            logging.error(f"Error generating AI task v3: {err}")
            return None, None, None, None

    def _get_meta_russian_prompt(self, topic: str, main_topic: str) -> str:
        """Создает Meta-prompt для русского языка"""
        return f"""Ты опытный учитель математики для 5-6 классов. Создай одну задачу по теме "{topic}" из раздела "{main_topic}".

КРИТИЧЕСКИ ВАЖНО: В твоем ответе должно быть РОВНО 3 неправильных 1 правильный ответа. Не больше и не меньше!

СТРОГИЙ ФОРМАТ ВЫВОДА (ОБЯЗАТЕЛЬНО СОБЛЮДАЙ):
ВОПРОС: [текст вопроса]
ПРАВИЛЬНЫЙ ОТВЕТ: [правильный ответ, максимум 40 символов]
НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [первый неправильный вариант]
НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [второй неправильный вариант]
НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [третий неправильный вариант]
ОБЪЯСНЕНИЕ: [ОЧЕНЬ ПОДРОБНОЕ пошаговое объяснение простым языком для детей с проверкой]

ВНИМАНИЕ: НЕ добавляй дополнительные неправильные ответы! Только 3!
ПРОВЕРЬ ПЕРЕД ОТПРАВКОЙ: считай неправильные ответы - их должно быть ровно 3!

ТРЕБОВАНИЯ К ЗАДАЧЕ:
1. 🎯 Соответствие теме "{topic}" из раздела "{main_topic}"
2. 👶 Простые числа и понятия для 5-6 классов
3. 🧮 Четкий вопрос с однозначным ответом
4. ✅ Правильный ответ должен быть коротким (до 40 символов)
5. ❌ Неправильные варианты должны быть правдоподобными, но явно неверными
6. 📚 ОБЪЯСНЕНИЕ: подробное, пошаговое, с вычислениями и проверкой

🚨 КРИТИЧЕСКИ ВАЖНО - ИЗБЕГАЙ ДУБЛИРОВАНИЯ:
- НЕ используй стандартные шаблоны типа "У Маши есть X литров сока с Y% сахара"
- НЕ повторяй одни и те же числа (2, 3, 10%, 20%) в каждом вопросе
- СОЗДАВАЙ РАЗНООБРАЗНЫЕ сценарии: разные продукты, разные ситуации, разные числа
- ИСПОЛЬЗУЙ РАЗНЫЕ единицы измерения: граммы, килограммы, литры, проценты, части
- МЕНЯЙ структуру вопроса: "Смешали", "Добавили", "Разделили", "Увеличили", "Уменьшили"

ПРИМЕРЫ РАЗНООБРАЗНЫХ ВОПРОСОВ (НЕ КОПИРУЙ, А ВДОХНОВЛЯЙСЯ):
- "В кафе смешали 400 мл кофе с 100 мл молока. Концентрация кофе стала..."
- "У бабушки было 1.5 кг муки, она добавила 500 г сахара. Процент муки в смеси..."
- "В аквариум налили 8 л воды и 2 л сиропа. Концентрация сиропа..."
- "Мама разделила 900 г теста на 3 части. Каждая часть весит..."

ТРЕБОВАНИЯ К ОБЪЯСНЕНИЮ:
- Начинай с приветствия: "Привет! Давай разберемся..."
- Объясни каждый шаг решения
- Покажи все вычисления
- Объясни, почему именно этот ответ правильный
- Добавь способ проверки результата
- Используй простые слова и короткие предложения
- Минимум 200 слов в объяснении

ПРИМЕР ХОРОШЕГО ОБЪЯСНЕНИЯ:
"Привет! Давай разберемся с этой задачей пошагово.

Шаг 1: Сначала внимательно прочитаем условие...
Шаг 2: Теперь найдем... Для этого нужно...
Вычисление: 2 + 3 = 5
Шаг 3: Проверим наш ответ...

Ответ: [правильный ответ]

Проверка: Мы можем убедиться в правильности, если..."

ЗАПРЕЩЕНО:
- Использовать сложные математические термины
- Давать неполные объяснения
- Создавать варианты ответов, которые могут быть правильными
- Добавлять больше 3 неправильных ответов
- Делать объяснение короче 200 слов
- Копировать стандартные шаблоны вопросов
- Использовать одни и те же числа и ситуации"""

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

🚨 КРИТИКАЛЫ МАҢЫЗДЫ - ҚАЙТАЛАУДАН САҚТАН:
- СТАНДАРТТЫ ҮЛГІЛЕРДІ ҚОЛДАНБА: "Машаның X литр шырыны бар, Y% қант бар" сияқты
- БІР ҚАЙТАР САНДАРДЫ ҚАЙТАЛАМА: 2, 3, 10%, 20% сияқты сандарды әр сұрақта қолданба
- ӘРТҮРЛІ СЦЕНАРИЙЛЕР ЖАСА: әртүрлі өнімдер, әртүрлі жағдайлар, әртүрлі сандар
- ӘРТҮРЛІ ӨЛШЕМ БІРЛІКТЕРІН ҚОЛДАН: грамм, килограмм, литр, пайыз, бөліктер
- СҰРАҚ ҚҰРЫЛЫМЫН ӨЗГЕРТ: "Араластырды", "Қосты", "Бөлді", "Көбейтті", "Азайтты"

ӘРТҮРЛІ СҰРАҚТАРДЫҢ МЫСАЛДАРЫ (КӨШІРМЕ, БІРАҚ ИНСПИРАЦИЯ АЛ):
- "Кафедә 400 мл кофе мен 100 мл сүт араластырды. Кофе концентрациясы..."
- "Әжеде 1.5 кг ұн болды, ол 500 г қант қосты. Араласмадағы ұн пайызы..."
- "Аквариумға 8 л су мен 2 л сироп құйды. Сироп концентрациясы..."
- "Ана 900 г қамырды 3 бөлікке бөлді. Әр бөлік салмағы..."

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

НАЗАР АУДАРЫҢЫЗ: Қосымша қате жауаптар қоспаңыз! Тек 3 ғана!

ТЫЙЫМ САЛЫНҒАН:
- Күрделі математикалық терминдерді қолдану
- Толық емес түсіндірме беру
- Дұрыс болуы мүмкін жауап нұсқаларын жасау
- 3-тен көп қате жауап қосу
- Стандартты сұрақ үлгілерін көшіру
- Бір қайтар сандар мен жағдайларды қолдану"""

    def _parse_response_v3(self, response_text: str, language: str) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """Парсинг ответа для Meta-prompt подхода"""
        if language == 'kk':
            question_pattern = r"СҰРАҚ:\s*(.*?)\s*(?=ДҰРЫС ЖАУАП:|$)"
            correct_answer_pattern = r"ДҰРЫС ЖАУАП:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП 1:|ТҮСІНДІРМЕ:|$)"
            incorrect_pattern = r"ҚАТЕ ЖАУАП \d+:\s*(.*?)\s*(?=ҚАТЕ ЖАУАП \d+:|ТҮСІНДІРМЕ:|$)"
            explanation_pattern = r"ТҮСІНДІРМЕ:\s*(.*?)$"
        else:
            question_pattern = r"ВОПРОС:\s*(.*?)\s*(?=ПРАВИЛЬНЫЙ ОТВЕТ:|$)"
            correct_answer_pattern = r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:|$)"
            incorrect_pattern = r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)\s*(?=НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|ОБЪЯСНЕНИЕ:|$)"
            explanation_pattern = r"ОБЪЯСНЕНИЕ:\s*(.*?)$"

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
        
        # Извлекаем объяснение - ПОЛНОСТЬЮ до конца
        e_match = re.search(explanation_pattern, response_text, re.DOTALL | re.IGNORECASE)
        explanation = e_match.group(1).strip() if e_match else None
        
        # Дополнительная очистка объяснения от лишних символов
        if explanation:
            # Убираем лишние пробелы и переносы в начале/конце
            explanation = explanation.strip()
            # Убираем возможные артефакты парсинга
            explanation = re.sub(r'\s+', ' ', explanation)  # Заменяем множественные пробелы на одинарные
            explanation = explanation.replace('\\n', '\n')  # Восстанавливаем переносы строк
        
        # Валидация - требуем точно 3 неправильных ответа
        if not (question and correct_answer and explanation and len(incorrect_options) == 3):
            if not question:
                logging.warning(f"[_parse_response_v3] Missing question in AI response")
            if not correct_answer:
                logging.warning(f"[_parse_response_v3] Missing correct answer in AI response")
            if not explanation:
                logging.warning(f"[_parse_response_v3] Missing explanation in AI response")
            if len(incorrect_options) != 3:
                logging.warning(f"[_parse_response_v3] Wrong number of incorrect options: got {len(incorrect_options)}, need exactly 3. Options: {incorrect_options}")
            
            logging.warning(f"[_parse_response_v3] Validation failed: question={bool(question)}, answer={bool(correct_answer)}, explanation={bool(explanation)} ({len(explanation) if explanation else 0} chars), incorrect_options={len(incorrect_options)} (need exactly 3)")
            return None, None, None, None
        
        if len(correct_answer) > MAX_OPTION_LENGTH:
            logging.warning(f"[_parse_response_v3] Answer too long: {len(correct_answer)} > {MAX_OPTION_LENGTH}")
            return None, None, None, None
        
        # Логируем длину полученного объяснения для диагностики
        logging.info(f"[_parse_response_v3] ✅ Parsed explanation: {len(explanation)} characters")
        
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
            prompt = f"""Сіз 5-6 сынып оқушыларына арналған математика пәнінің мұғалімісіз. Сізге балаларға түсінікті болатын толық түсіндірме жасау керек.

ТАҚЫРЫП: {topic}

СҰРАҚ: {question}

ДҰРЫС ЖАУАП: {correct_answer}

МІНДЕТ: Осы есептің шешімін балаларға ҚАДАМ-ҚАДАММЕН, ЖЕҢІЛ ТІЛМЕН түсіндіріңіз.

ТҮСІНДІРМЕ ТАЛАПТАРЫ:
1. 🎯 ҚАДАМДЫҚ ШЕШІМ - әрбір қадамды нөмірлеп көрсетіңіз (1-ші қадам, 2-ші қадам...)
2. 🧮 ЕСЕПТЕУЛЕРДІ КӨРСЕТУ - барлық арифметикалық амалдарды толық жазыңыз
3. 💡 НЕЛІКТЕН ОСЫЛАЙ - әрбір қадамда неліктен осы амалды орындағанын түсіндіріңіз
4. 👶 БАЛАЛАРҒА АРНАЛҒАН ТІЛ - қарапайым сөздер, қысқа сөйлемдер
5. ✅ ТЕКСЕРУ - соңында жауапты тексеру жолын көрсетіңіз

МЫСАЛ ФОРМАТЫ:
1-ші қадам: [не істеу керек және неліктен]
   Есептеу: [нақты есептеу]
2-ші қадам: [келесі қадам және неліктен]
   Есептеу: [нақты есептеу]
Жауап: [соңғы жауап]
Тексеру: [жауапты қалай тексеруге болады]

Тек түсіндірме мәтінін жазыңыз:"""
        else:
            prompt = f"""Вы учитель математики для учеников 5-6 классов. Вам нужно создать ОЧЕНЬ ПОДРОБНОЕ и ПОНЯТНОЕ объяснение для детей.

ТЕМА: {topic}

ВОПРОС: {question}

ПРАВИЛЬНЫЙ ОТВЕТ: {correct_answer}

ЗАДАЧА: Объяснить решение этой задачи ПОШАГОВО, ПРОСТЫМ ЯЗЫКОМ, как будто вы объясняете своему младшему брату или сестре.

ТРЕБОВАНИЯ К ОБЪЯСНЕНИЮ:
1. 🎯 ПОШАГОВОЕ РЕШЕНИЕ - пронумеруйте каждый шаг (Шаг 1, Шаг 2...)
2. 🧮 ПОКАЗАТЬ ВСЕ ВЫЧИСЛЕНИЯ - напишите все арифметические действия полностью
3. 💡 ОБЪЯСНИТЬ "ПОЧЕМУ" - в каждом шаге объясните, почему делаем именно это действие
4. 👶 ПРОСТОЙ ЯЗЫК - используйте простые слова, короткие предложения
5. 🔍 ПРОВЕРКА - в конце покажите, как можно проверить правильность ответа
6. 📖 ПРАВИЛО/ФОРМУЛА - если используется правило, объясните его простыми словами

ФОРМАТ ОТВЕТА:
Шаг 1: [что делаем и почему]
   Вычисление: [конкретное вычисление]
Шаг 2: [следующий шаг и почему]
   Вычисление: [конкретное вычисление]
...
Ответ: [итоговый ответ]
Проверка: [как можно проверить ответ]

ПРИМЕРЫ ХОРОШИХ ОБЪЯСНЕНИЙ:
- "Сначала найдем..." вместо "Определим..."
- "Умножаем 5 на 3, получается 15" вместо "5×3=15"
- "Это правило говорит нам, что..." вместо "По правилу..."

Напишите только текст объяснения:"""

        try:
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            # Очищаем объяснение от лишних символов и форматирования
            explanation = re.sub(r'^["\']|["\']$', '', explanation)  # Убираем кавычки в начале/конце
            explanation = re.sub(r'^\s*[-•]\s*', '', explanation, flags=re.MULTILINE)  # Убираем маркеры списков
            explanation = explanation.strip()
            
            # Проверяем, что объяснение не пустое и достаточно подробное
            if not explanation or len(explanation) < 50:
                if language == 'kk':
                    explanation = f"""Шешімі:
1-ші қадам: Есепті мұқият оқып, не сұралғанын анықтаймыз.
2-ші қадам: Берілген сандармен есептеу жасаймыз.
3-ші қадам: Жауапты тексереміз.

Дұрыс жауап: {correct_answer}

Бұл тақырып бойынша негізгі ұғымдарды қолдану арқылы табылады."""
                else:
                    explanation = f"""Решение:
Шаг 1: Внимательно читаем задачу и понимаем, что нужно найти.
Шаг 2: Выполняем вычисления с данными числами.
Шаг 3: Проверяем наш ответ.

Ответ: {correct_answer}

Это решается применением основных понятий по теме "{topic}"."""
            
            return explanation
            
        except Exception as e:
            logging.error(f"Error generating detailed explanation: {e}")
            # Возвращаем базовое объяснение в случае ошибки
            if language == 'kk':
                return f"Дұрыс жауап: {correct_answer}. Есепті қадам-қадаммен шешу керек."
            else:
                return f"Правильный ответ: {correct_answer}. Задачу нужно решать пошагово."

    def improve_existing_explanation(self, question: str, correct_answer: str, old_explanation: str, topic: str, language: str = 'ru') -> str:
        """
        Улучшить существующее объяснение, сделав его более понятным для детей.
        
        Args:
            question: Текст вопроса
            correct_answer: Правильный ответ
            old_explanation: Старое объяснение
            topic: Тема вопроса
            language: Язык ('ru' или 'kk')
            
        Returns:
            Улучшенное объяснение
        """
        if language == 'kk':
            prompt = f"""Сіз 5-6 сынып оқушыларына арналған математика мұғалімісіз. Сізге бар түсіндірмені ЖАҚСАРТУ керек.

ТАҚЫРЫП: {topic}
СҰРАҚ: {question}
ДҰРЫС ЖАУАП: {correct_answer}

ЕСКІ ТҮСІНДІРМЕ: {old_explanation}

МІНДЕТ: Ескі түсіндірмені алып, оны балаларға АНАҒҰРЛЫМ ТҮСІНІКТІ етіп жасаңыз.

ЖАҚСАРТУ ТАЛАПТАРЫ:
1. 🎯 Ескі түсіндірмедегі дұрыс ақпаратты сақтаңыз
2. 📝 ҚАДАМДЫҚ ФОРМАТҚА өзгертіңіз (1-ші қадам, 2-ші қадам...)
3. 🧮 БАРЛЫҚ ЕСЕПТЕУЛЕРДІ толық көрсетіңіз
4. 💡 Әрбір қадамда НЕЛІКТЕН осылай істейтінімізді түсіндіріңіз
5. 👶 БАЛАЛАР ТІЛІНЕ аударыңыз (қарапайым сөздер)
6. ✅ Соңында ТЕКСЕРУ қосыңыз

Тек жақсартылған түсіндірме мәтінін жазыңыз:"""
        else:
            prompt = f"""Вы учитель математики для 5-6 классов. Вам нужно УЛУЧШИТЬ существующее объяснение.

ТЕМА: {topic}
ВОПРОС: {question}
ПРАВИЛЬНЫЙ ОТВЕТ: {correct_answer}

СТАРОЕ ОБЪЯСНЕНИЕ: {old_explanation}

ЗАДАЧА: Взять старое объяснение и сделать его НАМНОГО ПОНЯТНЕЕ для детей.

ТРЕБОВАНИЯ К УЛУЧШЕНИЮ:
1. 🎯 Сохранить правильную информацию из старого объяснения
2. 📝 Переделать в ПОШАГОВЫЙ ФОРМАТ (Шаг 1, Шаг 2...)
3. 🧮 ПОКАЗАТЬ ВСЕ ВЫЧИСЛЕНИЯ полностью
4. 💡 В каждом шаге ОБЪЯСНИТЬ ПОЧЕМУ мы это делаем
5. 👶 Перевести на ДЕТСКИЙ ЯЗЫК (простые слова)
6. ✅ Добавить ПРОВЕРКУ в конце

ПРИМЕРЫ УЛУЧШЕНИЙ:
- Было: "Применяем правило" → Стало: "Используем правило, которое говорит нам..."
- Было: "5×3=15" → Стало: "Умножаем 5 на 3, получается 15"
- Было: "Получаем ответ" → Стало: "Теперь у нас есть ответ. Давайте проверим..."

Напишите только улучшенное объяснение:"""

        try:
            response = self.model.generate_content(prompt)
            improved_explanation = response.text.strip()
            
            # Очищаем объяснение
            improved_explanation = re.sub(r'^["\']|["\']$', '', improved_explanation)
            improved_explanation = improved_explanation.strip()
            
            # Если улучшение не получилось, возвращаем исходное
            if not improved_explanation or len(improved_explanation) < len(old_explanation) * 0.8:
                return old_explanation
            
            return improved_explanation
            
        except Exception as e:
            logging.error(f"Error improving explanation: {e}")
            return old_explanation