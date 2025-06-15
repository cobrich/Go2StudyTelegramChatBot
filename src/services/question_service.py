import logging
import asyncio
import random
from typing import List, Dict, Any, Set, Optional, Tuple
from services.database import Database
from services.ai_service import AIService
from config.constants import DEFAULT_QUESTIONS_PER_TEST, MAX_OPTION_LENGTH
import re

class QuestionService:
    def __init__(self, db: Database, ai_service: AIService):
        self.db = db
        self.ai_service = ai_service

    def _validate_ai_question(self, question: str, correct_answer: str, explanation: str, topic: str) -> Tuple[bool, str]:
        """
        Строгая валидация AI-вопросов для предотвращения сохранения некачественных вопросов.
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not question or not correct_answer or not explanation:
            return False, "Пустые обязательные поля"
        
        # 1. Проверка длины полей
        if len(question) < 20:
            return False, "Вопрос слишком короткий (менее 20 символов)"
        
        if len(question) > 1000:
            return False, "Вопрос слишком длинный (более 1000 символов)"
        
        if len(explanation) < 10:
            return False, "Объяснение слишком короткое (менее 10 символов)"
        
        # 2. Проверка на признаки ошибок в объяснении
        error_indicators = [
            "что-то не так",
            "ошибка в условии",
            "задача поставлена некорректно",
            "снова ошибка",
            "нужно изменить условие",
            "противоречие",
            "новый вопрос:",
            "правильный ответ:",
            "неправильный ответ",
            "объяснение:"
        ]
        
        explanation_lower = explanation.lower()
        for indicator in error_indicators:
            if indicator in explanation_lower:
                return False, f"Объяснение содержит признак ошибки: '{indicator}'"
        
        # 3. Проверка на слишком длинное объяснение (возможно содержит несколько задач)
        if len(explanation) > 2000:
            return False, "Объяснение слишком длинное (возможно содержит несколько задач)"
        
        # 4. Проверка на соответствие вопроса и ответа
        question_lower = question.lower()
        answer_lower = correct_answer.lower()
        
        # Проверяем, что вопрос и ответ логически связаны
        if "сколько" in question_lower and not any(char.isdigit() for char in correct_answer):
            # Если вопрос спрашивает "сколько", ответ должен содержать число
            if not re.search(r'\d+', correct_answer):
                return False, "Вопрос спрашивает количество, но ответ не содержит чисел"
        
        # 5. Проверка на противоречия в тексте
        if "экономи" in question_lower and ("не получится" in explanation_lower or "экономии не было" in explanation_lower):
            return False, "Противоречие: вопрос об экономии, но объяснение говорит об отсутствии экономии"
        
        # 6. Проверка на дублирование контента в объяснении
        sentences = explanation.split('.')
        if len(sentences) > 10:  # Слишком много предложений может указывать на проблему
            return False, "Объяснение содержит слишком много предложений (возможно несколько задач)"
        
        # 7. Проверка на наличие мета-информации в объяснении
        meta_indicators = [
            "правильный ответ:",
            "неправильный ответ",
            "вариант ответа",
            "ответ 1:",
            "ответ 2:",
            "ответ 3:"
        ]
        
        for indicator in meta_indicators:
            if indicator in explanation_lower:
                return False, f"Объяснение содержит мета-информацию: '{indicator}'"
        
        return True, ""

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
        """Get tasks for test: сначала ошибки пользователя, потом обычные вопросы, потом ИИ."""
        logging.info(f"[get_or_generate_tasks] user_id={user_id}, topic={topic}, needed={needed}, is_retake={is_retake}, force_ai={force_ai}")
        if existing_question_texts_to_exclude is None:
            existing_question_texts_to_exclude = set()
        tasks = []
        
        # Получаем главную тему для контекста AI генерации
        main_topic, language = self._get_main_topic_for_subtopic(topic)
        logging.info(f"[get_or_generate_tasks] main_topic for '{topic}': {main_topic}, language: {language}")
        
        # 1. Сначала ошибки пользователя
        error_tasks = self.db.get_error_tasks_for_user(user_id, topic, limit=needed)
        logging.info(f"[get_or_generate_tasks] error_tasks found: {len(error_tasks)}")
        error_questions = []
        for task in error_tasks:
            # Проверяем что все основные поля задачи не пустые
            if not task.get('question') or not task.get('answer') or not task.get('explanation'):
                logging.warning(f"[get_or_generate_tasks] Skipping error_task with empty fields: {task}")
                continue
            if task['question'] not in existing_question_texts_to_exclude:
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
                
                random.shuffle(options)
                tasks.append((
                    task['question'],
                    task['answer'],
                    task['explanation'],
                    options,  # Теперь гарантированно список
                    'db',
                    task['image_path'] if 'image_path' in task else None
                ))
                error_questions.append(task['question'])  # Add to error questions list
                existing_question_texts_to_exclude.add(task['question'])
                logging.info(f"[get_or_generate_tasks] Added error_task: {task['question']}")
            else:
                logging.info(f"[get_or_generate_tasks] Skipped duplicate error_task: {task['question']}")

        logging.info(f"[get_or_generate_tasks] Total error_tasks added: {len(tasks)}")

        # If this is a retake and we have some error tasks, generate additional questions to reach needed count
        if is_retake and error_questions:
            remaining = needed - len(tasks)
            logging.info(f"[get_or_generate_tasks][retake] Need to generate {remaining} AI questions based on errors")
            if remaining > 0:
                new_tasks = []
                loop = asyncio.get_running_loop()
                # Generate questions similar to error questions
                generation_tasks = []
                for error_question in error_questions:
                    if len(generation_tasks) >= remaining:
                        break
                    logging.info(f"[get_or_generate_tasks][retake] Scheduling AI generation for error_question: {error_question}")
                    generation_tasks.append(
                        loop.run_in_executor(
                            None,
                            self.ai_service.generate_similar_task,
                            topic,
                            error_question,
                            main_topic,
                            language
                        )
                    )
                # If we still need more questions, generate regular ones
                if len(generation_tasks) < remaining:
                    logging.info(f"[get_or_generate_tasks][retake] Not enough error_questions, scheduling {remaining - len(generation_tasks)} regular AI generations")
                    generation_tasks.extend([
                        loop.run_in_executor(None, self.ai_service.generate_task, topic, main_topic, language)
                        for _ in range(remaining - len(generation_tasks))
                    ])
                results = await asyncio.gather(*generation_tasks, return_exceptions=True)
                for result in results:
                    logging.info(f"[get_or_generate_tasks][retake][AI generation result]: {result}")
                    if isinstance(result, Exception):
                        logging.error(f"[get_or_generate_tasks][retake][AI generation] Error generating task: {result}")
                        continue
                    if result and len(result) >= 4:
                        question, correct_answer, incorrect_options, explanation = result
                        # Дополнительная проверка что все основные поля не None
                        if not question or not correct_answer or not explanation:
                            logging.warning(f"[get_or_generate_tasks][retake][AI generation] Skipping result with None fields: question={question}, answer={correct_answer}, explanation={explanation}")
                            continue
                        
                        # Строгая валидация AI-вопроса
                        is_valid, error_msg = self._validate_ai_question(question, correct_answer, explanation, topic)
                        if not is_valid:
                            logging.warning(f"[get_or_generate_tasks][retake][AI generation] Skipping invalid AI question: {error_msg}. Question: {question[:100]}...")
                            continue
                        
                        if question not in existing_question_texts_to_exclude:
                            # Сохраняем сгенерированный ИИ вопрос в базу, если его там нет
                            if not self.db.get_explanation_by_question_text(question):
                                # Validate that all required fields are not None/empty
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
                                    logging.info(f"[get_or_generate_tasks][retake][AI generation] Saved new AI question to DB: {question}")
                                else:
                                    logging.warning(f"[get_or_generate_tasks][retake][AI generation] Skipping question with NULL fields: question={question}, answer={correct_answer}, explanation={explanation}")
                            # Формируем варианты: правильный + неправильные, гарантируем наличие правильного
                            options = [correct_answer]
                            if incorrect_options:
                                if isinstance(incorrect_options, list):
                                    options.extend([opt for opt in incorrect_options if opt and str(opt).strip()])
                                elif isinstance(incorrect_options, str):
                                    options.extend([opt.strip() for opt in incorrect_options.split('\n') if opt.strip()])
                            
                            # Убеждаемся, что options - это список строк
                            options = [str(opt) for opt in options if opt and str(opt).strip()]
                            if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                                options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                            
                            if correct_answer not in options:
                                options.append(correct_answer)
                            options = list(dict.fromkeys(options))  # remove duplicates, preserve order
                            random.shuffle(options)
                            new_tasks.append((
                                question,
                                correct_answer,
                                explanation,
                                options,  # Теперь гарантированно список
                                'ai',
                                None
                            ))
                            existing_question_texts_to_exclude.add(question)
                            logging.info(f"[get_or_generate_tasks][retake][AI generation] Added AI question: {question}")
                        else:
                            logging.warning(f"[get_or_generate_tasks][retake][AI generation] Unexpected result format: {result}")
                logging.info(f"[get_or_generate_tasks][retake][AI generation] Total new AI tasks added: {len(new_tasks)}")
                tasks.extend(new_tasks)
                if len(tasks) >= needed:
                    logging.info(f"[get_or_generate_tasks][retake] Returning {len(tasks)} tasks (errors + AI)")
                    return tasks[:needed]

        # 2. Обычные вопросы из базы (только если это не ретейк или нет ошибок)
        if not is_retake or not tasks:
            db_tasks_pool_raw = self.db.get_tasks_for_topic(topic, limit=needed * 2)
            logging.info(f"[get_or_generate_tasks] db_tasks_pool_raw found: {len(db_tasks_pool_raw)}")
            for task in db_tasks_pool_raw:
                # Проверяем что все основные поля задачи не пустые
                if not task.get('question') or not task.get('answer') or not task.get('explanation'):
                    logging.warning(f"[get_or_generate_tasks] Skipping db_task with empty fields: {task}")
                    continue
                if task['question'] not in existing_question_texts_to_exclude:
                    options = []
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
                    
                    # КРИТИЧЕСКИ ВАЖНО: Гарантируем наличие правильного ответа в вариантах
                    if task['answer'] not in options:
                        options.append(task['answer'])
                    
                    # Удаляем дубликаты, сохраняя порядок
                    options = list(dict.fromkeys(options))
                    random.shuffle(options)
                    tasks.append((
                        task['question'],
                        task['answer'],
                        task['explanation'],
                        options,  # Теперь гарантированно список
                        task.get('source', 'db'),
                        task['image_path'] if 'image_path' in task else None
                    ))
                    existing_question_texts_to_exclude.add(task['question'])
                    logging.info(f"[get_or_generate_tasks] Added db_task: {task['question']}")
                    if len(tasks) >= needed:
                        logging.info(f"[get_or_generate_tasks] Returning {len(tasks)} tasks (errors + db)")
                        return tasks[:needed]
                else:
                    logging.info(f"[get_or_generate_tasks] Skipped duplicate db_task: {task['question']}")

        # 3. Генерация новых вопросов
        remaining = needed - len(tasks)
        logging.info(f"[get_or_generate_tasks] Need to generate {remaining} new AI questions (final stage)")
        new_tasks = []
        loop = asyncio.get_running_loop()
        generation_tasks = [
            loop.run_in_executor(None, self.ai_service.generate_task, topic, main_topic, language)
            for _ in range(remaining)
        ]
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        for result in results:
            logging.info(f"[get_or_generate_tasks][final AI generation result]: {result}")
            if isinstance(result, Exception):
                logging.error(f"[get_or_generate_tasks][final AI generation] Error generating task: {result}")
                continue
            if result:
                question, correct_answer, incorrect_options, explanation = result
                # Дополнительная проверка что все основные поля не None
                if not question or not correct_answer or not explanation:
                    logging.warning(f"[get_or_generate_tasks][final AI generation] Skipping result with None fields: question={question}, answer={correct_answer}, explanation={explanation}")
                    continue
                
                # Строгая валидация AI-вопроса
                is_valid, error_msg = self._validate_ai_question(question, correct_answer, explanation, topic)
                if not is_valid:
                    logging.warning(f"[get_or_generate_tasks][final AI generation] Skipping invalid AI question: {error_msg}. Question: {question[:100]}...")
                    continue
                
                if question not in existing_question_texts_to_exclude:
                    # Сохраняем сгенерированный ИИ вопрос в базу, если его там нет
                    if not self.db.get_explanation_by_question_text(question):
                        # Validate that all required fields are not None/empty
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
                            logging.info(f"[get_or_generate_tasks][final AI generation] Saved new AI question to DB: {question}")
                        else:
                            logging.warning(f"[get_or_generate_tasks][final AI generation] Skipping question with NULL fields: question={question}, answer={correct_answer}, explanation={explanation}")
                    # Формируем варианты: правильный + неправильные, гарантируем наличие правильного
                    options = [correct_answer]
                    if incorrect_options:
                        if isinstance(incorrect_options, list):
                            options.extend([opt for opt in incorrect_options if opt and str(opt).strip()])
                        elif isinstance(incorrect_options, str):
                            options.extend([opt.strip() for opt in incorrect_options.split('\n') if opt.strip()])
                    
                    # Убеждаемся, что options - это список строк
                    options = [str(opt) for opt in options if opt and str(opt).strip()]
                    if len(options) < 2:  # Добавляем фиктивные варианты если их мало
                        options.extend([f"Вариант {i}" for i in range(len(options), 4)])
                    
                    if correct_answer not in options:
                        options.append(correct_answer)
                    options = list(dict.fromkeys(options))  # remove duplicates, preserve order
                    random.shuffle(options)
                    new_tasks.append((
                        question,
                        correct_answer,
                        explanation,
                        options,  # Теперь гарантированно список
                        'ai',
                        None
                    ))
                    existing_question_texts_to_exclude.add(question)
                    logging.info(f"[get_or_generate_tasks][final AI generation] Added AI question: {question}")
                else:
                    logging.info(f"[get_or_generate_tasks][final AI generation] Skipped duplicate AI question: {question}")
            else:
                logging.warning(f"[get_or_generate_tasks][final AI generation] Skipping empty or invalid result: {result}")
        all_tasks = tasks + new_tasks
        # Filter out any None values from all_tasks before logging and returning
        all_tasks = [task for task in all_tasks if task is not None and len(task) >= 5]
        logging.info(f"[get_or_generate_tasks] Total tasks after all stages: {len(all_tasks)}")
        if len(all_tasks) < needed:
            logging.warning(f"[get_or_generate_tasks] Could only generate {len(all_tasks)} tasks out of {needed} needed.")
            # Возвращаем то, что удалось сгенерировать, вместо рекурсивного вызова
            return all_tasks
        # Лог финального списка вопросов - только после фильтрации
        for idx, q in enumerate(all_tasks[:needed]):
            if q is not None and len(q) >= 5:
                logging.info(f"[get_or_generate_tasks] Final task {idx+1}: {q[0][:80]}... (source: {q[4]})")
            else:
                logging.warning(f"[get_or_generate_tasks] Invalid task at index {idx}: {q}")
        return all_tasks[:needed]

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