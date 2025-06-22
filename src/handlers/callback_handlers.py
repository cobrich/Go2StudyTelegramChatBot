import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard, build_subtopic_selection_keyboard, build_question_keyboard, build_results_keyboard, build_continue_keyboard
from src.utils.translations import get_message
from src.config.constants import DEFAULT_QUESTIONS_PER_TEST
from src.services.ai_service import AIService
from src.services.topic_manager import TopicManager
from src.handlers.base_handler import BaseHandler

class CallbackHandlers(BaseHandler):
    def __init__(self, db=None, question_service=None):
        super().__init__()
        # Переопределяем db и question_service если переданы
        if db:
            self.db = db
        if question_service:
            self.question_service = question_service

    async def _delete_previous_bot_message(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Удаляет предыдущее сообщение бота, если оно сохранено в контексте."""
        try:
            last_bot_message_id = context.user_data.get('last_bot_message_id')
            chat_id = context.user_data.get('chat_id')
            
            if last_bot_message_id and chat_id:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_bot_message_id)
                # Очищаем сохраненный ID после удаления
                context.user_data.pop('last_bot_message_id', None)
        except Exception as e:
            # Игнорируем ошибки удаления (сообщение могло быть уже удалено)
            logging.debug(f"Could not delete previous bot message: {e}")

    async def _save_bot_message_id(self, context: ContextTypes.DEFAULT_TYPE, message, chat_id: int) -> None:
        """Сохраняет ID сообщения бота для последующего удаления."""
        context.user_data['last_bot_message_id'] = message.message_id
        context.user_data['chat_id'] = chat_id

    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (topic_selection): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя перед обработкой выбора темы
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=query.from_user.username or 'не указан')
            )
            return
        
        topic_data = query.data.replace('topic_', '')
        is_retake = False
        logging.info(f"[handle_topic_selection] query.data={query.data}, topic_data={topic_data}, is_retake={is_retake}")
        
        # Удаляем inline-клавиатуру у предыдущего сообщения (результаты или выбор темы)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
            
        # Check if this is a retake
        if topic_data.startswith('retake_'):
            is_retake = True
            topic_index = topic_data.replace('retake_', '')
        else:
            topic_index = topic_data
            
        logging.info(f"[handle_topic_selection] after retake check: is_retake={is_retake}, topic_index={topic_index}")
        try:
            topic_index = int(topic_index)
            # Используем БД вместо констант
            topics = self.db.get_topic_names(active_only=True)
            topic = topics[topic_index]
            logging.info(f"[handle_topic_selection] topic_index={topic_index}, topic={topic}")
        except (ValueError, IndexError):
            logging.error(f"Invalid topic selected: {topic_index}")
            try:
                await query.message.edit_text(
                    get_message('error_topic_selection', user_language),
                    reply_markup=build_topic_selection_keyboard(user_id)
                )
            except Exception:
                pass
            return
        
        chat_id = query.message.chat_id
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
            
        # Очищаем user_data при выборе новой темы
        self.clear_user_data(context)
        # Очищаем флаг выбора темы так как тест начинается
        context.user_data.pop('in_topic_selection', None)
        # Set user as active and store topic
        self.db.set_user_active(user_id, topic)
        self.set_user_data(context, 'current_topic', topic)
        self.set_user_data(context, 'current_question_index', 0)
        
        # Показываем сообщение о подготовке вопросов только перед генерацией
        try:
            # Создаем клавиатуру с кнопкой "В главное меню"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]])
            await query.message.edit_text(get_message('preparing_questions', user_language), reply_markup=keyboard)
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]])
            await query.message.reply_text(get_message('preparing_questions', user_language), reply_markup=keyboard)
        
        # Get or generate questions
        questions = await self.question_service.get_or_generate_tasks(
            user_id=user_id,
            topic=topic,
            needed=DEFAULT_QUESTIONS_PER_TEST,
            is_retake=is_retake
        )
        
        if not questions:
            logging.error(f"Failed to get questions for topic {topic}")
            try:
                await query.message.edit_text(
                    get_message('no_questions', user_language),
                    reply_markup=build_topic_selection_keyboard(user_id)
                )
            except Exception:
                pass
            return
            
        # Store questions in context
        self.set_user_data(context, 'questions', questions)
        self.set_user_data(context, 'answers', [q[1] for q in questions])
        
        # Display first question
        question = questions[0]
        source = question[4] if len(question) > 4 else 'db'
        # Убираем индикаторы источника вопросов
        logging.info(f"[DEBUG] question tuple: {question}")
        logging.info(f"[DEBUG] source: {source}")
        keyboard = build_question_keyboard(question[3], 0, 0, len(questions), user_id, is_random_test=False)
        
        try:
            # If question has an image, send it first
            if len(question) > 5 and question[5]:  # question[5] is image_path
                question_msg = await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=open(question[5], 'rb'),
                    caption=get_message('topic_question', user_language, 
                                      topic=topic, current=1, total=len(questions), question=question[0]),
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                # Сохраняем ID сообщения с вопросом
                await self._save_bot_message_id(context, question_msg, query.message.chat_id)
                return
            else:
                await query.message.edit_text(
                    get_message('topic_question', user_language, 
                              topic=topic, current=1, total=len(questions), question=question[0]),
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                # Сохраняем ID отредактированного сообщения
                await self._save_bot_message_id(context, query.message, query.message.chat_id)
        except Exception as e:
            logging.error(f"Error displaying question: {e}")
            pass

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle answer selection callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (answer): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя перед обработкой ответа
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=query.from_user.username or 'не указан')
            )
            return
        
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index >= len(questions):
            logging.error(f"No questions found for user {user_id}")
            try:
                await query.message.edit_text(
                    get_message('error_occurred', user_language),
                    reply_markup=build_topic_selection_keyboard(user_id)
                )
            except Exception:
                pass
            return
        question = questions[current_index]
        source = question[4] if len(question) > 4 else 'db'
        try:
            selected_index = int(query.data.replace('answer_', '').split('_')[0])
        except Exception:
            selected_index = -1
        options = question[3]
        
        # Дополнительная проверка типа данных для options
        if not isinstance(options, list):
            logging.error(f"Options is not a list: {type(options)}, value: {options}")
            if isinstance(options, str):
                # Пытаемся разбить строку на список
                options = [opt.strip() for opt in options.split('\n') if opt.strip()]
            else:
                # Создаем список с одним элементом
                options = [str(options)]
        
        # Убеждаемся, что все элементы options - строки
        options = [str(opt) for opt in options if opt is not None]
        
        correct_answer = question[1]
        selected_answer = options[selected_index] if 0 <= selected_index < len(options) else None
        
        # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ДЛЯ ОТЛАДКИ
        logging.info(f"🔍 [ОТЛАДКА ОТВЕТОВ] Пользователь {user_id}:")
        logging.info(f"  📋 Все варианты ответов: {options}")
        logging.info(f"  🎯 Выбранный индекс: {selected_index}")
        logging.info(f"  👤 Выбранный ответ: '{selected_answer}'")
        logging.info(f"  ✅ Правильный ответ: '{correct_answer}'")
        logging.info(f"  🔄 Типы данных: selected='{type(selected_answer)}', correct='{type(correct_answer)}'")
        logging.info(f"  📏 Длины строк: selected={len(str(selected_answer)) if selected_answer else 0}, correct={len(str(correct_answer))}")
        logging.info(f"  🔍 Побайтовое сравнение: selected={repr(selected_answer)}, correct={repr(correct_answer)}")
        
        is_correct = selected_answer == correct_answer
        logging.info(f"  ⚖️ Результат сравнения: {is_correct}")
        
        # Получаем объяснение - сначала из структуры вопроса, потом из БД
        explanation = question[2] if len(question) > 2 and question[2] else None
        
        # Если объяснение пустое, ищем в базе данных
        if not explanation or explanation.strip() == '':
            try:
                explanation = self.db.get_explanation_by_question_text(question[0])
                if not explanation:
                    # Пробуем нечеткий поиск
                    explanation = self.db.get_explanation_fuzzy_by_question_text(question[0])
                if not explanation:
                    explanation = "Объяснение не найдено" if user_language == 'ru' else "Түсіндірме табылмады"
            except Exception as e:
                logging.error(f"Error getting explanation for question: {e}")
                explanation = "Объяснение не найдено" if user_language == 'ru' else "Түсіндірме табылмады"
        
        # Store result
        if 'user_results' not in context.user_data:
            context.user_data['user_results'] = []
        
        context.user_data['user_results'].append({
            'q_num': current_index,
            'is_correct': is_correct,
            'question': question[0],
            'user_answer': selected_answer,
            'correct_answer': correct_answer,
            'explanation': explanation,
            'source': source
        })
        if not is_correct:
            # Для случайных тестов сохраняем ошибку под реальной темой вопроса
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            if is_random_test:
                # Извлекаем реальную тему из данных вопроса
                # Предполагаем, что вопрос имеет структуру: (question_text, answer, explanation, options, source, image_path, question_id)
                question_topic = None
                question_id = None
                
                # Проверяем есть ли question_id в структуре вопроса
                if len(question) > 6 and question[6] is not None:
                    question_id = question[6]
                    # Получаем тему из базы данных по question_id
                    try:
                        # Используем database facade вместо прямого SQLite подключения
                        question_topic_result = self.db.questions.fetch_one(
                            '''
                            SELECT s.subtopic_name 
                            FROM questions q 
                            JOIN subtopics s ON q.topic_id = s.id 
                            WHERE q.id = $1 LIMIT 1
                            ''', 
                            (question_id,)
                        )
                        if question_topic_result:
                            question_topic = question_topic_result['subtopic_name']
                    except Exception as e:
                        logging.error(f"Error finding question topic by ID: {e}")
                
                # Если не нашли тему по ID, ищем по тексту вопроса
                if not question_topic:
                    try:
                        # Используем database facade вместо прямого SQLite подключения
                        question_topic_result = self.db.questions.fetch_one(
                            '''
                            SELECT s.subtopic_name 
                            FROM questions q 
                            JOIN subtopics s ON q.topic_id = s.id 
                            WHERE q.question_text = $1 LIMIT 1
                            ''', 
                            (question[0],)
                        )
                        if question_topic_result:
                            question_topic = question_topic_result['subtopic_name']
                    except Exception as e:
                        logging.error(f"Error finding question topic: {e}")
                
                # Если не нашли тему, используем "Неизвестная тема"
                if not question_topic:
                    question_topic = "Неизвестная тема" if user_language == 'ru' else "Белгісіз тақырып"
                
                # Детальное логирование ошибки в случайном тесте
                question_text = question[0]
                if len(question_text) > 150:
                    question_text_short = question_text[:150] + "..."
                else:
                    question_text_short = question_text
                
                logging.info(f"❌ Неправильный ответ в случайном тесте (пользователь {user_id}):")
                logging.info(f"  📚 Тема: {question_topic}")
                logging.info(f"  🆔 Question ID: {question_id}")
                logging.info(f"  ❓ Вопрос: {question_text_short}")
                logging.info(f"  👤 Ответ пользователя: {selected_answer}")
                logging.info(f"  ✅ Правильный ответ: {correct_answer}")
                logging.info(f"  💡 Объяснение: {explanation}")
                logging.info(f"  ---")
                
                # Используем новый метод если есть question_id
                if question_id is not None:
                    # ✅ ЗАЩИТА РЕАЛИЗОВАНА: add_user_error_by_question_id автоматически 
                    # проверяет is_admin() и НЕ записывает ошибки админов в студенческую статистику
                    self.db.add_user_error_by_question_id(
                        user_id=user_id,
                        question_id=question_id,
                        topic=question_topic,
                        user_answer_text=selected_answer,
                        correct_answer_text=correct_answer
                    )
                else:
                    # Fallback к старому методу для AI-генерированных вопросов
                    # ✅ ЗАЩИТА РЕАЛИЗОВАНА: add_user_error автоматически проверяет is_admin()
                    self.db.add_user_error(
                        user_id=user_id,
                        topic=question_topic,
                        question_text=question[0],
                        user_answer_text=selected_answer,
                        correct_answer_text=correct_answer,
                        explanation_text=explanation
                    )
            else:
                # Для обычных тестов используем текущую тему
                current_topic = self.get_user_data(context).get('current_topic')
                question_text = question[0]
                question_id = None
                
                # Проверяем есть ли question_id в структуре вопроса
                if len(question) > 6 and question[6] is not None:
                    question_id = question[6]
                
                if len(question_text) > 150:
                    question_text_short = question_text[:150] + "..."
                else:
                    question_text_short = question_text
                
                logging.info(f"❌ Неправильный ответ в обычном тесте (пользователь {user_id}):")
                logging.info(f"  📚 Тема: {current_topic}")
                logging.info(f"  🆔 Question ID: {question_id}")
                logging.info(f"  ❓ Вопрос: {question_text_short}")
                logging.info(f"  👤 Ответ пользователя: {selected_answer}")
                logging.info(f"  ✅ Правильный ответ: {correct_answer}")
                logging.info(f"  💡 Объяснение: {explanation}")
                logging.info(f"  ---")
                
                # Используем новый метод если есть question_id
                if question_id is not None:
                    # ✅ ЗАЩИТА РЕАЛИЗОВАНА: add_user_error_by_question_id автоматически 
                    # проверяет is_admin() и НЕ записывает ошибки админов в студенческую статистику
                    self.db.add_user_error_by_question_id(
                        user_id=user_id,
                        question_id=question_id,
                        topic=current_topic,
                        user_answer_text=selected_answer,
                        correct_answer_text=correct_answer
                    )
                else:
                    # Fallback к старому методу для AI-генерированных вопросов
                    # ✅ ЗАЩИТА РЕАЛИЗОВАНА: add_user_error автоматически проверяет is_admin()
                    self.db.add_user_error(
                        user_id=user_id,
                        topic=current_topic,
                        question_text=question[0],
                        user_answer_text=selected_answer,
                        correct_answer_text=correct_answer,
                        explanation_text=explanation
                    )
        else:
            # Логируем правильный ответ
            question_text = question[0]
            question_id = None
            
            # Проверяем есть ли question_id в структуре вопроса
            if len(question) > 6 and question[6] is not None:
                question_id = question[6]
            
            if len(question_text) > 150:
                question_text_short = question_text[:150] + "..."
            else:
                question_text_short = question_text
            
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            test_type = "случайном" if is_random_test else "обычном"
            
            logging.info(f"✅ Правильный ответ в {test_type} тесте (пользователь {user_id}):")
            logging.info(f"  🆔 Question ID: {question_id}")
            logging.info(f"  ❓ Вопрос: {question_text_short}")
            logging.info(f"  👤 Ответ пользователя: {selected_answer}")
            
            # Decrement error count if this was previously an error
            if question_id is not None:
                self.db.decrement_error_count_by_question_id(user_id, question_id)
            else:
                # Fallback к старому методу для AI-генерированных вопросов
                self.db.decrement_error_count(user_id, question[0])

        # Get error count for display
        error_count = 0
        if not is_correct:
            error_tasks = self.db.get_error_tasks_for_user(user_id, self.get_user_data(context).get('current_topic'), limit=1)
            for task in error_tasks:
                if task['question'] == question[0]:
                    error_count = task['error_count']
                    break

        # Show brief result - only correct/incorrect and correct answer if wrong
        if is_correct:
            result_text = get_message('correct_answer', user_language)
        else:
            result_text = get_message('incorrect_answer', user_language, correct=correct_answer)
        
        if current_index == len(questions) - 1:
            # Last question - show final result and complete test
            self.db.clear_user_test_activity(user_id)  # Очищаем только тему теста
            self.db.set_user_inactive(user_id)  # Очищаем статус активного теста
            # НЕ очищаем user_data здесь, чтобы сохранить результаты для показа
            # Показываем только кнопку 'Показать результаты'
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('show_results', user_language), callback_data="show_results")]])
            try:
                await query.message.edit_text(
                    f"{result_text}\n\n{get_message('test_completed', user_language)}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Error editing message on test completion: {e}")
                try:
                    # Fallback: send new message
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"{result_text}\n\n{get_message('test_completed', user_language)}",
                        reply_markup=keyboard
                    )
                except Exception as e2:
                    logging.error(f"Error sending fallback message: {e2}")
        else:
            # Not last question - move to next
            next_index = current_index + 1
            self.set_user_data(context, 'current_question_index', next_index)
            keyboard = build_continue_keyboard(user_id)
            try:
                await query.message.edit_text(
                    f"{result_text}\n\n{get_message('continue_next', user_language)}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Error editing message for continue: {e}")
                try:
                    # Fallback: send new message
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"{result_text}\n\n{get_message('continue_next', user_language)}",
                        reply_markup=keyboard
                    )
                except Exception as e2:
                    logging.error(f"Error sending fallback message: {e2}")

    async def handle_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle continue button callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (continue): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        logging.info(f"[handle_continue] current_index={current_index}, questions_len={len(questions)}")
        if not questions or current_index >= len(questions):
            logging.error(f"[handle_continue] No questions found or invalid index: current_index={current_index}, questions_len={len(questions)}")
            try:
                await query.message.edit_text(
                    get_message('error_occurred', user_language),
                    reply_markup=build_topic_selection_keyboard(user_id)
                )
            except Exception as e:
                logging.error(f"[handle_continue] Exception in error message: {e}")
            return
        question = questions[current_index]
        source = question[4] if len(question) > 4 else 'db'
        keyboard = build_question_keyboard(question[3], current_index, current_index, len(questions), user_id, is_random_test=False)
        topic = self.get_user_data(context).get('current_topic', '')
        try:
            await query.message.edit_text(
                get_message('topic_question', user_language, 
                          topic=topic, current=current_index + 1, total=len(questions), question=question[0]),
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            # Сохраняем ID отредактированного сообщения
            await self._save_bot_message_id(context, query.message, query.message.chat_id)
        except Exception as e:
            logging.error(f"[handle_continue] Exception in edit_text: {e}")

    async def handle_show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (show_results): {e}")
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        topic = self.get_user_data(context).get('current_topic')
        questions = self.get_user_data(context).get('questions', [])
        user_results = context.user_data.get('user_results', [])
        if not topic or not questions or not user_results:
            await query.message.edit_text(
                get_message('error_occurred', user_language),
                reply_markup=build_topic_selection_keyboard(user_id)
            )
            return
        total = len(user_results)
        correct = sum(1 for r in user_results if r['is_correct'])
        # Добавляю запись о прохождении теста только здесь
        percentage = (correct / total * 100.0) if total > 0 else 0.0
        
        # Проверяем, является ли это случайным тестом
        is_random_test = self.get_user_data(context).get('is_random_test', False)
        test_type = "случайного" if is_random_test else "обычного"
        
        # Детальное логирование итогового результата
        logging.info(f"📊 Итоговый результат {test_type} теста (пользователь {user_id}):")
        logging.info(f"  📚 Тема: {topic}")
        logging.info(f"  ✅ Правильных ответов: {correct}/{total} ({percentage:.1f}%)")
        
        # ✅ ЗАЩИТА РЕАЛИЗОВАНА: add_test_result автоматически проверяет is_admin() 
        # и НЕ записывает результаты админов в студенческую статистику
        self.db.add_test_result(user_id, topic, percentage)
        errors = [r for r in user_results if not r['is_correct']]
        
        # Логируем детали всех ошибок
        if errors:
            logging.info(f"  ❌ Ошибки в тесте ({len(errors)} из {total}):")
            for i, err in enumerate(errors, 1):
                question_text = err.get('question', 'Вопрос не найден')
                if len(question_text) > 100:
                    question_text_short = question_text[:100] + "..."
                else:
                    question_text_short = question_text
                
                logging.info(f"    {i}. Вопрос #{err['q_num']+1}: {question_text_short}")
                logging.info(f"       👤 Ответ пользователя: {err['user_answer']}")
                logging.info(f"       ✅ Правильный ответ: {err['correct_answer']}")
                logging.info(f"       💡 Объяснение: {err.get('explanation', 'Объяснение отсутствует')}")
                logging.info(f"       ---")
        else:
            logging.info(f"  🎉 Отличный результат! Все ответы правильные")
        
        logging.info(f"✅ Тест завершен и результат сохранен для пользователя {user_id}")
        
        # Всегда показываем красивый краткий результат с кнопками для объяснений
        results_text = get_message('test_results', user_language, 
                                 topic=topic, correct=correct, total=total, percentage=percentage)
        
        if errors:
            results_text += get_message('errors_section', user_language)
            for err in errors:
                results_text += get_message('error_format', user_language, 
                                          num=err['q_num']+1, user_answer=err['user_answer'], 
                                          correct_answer=err['correct_answer'])
        else:
            results_text += get_message('no_errors', user_language)
        
        # Создаем кнопки
        buttons = [[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]]
        
        # Добавляем кнопки объяснений для ошибок
        for err in errors:
            buttons.append([
                InlineKeyboardButton(
                    get_message('explanation_btn', user_language, num=err['q_num']+1),
                    callback_data=f"show_expl_{err['q_num']}"
                )
            ])
        
        if is_random_test:
            # Для случайного теста добавляем кнопку "Пройти еще раз" (повторение ошибок)
            retry_text = "🔄 Пройти еще раз" if user_language == 'ru' else "🔄 Қайта өту"
            buttons.append([InlineKeyboardButton(retry_text, callback_data="retry_random_test")])
        else:
            # Для обычных тестов добавляем кнопку повторения темы
            buttons.append([InlineKeyboardButton(get_message('retake_topic', user_language), callback_data=f"retake_{self.db.get_topic_names(active_only=True).index(topic)}")])
        
        buttons.append([InlineKeyboardButton(get_message('back_to_topics', user_language), callback_data="back_to_topics")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        try:
            await query.message.edit_text(results_text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error editing message with results: {e}")
            try:
                # Fallback: send new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=results_text,
                    reply_markup=keyboard
                )
            except Exception as e2:
                logging.error(f"Error sending fallback results message: {e2}")
        # user_data теперь очищается только при возврате в меню или выборе новой темы

    async def handle_show_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (show_explanation): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        data = query.data.replace('show_expl_', '')
        try:
            q_num = int(data)
        except Exception:
            q_num = None
        user_results = context.user_data.get('user_results', [])
        # Ищем объяснение в user_results, если есть
        explanation = None
        for r in user_results:
            if r['q_num'] == q_num:
                explanation = r
                break
        if explanation:
            source = explanation['source']
            text = get_message('explanation_title', user_language, num=q_num+1)
            text += get_message('explanation_question', user_language, question=explanation['question'])
            text += get_message('explanation_user_answer', user_language, answer=explanation['user_answer'])
            text += get_message('explanation_correct_answer', user_language, answer=explanation['correct_answer'])
            text += get_message('explanation_text', user_language, explanation=explanation['explanation'])
        else:
            text = get_message('question_not_found', user_language)
        # Кнопка назад к результатам
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_message('back_to_results', user_language), callback_data="back_to_results")]
        ])
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            try:
                await query.message.reply_text(text, parse_mode='HTML')
            except Exception as e:
                logging.error(f"Error sending explanation text: {e}")

    async def handle_back_to_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (back_to_results): {e}")
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        topic = self.get_user_data(context).get('current_topic')
        questions = self.get_user_data(context).get('questions', [])
        user_results = context.user_data.get('user_results', [])
        if not topic or not questions or not user_results:
            await query.message.edit_text(
                get_message('error_occurred', user_language),
                reply_markup=build_topic_selection_keyboard(user_id)
            )
            return
        total = len(user_results)
        correct = sum(1 for r in user_results if r['is_correct'])
        percentage = (correct / total * 100.0) if total > 0 else 0.0
        errors = [r for r in user_results if not r['is_correct']]
        
        # Показываем краткий результат с ошибками и кнопками для объяснений
        results_text = get_message('test_results', user_language, 
                                 topic=topic, correct=correct, total=total, percentage=percentage)
        if errors:
            results_text += get_message('errors_section', user_language)
            for err in errors:
                results_text += get_message('error_format', user_language, 
                                          num=err['q_num']+1, user_answer=err['user_answer'], 
                                          correct_answer=err['correct_answer'])
        else:
            results_text += get_message('no_errors', user_language)
        
        buttons = [[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]]
        for err in errors:
            buttons.append([
                InlineKeyboardButton(
                    get_message('explanation_btn', user_language, num=err['q_num']+1),
                    callback_data=f"show_expl_{err['q_num']}"
                )
            ])
        
        # Проверяем, является ли это случайным тестом
        is_random_test = self.get_user_data(context).get('is_random_test', False)
        
        if is_random_test:
            # Для случайного теста добавляем кнопку "Пройти еще раз" (повторение ошибок)
            retry_text = "🔄 Пройти еще раз" if user_language == 'ru' else "🔄 Қайта өту"
            buttons.append([InlineKeyboardButton(retry_text, callback_data="retry_random_test")])
        else:
            # Для обычных тестов добавляем кнопку повторения темы
            buttons.append([InlineKeyboardButton(get_message('retake_topic', user_language), callback_data=f"retake_{self.db.get_topic_names(active_only=True).index(topic)}")])
        
        buttons.append([InlineKeyboardButton(get_message('back_to_topics', user_language), callback_data="back_to_topics")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        try:
            await query.message.edit_text(results_text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error editing message with results: {e}")
            try:
                # Fallback: send new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=results_text,
                    reply_markup=keyboard
                )
            except Exception as e2:
                logging.error(f"Error sending fallback results message: {e2}")
        # user_data теперь очищается только при возврате в меню или выборе новой темы

    async def handle_back_to_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (back_to_topics): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя перед возвратом к темам
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=query.from_user.username or 'не указан')
            )
            return
        
        self.db.clear_user_test_activity(user_id)  # Очищаем только тему теста
        self.db.set_user_inactive(user_id)  # Очищаем статус активного теста
        self.clear_user_data(context)
        # Устанавливаем флаг выбора темы
        context.user_data['in_topic_selection'] = True
        try:
            # Удаляем inline-клавиатуру у старого сообщения
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        try:
            # Отправляем новое сообщение с выбором основных разделов
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=get_message('select_topic', user_language),
                reply_markup=build_topic_selection_keyboard(user_id),
                parse_mode='Markdown'
            )
        except Exception:
            pass

    async def handle_prev_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (prev_question): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index <= 0:
            return
        prev_index = current_index - 1
        self.set_user_data(context, 'current_question_index', prev_index)
        question = questions[prev_index]
        source = question[4] if len(question) > 4 else 'db'
        user_results = context.user_data.get('user_results', [])
        user_answer = None
        correct_answer = question[1]
        explanation = None
        is_correct = False  # Добавляем переменную для отслеживания правильности
        
        for result in user_results:
            if result['q_num'] == prev_index:
                user_answer = result['user_answer']
                explanation = result['explanation']
                is_correct = result['is_correct']  # Получаем реальный результат
                break
        
        topic = self.get_user_data(context).get('current_topic', '')
        question_text = get_message('topic_question', user_language, 
                                  topic=topic, current=prev_index + 1, total=len(questions), question=question[0])
        
        if user_answer is not None:
            # Показываем правильную иконку в зависимости от результата
            if is_correct:
                question_text += f"\n\n✅ <b>Ваш ответ:</b> {user_answer}\n"
                question_text += f"✅ <b>Правильный ответ:</b> {correct_answer}\n\n"
            else:
                question_text += f"\n\n❌ <b>Ваш ответ:</b> {user_answer}\n"
                question_text += f"✅ <b>Правильный ответ:</b> {correct_answer}\n\n"
            
            if explanation:
                question_text += f"\n\n{get_message('explanation_text', user_language, explanation=explanation)}"
            # Только навигация
            nav_buttons = []
            if prev_index > 0:
                nav_buttons.append(InlineKeyboardButton(get_message('previous', user_language), callback_data="prev_question"))
            if prev_index < len(questions) - 1:
                nav_buttons.append(InlineKeyboardButton(get_message('next', user_language), callback_data="next_question"))
            # Добавляем кнопку навигации в зависимости от типа теста
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            if prev_index == 0:
                if is_random_test:
                    # Для случайных тестов показываем кнопку "В главное меню"
                    nav_buttons.append(InlineKeyboardButton(f"🏠 {get_message('main_menu', user_language)}", callback_data="main_menu"))
                else:
                    # Для обычных тестов показываем кнопку "Назад к темам"
                    nav_buttons.append(InlineKeyboardButton(f"⬅️ {get_message('back_to_topics', user_language)}", callback_data="back_to_topics"))
            keyboard = InlineKeyboardMarkup([nav_buttons] if nav_buttons else [])
        else:
            # Варианты ответа и навигация
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            keyboard = build_question_keyboard(question[3], prev_index, max(prev_index, current_index), len(questions), user_id, is_random_test=is_random_test)
        try:
            await query.message.edit_text(question_text, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            pass

    async def handle_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (next_question): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index >= len(questions) - 1:
            return
        next_index = current_index + 1
        self.set_user_data(context, 'current_question_index', next_index)
        question = questions[next_index]
        source = question[4] if len(question) > 4 else 'db'
        user_results = context.user_data.get('user_results', [])
        user_answer = None
        correct_answer = question[1]
        explanation = None
        is_correct = False  # Добавляем переменную для отслеживания правильности
        
        for result in user_results:
            if result['q_num'] == next_index:
                user_answer = result['user_answer']
                explanation = result['explanation']
                is_correct = result['is_correct']  # Получаем реальный результат
                break
        
        topic = self.get_user_data(context).get('current_topic', '')
        question_text = get_message('topic_question', user_language, 
                                  topic=topic, current=next_index + 1, total=len(questions), question=question[0])
        
        if user_answer is not None:
            # Показываем правильную иконку в зависимости от результата
            if is_correct:
                question_text += f"\n\n✅ <b>Ваш ответ:</b> {user_answer}\n"
                question_text += f"✅ <b>Правильный ответ:</b> {correct_answer}\n\n"
            else:
                question_text += f"\n\n❌ <b>Ваш ответ:</b> {user_answer}\n"
                question_text += f"✅ <b>Правильный ответ:</b> {correct_answer}\n\n"
            
            if explanation:
                question_text += f"\n\n{get_message('explanation_text', user_language, explanation=explanation)}"
            # Только навигация
            nav_buttons = []
            if next_index > 0:
                nav_buttons.append(InlineKeyboardButton(get_message('previous', user_language), callback_data="prev_question"))
            if next_index < len(questions) - 1:
                nav_buttons.append(InlineKeyboardButton(get_message('next', user_language), callback_data="next_question"))
            # Добавляем кнопку навигации в зависимости от типа теста
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            if next_index == 0:
                if is_random_test:
                    # Для случайных тестов показываем кнопку "В главное меню"
                    nav_buttons.append(InlineKeyboardButton(f"🏠 {get_message('main_menu', user_language)}", callback_data="main_menu"))
                else:
                    # Для обычных тестов показываем кнопку "Назад к темам"
                    nav_buttons.append(InlineKeyboardButton(f"⬅️ {get_message('back_to_topics', user_language)}", callback_data="back_to_topics"))
            keyboard = InlineKeyboardMarkup([nav_buttons] if nav_buttons else [])
        else:
            # Варианты ответа и навигация
            is_random_test = self.get_user_data(context).get('is_random_test', False)
            keyboard = build_question_keyboard(question[3], next_index, next_index, len(questions), user_id, is_random_test=is_random_test)
        try:
            await query.message.edit_text(question_text, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            pass

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (main_menu): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя перед отправкой главного меню
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=query.from_user.username or 'не указан')
            )
            return
        
        self.db.clear_user_test_activity(user_id)  # Очищаем только тему теста
        self.db.set_user_inactive(user_id)  # Очищаем статус активного теста
        self.clear_user_data(context)
        # Очищаем флаг выбора темы
        context.user_data.pop('in_topic_selection', None)
        try:
            # Удаляем inline-клавиатуру у старого сообщения
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        try:
            # Отправляем новое сообщение с главным меню (обычная клавиатура)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=get_message('topic_not_selected', user_language),
                reply_markup=get_main_menu_markup(user_id)
            )
        except Exception:
            pass

    async def handle_main_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main topic category selection callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (main_topic): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        is_admin = user_id and self.db.is_admin(user_id)
        
        # Извлекаем индекс основной темы
        try:
            main_topic_index = int(query.data.replace('main_topic_', ''))
            
            # Получаем основные разделы в зависимости от роли пользователя
            if is_admin:
                # Админы видят все разделы (русские и казахские)
                russian_topics = self.db.get_main_topics_by_language('ru', active_only=True)
                kazakh_topics = self.db.get_main_topics_by_language('kk', active_only=True)
                all_topics = russian_topics + kazakh_topics
                # Сортируем по названию
                all_topics.sort(key=lambda x: x['topic_name'])
                main_topic = all_topics[main_topic_index]['topic_name']
            else:
                # Ученики видят только разделы на своем языке
                user_topics = self.db.get_main_topics_by_language(user_language, active_only=True)
                main_topic = user_topics[main_topic_index]['topic_name']
            
            logging.info(f"[handle_main_topic_selection] main_topic_index={main_topic_index}, main_topic={main_topic}")
        except (ValueError, IndexError):
            logging.error(f"Invalid main topic selected: {query.data}")
            try:
                await query.message.edit_text(
                    get_message('error_topic_selection', user_language),
                    reply_markup=build_topic_selection_keyboard(user_id)
                )
            except Exception:
                pass
            return
        
        # Показываем подтемы выбранного раздела
        info_text = f"📚 **{main_topic}**\n\n"
        if user_language == 'kk':
            info_text += "Нақты тақырыпты таңдаңыз:"
        else:
            info_text += "Выберите конкретную тему:"
        
        # Добавляем объяснение индикаторов только для админов
        if is_admin:
            if user_language == 'kk':
                info_text += "\n\n🟢 - дерекқорда сұрақтар бар\n🟡 - ЖИ сіз үшін сұрақтар жасайды"
            else:
                info_text += "\n\n🟢 - есть вопросы в базе данных\n🟡 - ИИ сгенерирует вопросы для вас"
        
        try:
            await query.message.edit_text(
                info_text,
                reply_markup=build_subtopic_selection_keyboard(main_topic, main_topic_index, user_id),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error displaying subtopics: {e}")
            pass

    async def handle_back_to_main_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back to main topics callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (back_to_main_topics): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Возвращаемся к выбору основных разделов
        try:
            await query.message.edit_text(
                get_message('select_topic', user_language),
                reply_markup=build_topic_selection_keyboard(user_id),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error returning to main topics: {e}")
            pass 

    async def handle_retry_random_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle retry random test with focus on errors."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (retry_random_test): {e}")
        
        user_id = query.from_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=query.from_user.username or 'не указан')
            )
            return
        
        # Clear previous data
        self.clear_user_data(context)
        
        # Show preparing message
        preparing_text = get_message('preparing_retry_test', user_language)
        
        try:
            await query.message.edit_text(preparing_text)
        except Exception:
            await query.message.reply_text(preparing_text)
        
        # Generate retry test using RandomTestService
        from src.services.random_test_service import RandomTestService
        random_test_service = RandomTestService(self.db)
        questions_data = random_test_service.generate_retry_test(user_id, 10)
        
        if not questions_data:
            error_text = get_message('retry_test_error', user_language)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]])
            try:
                await query.message.edit_text(error_text, reply_markup=keyboard)
            except Exception:
                await query.message.reply_text(error_text, reply_markup=keyboard)
            return
        
        # Convert questions data to the format expected by the test system
        questions = []
        for q_data in questions_data:
            # Формируем список вариантов ответов как в handle_random_test
            options = [q_data.get('answer', '')]  # Сначала правильный ответ
            
            # Добавляем неправильные варианты
            incorrect_options = q_data.get('incorrect_options', '')
            if incorrect_options:
                if isinstance(incorrect_options, str):
                    incorrect_opts = [opt.strip() for opt in incorrect_options.split('\n') if opt.strip()]
                    options.extend(incorrect_opts)
            
            # Убеждаемся, что есть минимум 2 варианта
            if len(options) < 2:
                default_option = "Вариант" if user_language == 'ru' else "Нұсқа"
                options.extend([f"{default_option} {i}" for i in range(len(options), 4)])
            
            # Перемешиваем варианты
            import random
            random.shuffle(options)
            
            # Format: (question_text, correct_answer, explanation, options_list, source, image_path)
            question_tuple = (
                q_data.get('question', ''),  # 0 - question_text
                q_data.get('answer', ''),    # 1 - correct_answer  
                q_data.get('explanation', ''),  # 2 - explanation (ИСПРАВЛЕНО!)
                options,  # 3 - options_list
                'retry_test',  # 4 - source
                q_data.get('image_path', None)  # 5 - image_path
            )
            questions.append(question_tuple)
        
        # Set user as active for retry test
        retry_topic_name = get_message('retry_topic_name', user_language)
        self.db.set_user_active(user_id, retry_topic_name)
        self.set_user_data(context, 'current_topic', retry_topic_name)
        self.set_user_data(context, 'current_question_index', 0)
        self.set_user_data(context, 'questions', questions)
        self.set_user_data(context, 'answers', [q[1] for q in questions])
        self.set_user_data(context, 'is_random_test', True)  # Keep as random test for UI consistency
        
        # Display first question
        if questions:
            from src.utils.keyboards import build_question_keyboard
            
            question = questions[0]
            keyboard = build_question_keyboard(question[3], 0, 0, len(questions), user_id, is_random_test=True)
            
            try:
                # If question has an image, send it first
                if len(question) > 5 and question[5]:  # question[5] is image_path
                    question_msg = await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=open(question[5], 'rb'),
                        caption=get_message('random_test_question', user_language, 
                                          current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    # Сохраняем ID сообщения с вопросом
                    await self._save_bot_message_id(context, question_msg, query.message.chat_id)
                    return
                else:
                    await query.message.edit_text(
                        get_message('random_test_question', user_language, 
                                  current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard
                    )
                    # Сохраняем ID отредактированного сообщения
                    await self._save_bot_message_id(context, query.message, query.message.chat_id)
            except Exception as e:
                logging.error(f"Error displaying retry test question: {e}")
                error_text = get_message('question_display_error', user_language)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]])
                try:
                    await query.message.edit_text(error_text, reply_markup=keyboard)
                except Exception:
                    await query.message.reply_text(error_text, reply_markup=keyboard)
        else:
            error_text = get_message('questions_load_error', user_language)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]])
            try:
                await query.message.edit_text(error_text, reply_markup=keyboard)
            except Exception:
                await query.message.reply_text(error_text, reply_markup=keyboard) 

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main callback handler that routes to specific handlers based on callback data."""
        query = update.callback_query
        callback_data = query.data
        
        # Route to specific handlers based on callback data
        if callback_data.startswith('topic_') or callback_data.startswith('retake_'):
            await self.handle_topic_selection(update, context)
        elif callback_data.startswith('answer_'):
            await self.handle_answer(update, context)
        elif callback_data == 'continue_test':
            await self.handle_continue(update, context)
        elif callback_data == 'show_results':
            await self.handle_show_results(update, context)
        elif callback_data.startswith('show_expl_'):
            await self.handle_show_explanation(update, context)
        elif callback_data == 'back_to_results':
            await self.handle_back_to_results(update, context)
        elif callback_data == 'back_to_topics':
            await self.handle_back_to_topics(update, context)
        elif callback_data.startswith('prev_question_'):
            await self.handle_prev_question(update, context)
        elif callback_data.startswith('next_question_'):
            await self.handle_next_question(update, context)
        elif callback_data == 'main_menu':
            await self.handle_main_menu(update, context)
        elif callback_data.startswith('main_topic_'):
            await self.handle_main_topic_selection(update, context)
        elif callback_data == 'back_to_main_topics':
            await self.handle_back_to_main_topics(update, context)
        elif callback_data == 'retry_random_test':
            await self.handle_retry_random_test(update, context)
        else:
            # Default handling for unknown callbacks
            try:
                await self.safe_answer_callback(query)
            except Exception:
                pass 