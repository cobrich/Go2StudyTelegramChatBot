from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from handlers.base_handler import BaseHandler
from utils.keyboards import (
    build_topic_selection_keyboard,
    build_question_keyboard,
    build_results_keyboard,
    build_continue_keyboard,
    get_main_menu_markup
)
from config.constants import TOPICS, DEFAULT_QUESTIONS_PER_TEST

class CallbackHandlers(BaseHandler):
    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection callback."""
        query = update.callback_query
        topic_index = query.data.replace('topic_', '')
        try:
            topic_index = int(topic_index)
            topic = TOPICS[topic_index]
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
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
            
        # Set user as active and store topic
        self.db.set_user_active(user_id, topic)
        self.set_user_data(context, 'current_topic', topic)
        self.set_user_data(context, 'current_question_index', 0)
        
        # Get or generate questions
        questions = await self.question_service.get_or_generate_tasks(
            user_id=user_id,
            topic=topic,
            needed=DEFAULT_QUESTIONS_PER_TEST
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
        source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
        keyboard = build_question_keyboard(question[3], 0, 0, len(questions))
        
        try:
            # If question has an image, send it first
            if len(question) > 5 and question[5]:  # question[5] is image_path
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=open(question[5], 'rb'),
                    caption=f"Тема: {topic}\nВопрос 1 из {len(questions)} {source_text}:\n\n{question[0]}",
                    reply_markup=keyboard
                )
            else:
                await query.message.edit_text(
                    f"Тема: {topic}\nВопрос 1 из {len(questions)} {source_text}:\n\n{question[0]}",
                    reply_markup=keyboard
                )
        except Exception as e:
            logging.error(f"Error displaying question: {e}")
            pass

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle answer selection callback."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
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
        source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
        try:
            selected_index = int(query.data.replace('answer_', '').split('_')[0])
        except Exception:
            selected_index = -1
        options = question[3]
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
            'source': source_text
        })
        self.db.add_test_result(
            user_id=user_id,
            topic=self.get_user_data(context).get('current_topic'),
            percentage=100.0 if is_correct else 0.0
        )
        if not is_correct:
            self.db.add_user_error(
                user_id=user_id,
                topic=self.get_user_data(context).get('current_topic'),
                question_text=question[0],
                user_answer_text=selected_answer,
                correct_answer_text=correct_answer,
                explanation_text=question[2]
            )
        result_text = (
            f"{'✅ Правильно!' if is_correct else '❌ Неправильно!'}\n\n"
            f"Правильный ответ: {correct_answer}\n"
            f"Объяснение: {question[2]}\n"
            f"Источник: {source_text}"
        )
        if current_index == len(questions) - 1:
            self.db.set_user_inactive(user_id)
            # Показываем только кнопку 'Показать результаты'
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Показать результаты", callback_data="show_results")]])
            try:
                await query.message.edit_text(
                    f"{result_text}\n\nТест завершен! Нажмите 'Показать результаты' для просмотра итогов.",
                    reply_markup=keyboard
                )
            except Exception:
                pass
            # Не очищаем user_data, чтобы сохранить результаты для итогов
        else:
            next_index = current_index + 1
            self.set_user_data(context, 'current_question_index', next_index)
            keyboard = build_continue_keyboard()
            try:
                await query.message.edit_text(
                    f"{result_text}\n\nНажмите 'Продолжить' для следующего вопроса.",
                    reply_markup=keyboard
                )
            except Exception:
                pass

    async def handle_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle continue button callback."""
        query = update.callback_query
        await query.answer()
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
        source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
        keyboard = build_question_keyboard(question[3], current_index, current_index, len(questions))
        topic = self.get_user_data(context).get('current_topic', '')
        try:
            await query.message.edit_text(
                f"Тема: {topic}\nВопрос {current_index + 1} из {len(questions)} {source_text}:\n\n{question[0]}",
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"[handle_continue] Exception in edit_text: {e}")

    async def handle_show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle show results callback."""
        query = update.callback_query
        await query.answer()
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
        errors = [r for r in user_results if not r['is_correct']]
        results_text = f"📊 Результаты теста по теме '{topic}':\n\n"
        results_text += f"Правильных ответов: {correct} из {total}\n\n"
        if errors:
            results_text += "Ошибки:\n"
            for err in errors:
                results_text += (
                    f"\nВопрос {err['q_num']+1}: {err['question'][:80]}...\n"
                    f"Ваш ответ: {err['user_answer']}\n"
                    f"Правильный ответ: {err['correct_answer']}\n"
                    f"Объяснение: {err['explanation'][:200]}\n"
                )
        else:
            results_text += "Поздравляем! Все ответы верны!\n"
        keyboard = build_results_keyboard([
            {'q_num': err['q_num']} for err in errors
        ], topic)
        try:
            await query.message.edit_text(results_text, reply_markup=keyboard)
        except Exception:
            pass
        # Очищаем user_data после показа итогов
        self.clear_user_data(context)
        self.db.set_user_inactive(user_id)

    async def handle_show_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data.replace('show_expl_', '')
        try:
            q_num = int(data)
        except Exception:
            q_num = None
        questions = self.get_user_data(context).get('questions', [])
        if q_num is not None and 0 <= q_num < len(questions):
            q = questions[q_num]
            source = q[4] if len(q) > 4 else 'db'
            source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
            text = f"Вопрос: {q[0]}\n\nПравильный ответ: {q[1]}\n\nОбъяснение: {q[2]}\n\nИсточник: {source_text}"
        else:
            text = "Вопрос не найден."
        try:
            await query.message.reply_text(text)
        except Exception:
            pass

    async def handle_back_to_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        self.db.set_user_inactive(user_id)
        self.clear_user_data(context)
        try:
            await query.message.edit_text(
                "Выберите действие:",
                reply_markup=get_main_menu_markup()
            )
        except Exception:
            pass

    async def handle_prev_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index <= 0:
            return
        prev_index = current_index - 1
        self.set_user_data(context, 'current_question_index', prev_index)
        question = questions[prev_index]
        source = question[4] if len(question) > 4 else 'db'
        source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
        keyboard = build_question_keyboard(question[3], prev_index, max(prev_index, current_index), len(questions))
        try:
            await query.message.edit_text(
                f"Тема: {self.get_user_data(context).get('current_topic', '')}\nВопрос {prev_index + 1} из {len(questions)} {source_text}:\n\n{question[0]}",
                reply_markup=keyboard
            )
        except Exception:
            pass

    async def handle_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        if not questions or current_index >= len(questions) - 1:
            return
        next_index = current_index + 1
        self.set_user_data(context, 'current_question_index', next_index)
        question = questions[next_index]
        source = question[4] if len(question) > 4 else 'db'
        source_text = '🟢 (из базы)' if source == 'db' else '🤖 (ИИ)'
        keyboard = build_question_keyboard(question[3], next_index, next_index, len(questions))
        try:
            await query.message.edit_text(
                f"Тема: {self.get_user_data(context).get('current_topic', '')}\nВопрос {next_index + 1} из {len(questions)} {source_text}:\n\n{question[0]}",
                reply_markup=keyboard
            )
        except Exception:
            pass

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        self.db.set_user_inactive(user_id)
        self.clear_user_data(context)
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