import logging
import google.generativeai as genai
from typing import Optional, Tuple, List
import re
from src.config.constants import GEMINI_API_KEY, GEMINI_MODEL, MAX_OPTION_LENGTH
import time
from google.api_core import exceptions

class ImprovedAIService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate_task(self, topic: str, main_topic: Optional[str] = None, language: str = 'ru', max_retries: int = 3) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """
        Генерирует задачу, используя универсальный и строго структурированный промпт
        для максимальной надежности парсинга.
        Включает механизм повторных попыток при ошибках лимита API.
        """
        prompt = self._get_universal_prompt(topic, main_topic, language)
        
        retries = 0
        while retries < max_retries:
            try:
                response_text = self.model.generate_content(prompt).text
                return self._parse_structured_response(response_text)
            
            except exceptions.ResourceExhausted as err:
                retries += 1
                # Экспоненциальная задержка: 2, 4, 8 секунд.
                wait_time = (2 ** retries)
                logging.warning(
                    f"Rate limit exceeded. Retrying in {wait_time} seconds... "
                    f"(Attempt {retries}/{max_retries})"
                )
                time.sleep(wait_time)

            except Exception as err:
                # При других ошибках (не связанных с лимитом) не повторяем запрос
                logging.error(f"Error generating structured AI task (non-retryable): {err}")
                return None, None, None, None

        logging.error(f"Failed to generate task after {max_retries} retries due to persistent rate limiting.")
        return None, None, None, None

    def _get_universal_prompt(self, topic: str, main_topic: Optional[str] = None, language: str = 'ru') -> str:
        if language == 'kk':
            topic_context = f"'{topic}'"
            if main_topic:
                clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
                topic_context += f", '{clean_main_topic}' бөлімінен"

            return f"""Міндет: Төменде көрсетілген тақырып бойынша 5-6 сынып оқушыларына арналған БІР сұрақ құрастырыңыз.

Генерация тақырыбы: {topic_context}

ҚАТАҢ САҚТАЛУЫ ТИІС ЕРЕЖЕЛЕР:
1.  **Бір сұрақ:** Жауапта тек бір ғана сұрақ болуы керек. Тізімдерді құрастырмаңыз.
2.  **Сұрақ стилі:**
    *   **Нақты ғылымдар үшін** (математика, логика): шешу үшін 2-3 логикалық қадамды қажет ететін мәтіндік есеп болуы керек.
    *   **Гуманитарлық тақырыптар үшін** (тарих, әдебиет): жай ғана күнді немесе есімді жаттауды емес, талдауды немесе білімді қолдануды талап ететін сұрақ болуы керек.
    *   Астыртын сұрақтар мен екіұшты жұмбақтардан **аулақ болыңыз**.
3.  **Жауаптың қатаң форматы:** Жауапты дәл осы форматта, маркерлерді қолдана отырып беріңіз. Ешқандай артық мәтін немесе сәлемдесу қоспаңыз.

[TOPIC]
{topic}
[QUESTION]
<Сұрақтың мәтіні осында>
[CORRECT_ANSWER]
<Дұрыс жауап осында>
[INCORRECT_OPTIONS]
<1-ші қате нұсқа>
<2-ші қате нұсқа>
<3-ші қате нұсқа>
[EXPLANATION]
<Дұрыс жауаптың неге дұрыс екендігі туралы толық, қадамдық түсіндірме>
"""
        else: # Default to Russian
            topic_context = f"'{topic}'"
            if main_topic:
                clean_main_topic = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
                topic_context += f" из раздела '{clean_main_topic}'"

            return f"""Задача: Сгенерировать ОДИН вопрос на русском языке по теме, указанной ниже. Вопрос должен быть рассчитан на учеников 5-6 классов.

Тема для генерации: {topic_context}

Правила, которым нужно строго следовать:
1.  **Один вопрос за раз:** Ответ должен содержать строго один вопрос. Не генерируй списки.
2.  **Стиль вопроса:**
    *   Для **точных наук** (математика, логика): это должна быть текстовая задача, требующая 2-3 логических шага для решения.
    *   Для **гуманитарных тем** (история, литература): это должен быть вопрос, требующий анализа или применения знаний, а не простого запоминания даты или имени.
    *   **Избегай** вопросов с подвохом и неоднозначных загадок.
3.  **Строгий формат ответа:** Предоставь ответ точно в таком формате, используя маркеры. Не добавляй никакого лишнего текста или приветствий.

[TOPIC]
{topic}
[QUESTION]
<Текст вопроса здесь>
[CORRECT_ANSWER]
<Правильный ответ здесь>
[INCORRECT_OPTIONS]
<Неправильный вариант 1>
<Неправильный вариант 2>
<Неправильный вариант 3>
[EXPLANATION]
<Подробное и пошаговое объяснение, почему правильный ответ является верным>
"""

    def _parse_structured_response(self, response_text: str) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """
        Парсит ответ от AI, сгенерированный с использованием строгого формата на основе маркеров.
        Этот метод намного надежнее, чем парсинг на основе регулярных выражений.
        """
        try:
            # Разделяем по маркерам. \s* позволяет игнорировать пробелы/переносы строк вокруг маркеров
            parts = re.split(r'\s*\[(TOPIC|QUESTION|CORRECT_ANSWER|INCORRECT_OPTIONS|EXPLANATION)\]\s*', response_text)

            if len(parts) < 11:
                logging.warning(f"Structured response parsing failed. Not all parts found. Response: {response_text}")
                return None, None, None, None

            # Первым элементом часто бывает пустая строка, удаляем ее, если есть
            if not parts[0].strip():
                parts = parts[1:]

            data = {parts[i]: parts[i+1].strip() for i in range(0, len(parts), 2)}

            question = data.get('QUESTION')
            # Очищаем ответ от распространенных ошибок форматирования AI
            correct_answer_raw = data.get('CORRECT_ANSWER', '')
            correct_answer = self._clean_option_text(re.sub(r'^\s*[\*\-•]\s*', '', correct_answer_raw).strip())

            # .splitlines() правильно обрабатывает разные типы переносов строк (\n, \r\n)
            incorrect_options_raw = data.get('INCORRECT_OPTIONS', '').splitlines()
            incorrect_options = [self._clean_option_text(opt) for opt in incorrect_options_raw if opt.strip()]

            explanation = self._clean_explanation_text(data.get('EXPLANATION'))

            if not (question and correct_answer and explanation and len(incorrect_options) >= 1):
                logging.warning(f"Structured response parsing failed. Missing essential data. Parsed data: {data}")
                return None, None, None, None

            if len(correct_answer) > MAX_OPTION_LENGTH:
                 return None, None, None, None

            incorrect_options = [opt for opt in incorrect_options if len(opt) <= MAX_OPTION_LENGTH]

            return question, correct_answer, incorrect_options, explanation

        except Exception as err:
            logging.error(f"Error parsing structured AI response: {err}\nResponse text: {response_text}")
            return None, None, None, None

    @staticmethod
    def _clean_option_text(text: str) -> str:
        """Clean option text by removing unnecessary words and extra spaces."""
        # Remove words like "ANSWER", "CORRECT", "INCORRECT", etc. in Russian and Kazakh
        text = re.sub(r'(ОТВЕТ|ПРАВИЛЬНЫЙ|НЕПРАВИЛЬНЫЙ|ВЕРНО|НЕВЕРНО|НЕВОЗМОЖНО ОПРЕДЕЛИТЬ|НЕВОЗМОЖНО СКАЗАТЬ|НЕ МОГУ ОПРЕДЕЛИТЬ|НЕ МОГУ СКАЗАТЬ|НЕ УВЕРЕН|НЕ ЗНАЮ|ЗАТРУДНЯЮСЬ ОТВЕТИТЬ|СЛОЖНО СКАЗАТЬ|НУЖНО ПОДУМАТЬ|ПРОВЕРЮ ЕЩЕ РАЗ|ДРУГОЙ ВАРИАНТ|ЭТО НЕВЕРНО|НЕПРАВИЛЬНЫЙ ВАРИАНТ|ПРАВИЛЬНЫЙ ВАРИАНТ|ВЕРНЫЙ ОТВЕТ|НЕВЕРНЫЙ ОТВЕТ|ЖАУАП|ДҰРЫС|ҚАТЕ|ДҰРЫС ЖАУАП|ҚАТЕ ЖАУАП|АНЫҚТАУ МҮМКІН ЕМЕС|АЙТА АЛМАЙМЫН|БІЛМЕЙМІН|СЕНІМДІ ЕМЕСПІН|\\s*\\(.*?\\))', '', text, flags=re.IGNORECASE)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove leading and trailing spaces
        return text.strip()

    def _clean_explanation_text(self, text: str) -> str:
        """Removes AI's meta-commentary and self-evaluation from explanations."""
        if not text:
            return ""

        # Удаляем любые строки, начинающиеся с "ЭТАП", "ШАГ", "КЕЗЕҢ", "ҚАДАМ" и т.д., а также маркеры списка
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Используем re.IGNORECASE для регистронезависимости
            if not re.match(r'^\s*(\*|\-|•|ЭТАП|ШАГ|КЕЗЕҢ|ҚАДАМ|САМОПРОВЕРКА|ТЕКСЕРУ|ПРОВЕРКА|МІНДЕТ|ЗАДАЧА|Помни|Есте сақтаңыз|ФОРМАТ|FORMAT)\s*[:\d]*', line.strip(), re.IGNORECASE):
                cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines)

        # Удаляем оставшиеся маркеры, которые могли быть в середине
        final_text = re.sub(r'\*?\*(ЭТАП|ШАГ|КЕЗЕҢ|ҚАДАМ|САМОПРОВЕРКА|ТЕКСЕРУ|ПРОВЕРКА|МІНДЕТ|ЗАДАЧА|Помни|Есте сақтаңыз)[^\\n]*', '', cleaned_text, flags=re.IGNORECASE)
        
        return final_text.strip()

    def generate_detailed_explanation(self, question: str, correct_answer: str, topic: str, language: str = 'ru') -> str:
        """
        Generate detailed explanation for a question and its correct answer.
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
            
            explanation = re.sub(r'^["\']|["\']$', '', explanation)
            explanation = re.sub(r'^\s*[-•]\s*', '', explanation, flags=re.MULTILINE)
            explanation = explanation.strip()
            
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
            if language == 'kk':
                return f"Дұрыс жауап: {correct_answer}. Есепті қадам-қадаммен шешу керек."
            else:
                return f"Правильный ответ: {correct_answer}. Задачу нужно решать пошагово."

    def improve_existing_explanation(self, question: str, correct_answer: str, old_explanation: str, topic: str, language: str = 'ru') -> str:
        """
        Улучшить существующее объяснение, сделав его более понятным для детей.
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
            
            improved_explanation = re.sub(r'^["\']|["\']$', '', improved_explanation)
            improved_explanation = improved_explanation.strip()
            
            if not improved_explanation or len(improved_explanation) < len(old_explanation) * 0.8:
                return old_explanation
            
            return improved_explanation
            
        except Exception as e:
            logging.error(f"Error improving explanation: {e}")
            return old_explanation