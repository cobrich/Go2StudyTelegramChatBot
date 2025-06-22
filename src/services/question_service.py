"""
Question Service

Handles question-related operations and test logic.
"""

import logging
import asyncio
import random
from typing import List, Dict, Any, Set, Optional, Tuple
from src.db.sync_database_facade import get_sync_database_facade
from src.services.ai_service import AIService
from src.config.constants import DEFAULT_QUESTIONS_PER_TEST, MAX_OPTION_LENGTH, get_active_topics
import re

class QuestionService:
    def __init__(self, db=None, ai_service: AIService = None):
        self.db = db if db else get_sync_database_facade()
        self.ai_service = ai_service
        # Флаг для использования нового метода генерации (по умолчанию True - используем новый метод)
        self.use_v3_generation = True

    def enable_v3_generation(self, enable: bool = True):
        """Включает/выключает использование нового метода генерации v3"""
        self.use_v3_generation = enable
        logging.info(f"AI generation method changed to: {'v3 (Meta-prompt)' if enable else 'original'}")

    def _generate_ai_task(self, topic: str, main_topic: str = None, language: str = 'ru'):
        """Генерирует AI задачу используя выбранный метод"""
        if self.use_v3_generation:
            logging.info(f"[_generate_ai_task] Using v3 method for topic: {topic}")
            return self.ai_service.generate_task_v3(topic, main_topic, language)
        else:
            logging.info(f"[_generate_ai_task] Using original method for topic: {topic}")
            return self.ai_service.generate_task(topic, main_topic, language)

    def _validate_ai_question(self, question: str, correct_answer: str, explanation: str, topic: str) -> Tuple[bool, str]:
        """
        Строгая валидация AI-вопросов для предотвращения сохранения некачественных вопросов.
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not question or not correct_answer or not explanation:
            return False, "Пустые обязательные поля"
        
        # Проверка длины полей
        if len(question) < 20 or len(question) > 1000:
            return False, f"Неправильная длина вопроса: {len(question)} символов"
        
        if len(explanation) < 10 or len(explanation) > 2000:
            return False, f"Неправильная длина объяснения: {len(explanation)} символов"
        
        # НОВАЯ ПРОВЕРКА: Соответствие ответа теме
        if not self._validate_answer_topic_consistency(correct_answer, topic):
            return False, f"Ответ '{correct_answer}' не соответствует теме '{topic}'"
        
        # Проверка на признаки ошибок в тексте
        error_indicators = [
            "что-то не так", "ошибка в условии", "задача поставлена некорректно",
            "некорректно", "неправильно", "не могу решить", "невозможно решить",
            "ошибка в задаче", "условие неверно", "задача содержит ошибку"
        ]
        
        explanation_lower = explanation.lower()
        question_lower = question.lower()
        
        for indicator in error_indicators:
            if indicator in explanation_lower or indicator in question_lower:
                return False, f"Обнаружен индикатор ошибки: '{indicator}'"
        
        # Проверка на мета-информацию (ИИ говорит о себе)
        meta_indicators = [
            "как ии", "как искусственный интеллект", "я не могу", "мне нужно",
            "давайте разберем", "рассмотрим", "попробуем решить", "нужно понять"
        ]
        
        for indicator in meta_indicators:
            if indicator in explanation_lower:
                return False, f"Обнаружена мета-информация: '{indicator}'"
        
        # Проверка соответствия ответа и объяснения
        if not self._validate_answer_explanation_consistency(correct_answer, explanation):
            return False, "Ответ не соответствует объяснению"
        
        # Проверка на слишком много предложений (возможно несколько вопросов)
        sentence_count = len([s for s in explanation.split('.') if s.strip()])
        if sentence_count > 10:
            return False, f"Слишком длинное объяснение: {sentence_count} предложений"
        
        return True, ""
    
    def _validate_answer_topic_consistency(self, answer: str, topic: str) -> bool:
        """
        Проверяет соответствие ответа теме.
        
        Returns:
            bool: True если ответ соответствует теме
        """
        import re
        
        topic_lower = topic.lower()
        answer_lower = answer.lower()
        
        # Извлекаем числовые значения из ответа
        number_matches = re.findall(r'-?\d+(?:[.,]\d+)?', answer)
        
        if "натуральн" in topic_lower:
            # Для натуральных чисел ответ должен быть только положительным целым числом
            if number_matches:
                try:
                    for num_str in number_matches:
                        num = float(num_str.replace(',', '.'))
                        # Проверяем что число положительное и целое
                        if num <= 0 or num != int(num):
                            return False
                except ValueError:
                    return False
            # Проверяем что в ответе нет дробей, отрицательных чисел, нуля
            if any(indicator in answer_lower for indicator in ['.', ',', '/', '-', 'ноль', 'нуль']):
                # Исключение для случаев типа "5-6" (диапазон) или "10-15"
                if not re.match(r'^\d+-\d+', answer.strip()):
                    return False
        
        elif "целые" in topic_lower:
            # Для целых чисел ответ должен быть целым (может быть отрицательным или нулем)
            if number_matches:
                try:
                    for num_str in number_matches:
                        num = float(num_str.replace(',', '.'))
                        # Проверяем что число целое
                        if num != int(num):
                            return False
                except ValueError:
                    return False
            # Проверяем что в ответе нет дробей
            if any(indicator in answer_lower for indicator in ['.', ',', '/']):
                return False
        
        elif "обыкновенн" in topic_lower and "дроб" in topic_lower:
            # Для обыкновенных дробей ответ должен содержать дробь или быть целым числом
            has_fraction = '/' in answer
            has_decimal = '.' in answer or ',' in answer
            if has_decimal and not has_fraction:
                return False  # Десятичная дробь недопустима
        
        elif "десятичн" in topic_lower and "дроб" in topic_lower:
            # Для десятичных дробей ответ должен содержать десятичную дробь или быть целым числом
            has_fraction = '/' in answer
            if has_fraction:
                return False  # Обыкновенная дробь недопустима
        
        elif "процент" in topic_lower:
            # Для процентов ответ должен содержать знак % или слово "процент"
            if '%' not in answer and 'процент' not in answer_lower:
                return False
        
        return True

    def _validate_answer_explanation_consistency(self, answer: str, explanation: str) -> bool:
        """
        Проверяет соответствие между ответом и объяснением.
        
        Returns:
            bool: True если ответ соответствует объяснению
        """
        import re
        
        # Извлекаем числовые значения из ответа
        answer_numbers = re.findall(r'-?\d+(?:[.,]\d+)?', answer)
        if not answer_numbers:
            return True  # Если в ответе нет чисел, пропускаем проверку
        
        # Берем первое число из ответа как основное
        try:
            main_answer_num = float(answer_numbers[0].replace(',', '.'))
        except ValueError:
            return True  # Если не можем преобразовать, пропускаем
        
        # Ищем вычисления в объяснении
        calculation_patterns = [
            r'=\s*(-?\d+(?:[.,]\d+)?)',  # = 24, = 26.5
            r'равно\s*(-?\d+(?:[.,]\d+)?)',  # равно 24
            r'составляет\s*(-?\d+(?:[.,]\d+)?)',  # составляет 24
            r'получается\s*(-?\d+(?:[.,]\d+)?)',  # получается 24
            r'итого\s*(-?\d+(?:[.,]\d+)?)',  # итого 24
            r'ответ:?\s*(-?\d+(?:[.,]\d+)?)',  # ответ: 24
        ]
        
        explanation_numbers = []
        for pattern in calculation_patterns:
            matches = re.findall(pattern, explanation, re.IGNORECASE)
            for match in matches:
                try:
                    num = float(match.replace(',', '.'))
                    explanation_numbers.append(num)
                except ValueError:
                    continue
        
        if not explanation_numbers:
            return True  # Если в объяснении нет явных вычислений, пропускаем
        
        # Проверяем, есть ли в объяснении число, соответствующее ответу
        tolerance = 0.01  # Допустимая погрешность
        for exp_num in explanation_numbers:
            if abs(main_answer_num - exp_num) <= tolerance:
                return True
        
        # Если основное число не найдено, проверяем все числа из ответа
        for ans_num_str in answer_numbers:
            try:
                ans_num = float(ans_num_str.replace(',', '.'))
                for exp_num in explanation_numbers:
                    if abs(ans_num - exp_num) <= tolerance:
                        return True
            except ValueError:
                continue
        
        return False  # Ответ не соответствует объяснению

    def cleanup_invalid_ai_questions(self) -> int:
        """
        Очищает базу данных от некачественных AI-вопросов.
        
        Returns:
            int: Количество удаленных вопросов
        """
        logging.info("[cleanup_invalid_ai_questions] Начинаем очистку некачественных AI-вопросов...")
        
        # Получаем все AI-вопросы
        ai_questions = self.db.get_all_ai_questions()
        deleted_count = 0
        
        for question_data in ai_questions:
            question_id = question_data.get('id')
            question = question_data.get('question', '')
            answer = question_data.get('answer', '')
            explanation = question_data.get('explanation', '')
            topic = question_data.get('topic', '')
            
            # Валидируем вопрос
            is_valid, error_msg = self._validate_ai_question(question, answer, explanation, topic)
            
            if not is_valid:
                logging.info(f"[cleanup_invalid_ai_questions] Удаляем некачественный вопрос ID {question_id}: {error_msg}")
                logging.info(f"[cleanup_invalid_ai_questions] Вопрос: {question[:100]}...")
                
                # Удаляем вопрос из базы данных
                self.db.delete_question_by_id(question_id)
                deleted_count += 1
        
        logging.info(f"[cleanup_invalid_ai_questions] Очистка завершена. Удалено {deleted_count} некачественных вопросов.")
        return deleted_count

    def _get_main_topic_for_subtopic(self, subtopic: str) -> tuple[Optional[str], str]:
        """Получить главную тему и язык для подтемы."""
        try:
            return self.db.get_main_topic_and_language_for_subtopic(subtopic)
        except Exception as e:
            logging.error(f"Error getting main topic and language for {subtopic}: {e}")
            return None, 'ru'

    async def get_or_generate_tasks(
        self,
        user_id: int,
        topic: str,
        needed: int = DEFAULT_QUESTIONS_PER_TEST,
        force_ai: bool = False,
        existing_question_texts_to_exclude: Optional[Set[str]] = None,
        is_retake: bool = False
    ) -> List[tuple]:
        """Get tasks for test: сначала ошибки пользователя, потом обычные вопросы, потом ИИ.
        
        Логика для разных типов тестов:
        - Обычный тест: 8 вопросов из БД + 2 ИИ вопроса
        - Пересдача обычного теста: неправильно отвеченные вопросы + похожие ИИ вопросы до 10
        - Рандомный тест: все 10 вопросов из БД (используется RandomTestService)
        """
        logging.info(f"[get_or_generate_tasks] user_id={user_id}, topic={topic}, needed={needed}, is_retake={is_retake}, force_ai={force_ai}")
        if existing_question_texts_to_exclude is None:
            existing_question_texts_to_exclude = set()
        tasks = []
        
        # Получаем главную тему для контекста AI генерации
        main_topic, language = self._get_main_topic_for_subtopic(topic)
        logging.info(f"[get_or_generate_tasks] main_topic for '{topic}': {main_topic}, language: {language}")
        
        if is_retake:
            # ЛОГИКА ПЕРЕСДАЧИ: только ошибки + ИИ вопросы для достижения нужного количества
            logging.info(f"[get_or_generate_tasks] RETAKE MODE for topic '{topic}' with {needed} questions needed")
            
            # 1. Получаем все ошибки пользователя по данной теме
            error_tasks = self.db.get_error_tasks_for_user(user_id, topic, limit=needed)
            logging.info(f"[get_or_generate_tasks] error_tasks found for retake: {len(error_tasks)}")
            
            for task in error_tasks:
                # Проверяем что все основные поля задачи не пустые
                if not task.get('question') or not task.get('answer') or not task.get('explanation'):
                    logging.warning(f"[get_or_generate_tasks] Skipping error_task with empty fields: {task}")
                    continue
                if task['question'] not in existing_question_texts_to_exclude:
                    # Используем готовые варианты ответов из базы данных если они есть
                    if 'all_options' in task and task['all_options']:
                        options = task['all_options']
                    else:
                        # Fallback: формируем варианты из правильного ответа и incorrect_options
                        options = [task['answer']]
                        if task['incorrect_options']:
                            # Убеждаемся, что incorrect_options правильно разбиваются на список
                            if isinstance(task['incorrect_options'], str):
                                incorrect_opts = [opt.strip() for opt in task['incorrect_options'].split('\n') if opt.strip()]
                            else:
                                incorrect_opts = task['incorrect_options'] if isinstance(task['incorrect_options'], list) else []
                            options.extend(incorrect_opts)
                        
                        # Убеждаемся, что options - это список строк
                        options = [str(opt) for opt in options if opt and str(opt).strip()]
                        if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                            options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                    
                    # Перемешиваем варианты
                    random.shuffle(options)
                    tasks.append((
                        task['question'],
                        task['answer'],
                        task['explanation'],
                        options,  # Теперь гарантированно список
                        'db_error',
                        task['image_path'] if 'image_path' in task else None,
                        task.get('id')  # Добавляем question_id
                    ))
                    existing_question_texts_to_exclude.add(task['question'])
                    logging.info(f"[get_or_generate_tasks] Added error_task for retake: {task['question']}")
                else:
                    logging.info(f"[get_or_generate_tasks] Skipped duplicate error_task: {task['question']}")

            # 2. Если ошибок недостаточно до 10, генерируем похожие ИИ вопросы
            if len(tasks) < needed:
                ai_questions_needed = needed - len(tasks)
                logging.info(f"[get_or_generate_tasks] Need {ai_questions_needed} more AI questions for retake to reach {needed}")
                
                # Генерируем ИИ вопросы с контекстом "пересдача" для более похожих вопросов
                new_tasks = []
                loop = asyncio.get_running_loop()
                
                # Увеличиваем количество попыток для лучшего качества в пересдаче
                max_attempts = ai_questions_needed * 3
                generation_tasks = [
                    loop.run_in_executor(None, self._generate_ai_task, topic, main_topic, language)
                    for _ in range(max_attempts)
                ]
                results = await asyncio.gather(*generation_tasks, return_exceptions=True)
                
                valid_questions = 0
                for result in results:
                    if valid_questions >= ai_questions_needed:
                        break
                        
                    if isinstance(result, Exception):
                        logging.error(f"[get_or_generate_tasks][RETAKE AI] Error generating task: {result}")
                        continue
                    if result:
                        question, correct_answer, incorrect_options, explanation = result
                        if not question or not correct_answer or not explanation:
                            continue
                        
                        # Более мягкая валидация для пересдачи - важно дать достаточно вопросов
                        if question not in existing_question_texts_to_exclude:
                            # Сохраняем сгенерированный ИИ вопрос в базу
                            if not self.db.get_explanation_by_question_text(question):
                                if question and correct_answer and explanation:
                                    self.db.add_question({
                                        'topic': topic,
                                        'question': question,
                                        'answer': correct_answer,
                                        'explanation': explanation,
                                        'incorrect_options': '\n'.join(incorrect_options) if isinstance(incorrect_options, list) else (incorrect_options or ''),
                                        'question_type': 'standard',
                                        'source': 'ai_retake'
                                    })
                                    logging.info(f"[get_or_generate_tasks][RETAKE AI] Saved new AI question to DB: {question}")
                            
                            # Формируем варианты ответов
                            options = [correct_answer]
                            if incorrect_options:
                                if isinstance(incorrect_options, list):
                                    options.extend([opt for opt in incorrect_options if opt and str(opt).strip()])
                                elif isinstance(incorrect_options, str):
                                    options.extend([opt.strip() for opt in incorrect_options.split('\n') if opt.strip()])
                            
                            options = [str(opt) for opt in options if opt and str(opt).strip()]
                            if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                                options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                            
                            if correct_answer not in options:
                                options.append(correct_answer)
                            options = list(dict.fromkeys(options))  # remove duplicates, preserve order
                            
                            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ФОРМИРОВАНИЯ ВАРИАНТОВ
                            logging.info(f"🔍 [AI ВОПРОС] Формирование вариантов для: {question[:50]}...")
                            logging.info(f"  ✅ Правильный ответ: '{correct_answer}' (тип: {type(correct_answer)})")
                            logging.info(f"  ❌ Неправильные варианты: {incorrect_options}")
                            logging.info(f"  📋 Финальные варианты ДО перемешивания: {options}")
                            
                            random.shuffle(options)
                            
                            logging.info(f"  🔄 Финальные варианты ПОСЛЕ перемешивания: {options}")
                            logging.info(f"  🎯 Правильный ответ остался: '{correct_answer}' в позиции {options.index(correct_answer) if correct_answer in options else 'НЕ НАЙДЕН!'}")
                            
                            new_tasks.append((
                                question,
                                correct_answer,
                                explanation,
                                options,  # Теперь гарантированно список
                                'ai_retake',
                                None
                            ))
                            existing_question_texts_to_exclude.add(question)
                            valid_questions += 1
                            logging.info(f"[get_or_generate_tasks][RETAKE AI] Added AI question {valid_questions}/{ai_questions_needed}: {question}")
                
                tasks.extend(new_tasks)
                logging.info(f"[get_or_generate_tasks] RETAKE FINAL: {len(tasks)} total questions ({len(tasks) - len(new_tasks)} errors + {len(new_tasks)} AI)")
        else:
            # ЛОГИКА ОБЫЧНОГО ТЕСТА: 8 из БД + 2 ИИ
            min_ai_questions = 2
            max_db_questions = max(0, needed - min_ai_questions)  # Максимум вопросов из БД
            logging.info(f"[get_or_generate_tasks] NORMAL MODE: Will generate {min_ai_questions} AI questions minimum, max {max_db_questions} from DB")
            
            # 1. Сначала ошибки пользователя (ограничиваем чтобы оставить место для ИИ)
            error_tasks = self.db.get_error_tasks_for_user(user_id, topic, limit=max_db_questions)
            logging.info(f"[get_or_generate_tasks] error_tasks found: {len(error_tasks)}")
            
            for task in error_tasks:
                # Проверяем что все основные поля задачи не пустые
                if not task.get('question') or not task.get('answer') or not task.get('explanation'):
                    logging.warning(f"[get_or_generate_tasks] Skipping error_task with empty fields: {task}")
                    continue
                if task['question'] not in existing_question_texts_to_exclude:
                    # Используем готовые варианты ответов из базы данных если они есть
                    if 'all_options' in task and task['all_options']:
                        options = task['all_options']
                    else:
                        # Fallback: формируем варианты из правильного ответа и incorrect_options
                        options = [task['answer']]
                        if task['incorrect_options']:
                            # Убеждаемся, что incorrect_options правильно разбиваются на список
                            if isinstance(task['incorrect_options'], str):
                                incorrect_opts = [opt.strip() for opt in task['incorrect_options'].split('\n') if opt.strip()]
                            else:
                                incorrect_opts = task['incorrect_options'] if isinstance(task['incorrect_options'], list) else []
                            options.extend(incorrect_opts)
                        
                        # Убеждаемся, что options - это список строк
                        options = [str(opt) for opt in options if opt and str(opt).strip()]
                        if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                            options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                    
                    # Перемешиваем варианты
                    random.shuffle(options)
                    tasks.append((
                        task['question'],
                        task['answer'],
                        task['explanation'],
                        options,  # Теперь гарантированно список
                        'db',
                        task['image_path'] if 'image_path' in task else None,
                        task.get('id')  # Добавляем question_id
                    ))
                    existing_question_texts_to_exclude.add(task['question'])
                    logging.info(f"[get_or_generate_tasks] Added error_task: {task['question']}")
                    
                    # Останавливаемся если достигли лимита DB вопросов
                    if len(tasks) >= max_db_questions:
                        logging.info(f"[get_or_generate_tasks] Reached max DB questions limit: {max_db_questions}")
                        break
                else:
                    logging.info(f"[get_or_generate_tasks] Skipped duplicate error_task: {task['question']}")

            logging.info(f"[get_or_generate_tasks] Total error_tasks added: {len(tasks)}")

            # 2. Обычные вопросы из базы (только если не достигли лимита DB вопросов)
            if len(tasks) < max_db_questions:
                remaining_db_slots = max_db_questions - len(tasks)
                db_tasks_pool_raw = self.db.get_tasks_for_topic(topic, limit=remaining_db_slots * 2)
                logging.info(f"[get_or_generate_tasks] db_tasks_pool_raw found: {len(db_tasks_pool_raw)}, remaining_db_slots: {remaining_db_slots}")
                for task in db_tasks_pool_raw:
                    # Проверяем что все основные поля задачи не пустые
                    if not task.get('question') or not task.get('answer') or not task.get('explanation'):
                        logging.warning(f"[get_or_generate_tasks] Skipping db_task with empty fields: {task}")
                        continue
                    
                    if task['question'] not in existing_question_texts_to_exclude:
                        # Используем готовые варианты ответов из базы данных если они есть
                        if 'all_options' in task and task['all_options']:
                            options = task['all_options']
                        else:
                            # Fallback: формируем варианты из правильного ответа и incorrect_options
                            options = [task['answer']]
                            if task['incorrect_options']:
                                # Убеждаемся, что incorrect_options правильно разбиваются на список
                                if isinstance(task['incorrect_options'], str):
                                    incorrect_opts = [opt.strip() for opt in task['incorrect_options'].split('\n') if opt.strip()]
                                else:
                                    incorrect_opts = task['incorrect_options'] if isinstance(task['incorrect_options'], list) else []
                                options.extend(incorrect_opts)
                            
                            # Убеждаемся, что options - это список строк
                            options = [str(opt) for opt in options if opt and str(opt).strip()]
                            
                            # КРИТИЧЕСКИ ВАЖНО: Гарантируем наличие правильного ответа в вариантах
                            if task['answer'] not in options:
                                options.append(task['answer'])
                            
                            # Если вариантов мало, добавляем фиктивные
                            if len(options) < 4:
                                options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                            
                            # Удаляем дубликаты, сохраняя порядок
                            options = list(dict.fromkeys(options))
                        
                        # Перемешиваем варианты
                        random.shuffle(options)
                        tasks.append((
                            task['question'],
                            task['answer'],
                            task['explanation'],
                            options,  # Теперь гарантированно список
                            task.get('source', 'db'),
                            task['image_path'] if 'image_path' in task else None,
                            task.get('id')  # Добавляем question_id
                        ))
                        existing_question_texts_to_exclude.add(task['question'])
                        logging.info(f"[get_or_generate_tasks] Added db_task: {task['question']}")
                                
                        # Останавливаемся если достигли лимита DB вопросов
                        if len(tasks) >= max_db_questions:
                            logging.info(f"[get_or_generate_tasks] Reached max DB questions limit: {max_db_questions}")
                            break
                    else:
                        # Если вопрос уже есть в исключениях, пропускаем его
                        logging.info(f"[get_or_generate_tasks] Skipped duplicate db_task: {task['question']}")

            # 3. ОБЯЗАТЕЛЬНАЯ генерация ИИ вопросов (минимум min_ai_questions)
            ai_questions_needed = needed - len(tasks)
            ai_questions_to_generate = max(min_ai_questions, ai_questions_needed)  # Минимум 2, но может быть больше если нужно
            
            logging.info(f"[get_or_generate_tasks] Current tasks: {len(tasks)}, AI questions needed: {ai_questions_needed}, will generate: {ai_questions_to_generate}")
            
            new_tasks = []
            loop = asyncio.get_running_loop()
            
            # ИСПРАВЛЕНИЕ: Убираем ограничения и генерируем до достижения нужного количества
            valid_questions = 0
            attempt_batch = 1
            max_batches = 10  # Максимум батчей для предотвращения бесконечного цикла
            
            while valid_questions < ai_questions_to_generate and attempt_batch <= max_batches:
                # Генерируем батч вопросов
                remaining_needed = ai_questions_to_generate - valid_questions
                batch_size = min(remaining_needed * 3, 20)  # Генерируем с запасом, но не слишком много за раз
                
                logging.info(f"[get_or_generate_tasks] AI generation batch {attempt_batch}: need {remaining_needed} more questions, generating {batch_size} attempts")
                
                generation_tasks = [
                    loop.run_in_executor(None, self._generate_ai_task, topic, main_topic, language)
                    for _ in range(batch_size)
                ]
                results = await asyncio.gather(*generation_tasks, return_exceptions=True)
                
                batch_valid_count = 0
                for result in results:
                    # Прерываем если уже набрали нужное количество
                    if valid_questions >= ai_questions_to_generate:
                        break
                        
                    if isinstance(result, Exception):
                        logging.error(f"[get_or_generate_tasks][AI generation] Error generating task: {result}")
                        continue
                    if result:
                        question, correct_answer, incorrect_options, explanation = result
                        if not question or not correct_answer or not explanation:
                            logging.warning(f"[get_or_generate_tasks][AI generation] Skipping result with None fields: question={question is not None}, answer={correct_answer is not None}, explanation={explanation is not None}")
                            continue
                        
                        # Проверяем валидность вопроса
                        is_valid, error_msg = self._validate_ai_question(question, correct_answer, explanation, topic)
                        if not is_valid:
                            # Мягкая валидация - принимаем сомнительные вопросы если их не хватает
                            if valid_questions < min_ai_questions or attempt_batch >= max_batches - 1:
                                logging.warning(f"[get_or_generate_tasks][AI generation] Soft validation: accepting questionable AI question due to shortage: {error_msg}. Question: {question[:100]}...")
                            else:
                                logging.warning(f"[get_or_generate_tasks][AI generation] Skipping invalid AI question: {error_msg}. Question: {question[:100]}...")
                                continue
                        
                        if question not in existing_question_texts_to_exclude:
                            # Сохраняем сгенерированный ИИ вопрос в базу
                            if not self.db.get_explanation_by_question_text(question):
                                if question and correct_answer and explanation:
                                    self.db.add_question({
                                        'topic': topic,
                                        'question': question,
                                        'answer': correct_answer,
                                        'explanation': explanation,
                                        'incorrect_options': '\n'.join(incorrect_options) if isinstance(incorrect_options, list) else (incorrect_options or ''),
                                        'question_type': 'standard',
                                        'source': 'ai'
                                    })
                                    logging.info(f"[get_or_generate_tasks][AI generation] Saved new AI question to DB: {question}")
                                else:
                                    logging.warning(f"[get_or_generate_tasks][AI generation] Skipping question with NULL fields: question={question}, answer={correct_answer}, explanation={explanation}")
                                    continue
                            
                            # Формируем варианты ответов
                            options = [correct_answer]
                            if incorrect_options:
                                if isinstance(incorrect_options, list):
                                    options.extend([opt for opt in incorrect_options if opt and str(opt).strip()])
                                elif isinstance(incorrect_options, str):
                                    options.extend([opt.strip() for opt in incorrect_options.split('\n') if opt.strip()])
                            
                            options = [str(opt) for opt in options if opt and str(opt).strip()]
                            if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                                options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                            
                            if correct_answer not in options:
                                options.append(correct_answer)
                            options = list(dict.fromkeys(options))  # remove duplicates, preserve order
                            
                            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ФОРМИРОВАНИЯ ВАРИАНТОВ
                            logging.info(f"🔍 [AI ВОПРОС] Формирование вариантов для: {question[:50]}...")
                            logging.info(f"  ✅ Правильный ответ: '{correct_answer}' (тип: {type(correct_answer)})")
                            logging.info(f"  ❌ Неправильные варианты: {incorrect_options}")
                            logging.info(f"  📋 Финальные варианты ДО перемешивания: {options}")
                            
                            random.shuffle(options)
                            
                            logging.info(f"  🔄 Финальные варианты ПОСЛЕ перемешивания: {options}")
                            logging.info(f"  🎯 Правильный ответ остался: '{correct_answer}' в позиции {options.index(correct_answer) if correct_answer in options else 'НЕ НАЙДЕН!'}")
                            
                            new_tasks.append((
                                question,
                                correct_answer,
                                explanation,
                                options,  # Теперь гарантированно список
                                'ai',
                                None
                            ))
                            existing_question_texts_to_exclude.add(question)
                            valid_questions += 1
                            batch_valid_count += 1
                            logging.info(f"[get_or_generate_tasks][AI generation] Added AI question {valid_questions}/{ai_questions_to_generate}: {question}")
                        else:
                            logging.info(f"[get_or_generate_tasks][AI generation] Skipped duplicate AI question: {question}")
                    else:
                        logging.warning(f"[get_or_generate_tasks][AI generation] Skipping empty or invalid result: {result}")
                
                logging.info(f"[get_or_generate_tasks] Batch {attempt_batch} completed: got {batch_valid_count} valid questions, total: {valid_questions}/{ai_questions_to_generate}")
                attempt_batch += 1
            
            if valid_questions < ai_questions_to_generate:
                logging.warning(f"[get_or_generate_tasks] Could only generate {valid_questions} AI questions out of {ai_questions_to_generate} needed after {max_batches} batches")
            else:
                logging.info(f"[get_or_generate_tasks] Successfully generated {valid_questions} AI questions")
            
            tasks.extend(new_tasks)
        
        # Filter out any None values from all_tasks before logging and returning
        tasks = [task for task in tasks if task is not None and len(task) >= 5]
        logging.info(f"[get_or_generate_tasks] Total tasks after all stages: {len(tasks)}")
        
        # Если у нас больше вопросов чем нужно, возвращаем нужное количество
        if len(tasks) > needed:
            if is_retake:
                # Для пересдачи: сначала ошибки, потом ИИ
                error_tasks = [task for task in tasks if task[4] in ['db_error', 'db']]
                ai_tasks = [task for task in tasks if task[4] in ['ai_retake', 'ai']]
                
                final_tasks = error_tasks[:needed]  # Берем сначала ошибки
                if len(final_tasks) < needed:
                    remaining_slots = needed - len(final_tasks)
                    final_tasks.extend(ai_tasks[:remaining_slots])  # Добавляем ИИ
            else:
                # Для обычного теста: убеждаемся что в финальном списке есть минимум ИИ вопросов
                ai_tasks = [task for task in tasks if task[4] == 'ai']
                db_tasks = [task for task in tasks if task[4] != 'ai']
                
                # Берем все ИИ вопросы (но не больше needed)
                final_ai_tasks = ai_tasks[:needed]
                # Дополняем DB вопросами если нужно
                remaining_slots = needed - len(final_ai_tasks)
                final_db_tasks = db_tasks[:remaining_slots] if remaining_slots > 0 else []
                
                final_tasks = final_ai_tasks + final_db_tasks
            
            random.shuffle(final_tasks)  # Перемешиваем для случайного порядка
            logging.info(f"[get_or_generate_tasks] Final composition: {len(final_tasks)} total")
            return final_tasks
        
        if len(tasks) < needed:
            logging.warning(f"[get_or_generate_tasks] Could only generate {len(tasks)} tasks out of {needed} needed.")
        
        # Лог финального списка вопросов - только после фильтрации
        ai_count = sum(1 for q in tasks if q[4] in ['ai', 'ai_retake'])
        db_count = len(tasks) - ai_count
        test_type = "RETAKE" if is_retake else "NORMAL"
        logging.info(f"[get_or_generate_tasks] {test_type} Final result: {ai_count} AI questions, {db_count} DB questions")
        for idx, q in enumerate(tasks[:needed]):
            if q is not None and len(q) >= 5:
                logging.info(f"[get_or_generate_tasks] Final task {idx+1}: {q[0][:80]}... (source: {q[4]})")
            else:
                logging.warning(f"[get_or_generate_tasks] Invalid task at index {idx}: {q}")
        return tasks[:needed]

    @staticmethod
    def generate_universal_options(correct_answer_str: str) -> List[str]:
        """Generate universal options for a given correct answer."""
        correct_answer_str = str(correct_answer_str).strip()
        options = set()
        
        if len(correct_answer_str) <= MAX_OPTION_LENGTH:
            options.add(correct_answer_str)

        num_match = re.match(r"^(-?\d+([.,]\d+)?)\s*(.*)$", correct_answer_str.strip())
        generated_numeric_options = False

        if num_match:
            num_val_str = num_match.group(1)
            unit = num_match.group(3).strip()
            try:
                num_val = float(num_val_str.replace(',', '.'))
                is_int_val = num_val == int(num_val)
                if is_int_val:
                    num_val = int(num_val)
                possible_distractors = set()
                
                for i in range(15):
                    if len(options) + len(possible_distractors) >= 4 and i > 5:
                        break
                    op_choice = random.choice([-1, 1, -2, 2, 3, 4])
                    if op_choice == 1:
                        delta_abs = max(1, abs(num_val) * random.uniform(0.1, 0.5))
                        dist_candidate_val = num_val + delta_abs * (1 + random.random())
                    elif op_choice == -1:
                        delta_abs = max(1, abs(num_val) * random.uniform(0.1, 0.5))
                        dist_candidate_val = num_val - delta_abs * (1 + random.random())
                    elif op_choice == 2 and num_val != 0:
                        factor = random.choice([0.5, 1.5, 2, 0.75, 1.25, 1.75])
                        dist_candidate_val = num_val * factor
                    elif op_choice == -2 and num_val != 0:
                        factor = random.choice([2, 3, 4, 1.5])
                        dist_candidate_val = num_val / factor
                    elif op_choice == 3:
                        dist_candidate_val = num_val * (1 + random.uniform(0.1, 0.3))
                    else:
                        dist_candidate_val = num_val * (1 - random.uniform(0.1, 0.3))
                    
                    if is_int_val:
                        dist_candidate_val = round(dist_candidate_val)
                    else:
                        dist_candidate_val = round(dist_candidate_val, 2)
                    
                    if num_val > 0 and dist_candidate_val <= 0:
                        if num_val > 1 and is_int_val:
                            dist_candidate_val = max(1, round(num_val * random.uniform(0.1, 0.5)))
                        elif not is_int_val and num_val > 0.01:
                            dist_candidate_val = round(max(0.01, num_val * random.uniform(0.1, 0.5)), 2)
                        else:
                            dist_candidate_val = abs(dist_candidate_val) + (1 if is_int_val else 0.01)
                    
                    if unit:
                        option_str = f"{dist_candidate_val} {unit}".strip()
                    else:
                        option_str = str(dist_candidate_val)
                    
                    if option_str != correct_answer_str and len(option_str) <= MAX_OPTION_LENGTH:
                        possible_distractors.add(option_str)
                
                for distractor in list(possible_distractors):
                    if len(options) < 4:
                        options.add(distractor)
                    else:
                        break
                
                if len(options) > 1:
                    generated_numeric_options = True
                    
            except ValueError:
                pass

        if not generated_numeric_options or len(options) < 4:
            if len(correct_answer_str) > 0:
                base_options = set()
                for _ in range(10):
                    if len(base_options) >= 3:
                        break
                    if random.random() < 0.5:
                        words = correct_answer_str.split()
                        if len(words) > 1:
                            random.shuffle(words)
                            modified = ' '.join(words)
                            if modified != correct_answer_str and len(modified) <= MAX_OPTION_LENGTH:
                                base_options.add(modified)
                    else:
                        if len(correct_answer_str) > 3:
                            pos = random.randint(0, len(correct_answer_str) - 1)
                            modified = correct_answer_str[:pos] + correct_answer_str[pos + 1:]
                            if modified != correct_answer_str and len(modified) <= MAX_OPTION_LENGTH:
                                base_options.add(modified)
                
                for option in base_options:
                    if len(options) < 4:
                        options.add(option)

        final_options_list = list(options)
        if len(final_options_list) < 2:
            return []
        
        if correct_answer_str not in final_options_list and len(correct_answer_str) <= MAX_OPTION_LENGTH:
            if len(final_options_list) < 4:
                final_options_list.append(correct_answer_str)
        
        random.shuffle(final_options_list)
        return final_options_list[:4] 