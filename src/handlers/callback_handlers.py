from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from .base_handler import BaseHandler
from utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard, build_subtopic_selection_keyboard, build_question_keyboard, build_results_keyboard, build_continue_keyboard
from config.constants import DEFAULT_QUESTIONS_PER_TEST
from services.ai_service import AIService
from services.topic_manager import TopicManager

class CallbackHandlers(BaseHandler):
    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection callback."""
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (topic_selection): {e}")
        
        user_id = query.from_user.id
        
        # Проверяем доступ пользователя перед обработкой выбора темы
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{query.from_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
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
                    "Произошла ошибка при выборе темы. Пожалуйста, попробуйте еще раз.",
                    reply_markup=build_topic_selection_keyboard()
                )
            except Exception:
                pass
            return
        
        # Показываем сообщение о поиске для всех выборов темы
        try:
            # Проверяем, есть ли вопросы в БД для этой темы
            topic_counts = self.db.get_topic_question_counts()
            has_questions_in_db = topic_counts.get(topic, 0) > 0
            
            # Создаем клавиатуру с кнопкой "В главное меню"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]])
            
            await query.message.edit_text("🔍 Подготавливаем вопросы...", reply_markup=keyboard)
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            try:
                # Создаем клавиатуру с кнопкой "В главное меню"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]])
                
                await query.message.reply_text("🔍 Подготавливаем вопросы...", reply_markup=keyboard)
            except Exception:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]])
                await query.message.reply_text("🔍 Подготавливаем вопросы, подождите...", reply_markup=keyboard)
        
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
                    "Произошла ошибка при получении вопросов. Пожалуйста, попробуйте еще раз.",
                    reply_markup=build_topic_selection_keyboard()
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
        keyboard = build_question_keyboard(question[3], 0, 0, len(questions))
        
        try:
            # If question has an image, send it first
            if len(question) > 5 and question[5]:  # question[5] is image_path
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=open(question[5], 'rb'),
                    caption=f"Тема: {topic}\nВопрос 1 из {len(questions)}:\n\n{question[0]}",
                    reply_markup=keyboard
                )
                return
            else:
                await query.message.edit_text(
                    f"Тема: {topic}\nВопрос 1 из {len(questions)}:\n\n{question[0]}",
                    reply_markup=keyboard
                )
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
        
        # Проверяем доступ пользователя перед обработкой ответа
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{query.from_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return
        
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index >= len(questions):
            logging.error(f"No questions found for user {user_id}")
            try:
                await query.message.edit_text(
                    "Произошла ошибка. Пожалуйста, начните тест заново.",
                    reply_markup=build_topic_selection_keyboard()
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
        is_correct = selected_answer == correct_answer
        # Store result
        if 'user_results' not in context.user_data:
            context.user_data['user_results'] = []
        context.user_data['user_results'].append({
            'q_num': current_index,
            'is_correct': is_correct,
            'question': question[0],
            'user_answer': selected_answer,
            'correct_answer': correct_answer,
            'explanation': question[2],
            'source': source
        })
        if not is_correct:
            logging.info(f"[DEBUG] add_user_error: user_id={user_id}, topic={self.get_user_data(context).get('current_topic')}, question_text={question[0]}, user_answer_text={selected_answer}, correct_answer_text={correct_answer}, explanation_text={question[2]}, is_correct={is_correct}")
            self.db.add_user_error(
                user_id=user_id,
                topic=self.get_user_data(context).get('current_topic'),
                question_text=question[0],
                user_answer_text=selected_answer,
                correct_answer_text=correct_answer,
                explanation_text=question[2]
            )
        else:
            # Decrement error count if this was previously an error
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
            result_text = "✅ Правильно!"
        else:
            result_text = f"❌ Неправильно!\n\nПравильный ответ: {correct_answer}"
        
        if current_index == len(questions) - 1:
            # Last question - show final result and complete test
            self.db.set_user_inactive(user_id)
            # Показываем только кнопку 'Показать результаты'
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Показать результаты", callback_data="show_results")]])
            try:
                await query.message.edit_text(
                    f"{result_text}\n\nТест завершен! Нажмите 'Показать результаты' для просмотра полного разбора.",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Error editing message on test completion: {e}")
                try:
                    # Fallback: send new message
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"{result_text}\n\nТест завершен! Нажмите 'Показать результаты' для просмотра полного разбора.",
                        reply_markup=keyboard
                    )
                except Exception as e2:
                    logging.error(f"Error sending fallback message: {e2}")
            # Не очищаем user_data, чтобы сохранить результаты для итогов
        else:
            # Not last question - move to next
            next_index = current_index + 1
            self.set_user_data(context, 'current_question_index', next_index)
            keyboard = build_continue_keyboard()
            try:
                await query.message.edit_text(
                    f"{result_text}\n\nНажмите 'Продолжить' для следующего вопроса.",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Error editing message for continue: {e}")
                try:
                    # Fallback: send new message
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"{result_text}\n\nНажмите 'Продолжить' для следующего вопроса.",
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
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        logging.info(f"[handle_continue] current_index={current_index}, questions_len={len(questions)}")
        if not questions or current_index >= len(questions):
            logging.error(f"[handle_continue] No questions found or invalid index: current_index={current_index}, questions_len={len(questions)}")
            try:
                await query.message.edit_text(
                    "Произошла ошибка. Пожалуйста, начните тест заново.",
                    reply_markup=build_topic_selection_keyboard()
                )
            except Exception as e:
                logging.error(f"[handle_continue] Exception in error message: {e}")
            return
        question = questions[current_index]
        source = question[4] if len(question) > 4 else 'db'
        keyboard = build_question_keyboard(question[3], current_index, current_index, len(questions))
        topic = self.get_user_data(context).get('current_topic', '')
        try:
            await query.message.edit_text(
                f"Тема: {topic}\nВопрос {current_index + 1} из {len(questions)}:\n\n{question[0]}",
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"[handle_continue] Exception in edit_text: {e}")

    async def handle_show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (show_results): {e}")
        user_id = query.from_user.id
        topic = self.get_user_data(context).get('current_topic')
        questions = self.get_user_data(context).get('questions', [])
        user_results = context.user_data.get('user_results', [])
        if not topic or not questions or not user_results:
            await query.message.edit_text(
                "Произошла ошибка. Пожалуйста, начните тест заново.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
        total = len(user_results)
        correct = sum(1 for r in user_results if r['is_correct'])
        # Добавляю запись о прохождении теста только здесь
        percentage = (correct / total * 100.0) if total > 0 else 0.0
        self.db.add_test_result(user_id, topic, percentage)
        errors = [r for r in user_results if not r['is_correct']]
        
        # Всегда показываем красивый краткий результат с кнопками для объяснений
        results_text = f"📊 Результаты теста по теме '{topic}':\n\n"
        results_text += f"Правильных ответов: {correct} из {total} ({percentage:.1f}%)\n\n"
        
        if errors:
            results_text += "❌ Ошибки:\n"
            for err in errors:
                results_text += f"Вопрос {err['q_num']+1}: {err['user_answer']} → {err['correct_answer']}\n"
        else:
            results_text += "🎉 Поздравляем! Все ответы верны!\n"
        
        # Создаем кнопки
        buttons = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
        
        # Добавляем кнопки объяснений для ошибок
        for err in errors:
            buttons.append([
                InlineKeyboardButton(
                    f"💡 Объяснение к вопросу {err['q_num']+1}",
                    callback_data=f"show_expl_{err['q_num']}"
                )
            ])
        
        # Добавляем кнопки навигации
        buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", callback_data=f"retake_{self.db.get_topic_names(active_only=True).index(topic)}")])
        buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
        
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
            text = f"💡 <b>Объяснение к вопросу {q_num+1}</b>\n\n"
            text += f"<b>Вопрос:</b> {explanation['question']}\n\n"
            text += f"❌ <b>Ваш ответ:</b> {explanation['user_answer']}\n"
            text += f"✅ <b>Правильный ответ:</b> {explanation['correct_answer']}\n\n"
            text += f"📝 <b>Объяснение:</b>\n{explanation['explanation']}"
        else:
            text = "❌ Вопрос не найден."
        # Кнопка назад к результатам
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад к результатам", callback_data="back_to_results")]
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
        topic = self.get_user_data(context).get('current_topic')
        questions = self.get_user_data(context).get('questions', [])
        user_results = context.user_data.get('user_results', [])
        if not topic or not questions or not user_results:
            await query.message.edit_text(
                "Произошла ошибка. Пожалуйста, начните тест заново.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
        total = len(user_results)
        correct = sum(1 for r in user_results if r['is_correct'])
        percentage = (correct / total * 100.0) if total > 0 else 0.0
        errors = [r for r in user_results if not r['is_correct']]
        
        # Показываем краткий результат с ошибками и кнопками для объяснений
        results_text = f"📊 Результаты теста по теме '{topic}':\n\n"
        results_text += f"Правильных ответов: {correct} из {total} ({percentage:.1f}%)\n\n"
        if errors:
            results_text += "❌ Ошибки:\n"
            for err in errors:
                results_text += f"Вопрос {err['q_num']+1}: {err['user_answer']} → {err['correct_answer']}\n"
        else:
            results_text += "🎉 Поздравляем! Все ответы верны!\n"
        
        buttons = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
        for err in errors:
            buttons.append([
                InlineKeyboardButton(
                    f"💡 Объяснение к вопросу {err['q_num']+1}",
                    callback_data=f"show_expl_{err['q_num']}"
                )
            ])
        buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", callback_data=f"retake_{self.db.get_topic_names(active_only=True).index(topic)}")])
        buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(results_text, reply_markup=keyboard)
        except Exception:
            pass

    async def handle_back_to_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (back_to_topics): {e}")
        
        user_id = query.from_user.id
        
        # Проверяем доступ пользователя перед возвратом к темам
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{query.from_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return
        
        self.db.set_user_inactive(user_id)
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
                text="📚 **Выберите раздел математики:**",
                reply_markup=build_topic_selection_keyboard(),
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
        for result in user_results:
            if result['q_num'] == prev_index:
                user_answer = result['user_answer']
                explanation = result['explanation']
                break
        question_text = f"Тема: {self.get_user_data(context).get('current_topic', '')}\nВопрос {prev_index + 1} из {len(questions)}:\n\n{question[0]}"
        if user_answer is not None:
            question_text += f"\n\nВаш ответ: {user_answer}\nПравильный ответ: {correct_answer}"
            if explanation:
                question_text += f"\n\nОбъяснение: {explanation}"
            # Только навигация
            nav_buttons = []
            if prev_index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data="prev_question"))
            if prev_index < len(questions) - 1:
                nav_buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data="next_question"))
            if prev_index == 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics"))
            keyboard = InlineKeyboardMarkup([nav_buttons] if nav_buttons else [])
        else:
            # Варианты ответа и навигация
            keyboard = build_question_keyboard(question[3], prev_index, max(prev_index, current_index), len(questions))
        try:
            await query.message.edit_text(question_text, reply_markup=keyboard)
        except Exception:
            pass

    async def handle_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (next_question): {e}")
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
        for result in user_results:
            if result['q_num'] == next_index:
                user_answer = result['user_answer']
                explanation = result['explanation']
                break
        question_text = f"Тема: {self.get_user_data(context).get('current_topic', '')}\nВопрос {next_index + 1} из {len(questions)}:\n\n{question[0]}"
        if user_answer is not None:
            question_text += f"\n\nВаш ответ: {user_answer}\nПравильный ответ: {correct_answer}"
            if explanation:
                question_text += f"\n\nОбъяснение: {explanation}"
            # Только навигация
            nav_buttons = []
            if next_index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data="prev_question"))
            if next_index < len(questions) - 1:
                nav_buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data="next_question"))
            if next_index == 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics"))
            keyboard = InlineKeyboardMarkup([nav_buttons] if nav_buttons else [])
        else:
            # Варианты ответа и навигация
            keyboard = build_question_keyboard(question[3], next_index, next_index, len(questions))
        try:
            await query.message.edit_text(question_text, reply_markup=keyboard)
        except Exception:
            pass

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        try:
            await self.safe_answer_callback(query)
        except Exception as e:
            logging.error(f"Error in query.answer() (main_menu): {e}")
        
        user_id = query.from_user.id
        
        # Проверяем доступ пользователя перед отправкой главного меню
        if not self.db.check_user_access(user_id, query.from_user.username):
            await query.message.edit_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{query.from_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return
        
        self.db.set_user_inactive(user_id)
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
                text="Тема не выбрана. Пожалуйста, выберите действие из меню.",
                reply_markup=get_main_menu_markup()
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
        
        # Извлекаем индекс основной темы
        try:
            main_topic_index = int(query.data.replace('main_topic_', ''))
            # Получаем основные разделы из БД
            base_structure = self.db.get_base_topic_structure()
            main_topics = list(base_structure.keys())
            main_topic = main_topics[main_topic_index]
            logging.info(f"[handle_main_topic_selection] main_topic_index={main_topic_index}, main_topic={main_topic}")
        except (ValueError, IndexError):
            logging.error(f"Invalid main topic selected: {query.data}")
            try:
                await query.message.edit_text(
                    "Произошла ошибка при выборе раздела. Пожалуйста, попробуйте еще раз.",
                    reply_markup=build_topic_selection_keyboard()
                )
            except Exception:
                pass
            return
        
        # Показываем подтемы выбранного раздела
        info_text = f"📚 **{main_topic}**\n\nВыберите конкретную тему:"
        
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
        
        # Возвращаемся к выбору основных разделов
        try:
            await query.message.edit_text(
                "📚 **Выберите раздел математики:**",
                reply_markup=build_topic_selection_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error returning to main topics: {e}")
            pass 