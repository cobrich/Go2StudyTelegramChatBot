from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from src.handlers.base_handler import BaseHandler
from src.utils.keyboards import (
    build_topic_selection_keyboard,
    build_question_keyboard,
    build_results_keyboard,
    build_continue_keyboard
)
from src.config.constants import TOPICS, DEFAULT_QUESTIONS_PER_TEST

class CallbackHandlers(BaseHandler):
    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection callback."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        topic = query.data.replace('topic_', '')
        
        if topic not in TOPICS:
            logging.error(f"Invalid topic selected: {topic}")
            await query.message.edit_text(
                "Произошла ошибка при выборе темы. Пожалуйста, попробуйте еще раз.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
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
            num_questions=DEFAULT_QUESTIONS_PER_TEST
        )
        
        if not questions:
            logging.error(f"Failed to get questions for topic {topic}")
            await query.message.edit_text(
                "Произошла ошибка при получении вопросов. Пожалуйста, попробуйте еще раз.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
        # Store questions in context
        self.set_user_data(context, 'questions', questions)
        
        # Display first question
        question = questions[0]
        keyboard = build_question_keyboard(0, len(questions))
        
        await query.message.edit_text(
            f"Вопрос 1 из {len(questions)}:\n\n{question['question']}",
            reply_markup=keyboard
        )

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle answer selection callback."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        # Get current question data
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        
        if not questions or current_index >= len(questions):
            logging.error(f"No questions found for user {user_id}")
            await query.message.edit_text(
                "Произошла ошибка. Пожалуйста, начните тест заново.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
        question = questions[current_index]
        selected_answer = query.data.replace('answer_', '')
        
        # Check if answer is correct
        is_correct = selected_answer == question['correct_answer']
        
        # Store result
        self.db.add_test_result(
            user_id=user_id,
            topic=question['topic'],
            question_id=question['id'],
            is_correct=is_correct,
            selected_answer=selected_answer
        )
        
        # If incorrect, store as error
        if not is_correct:
            self.db.add_user_error(
                user_id=user_id,
                topic=question['topic'],
                question_id=question['id']
            )
        
        # Show result
        result_text = (
            f"{'✅ Правильно!' if is_correct else '❌ Неправильно!'}\n\n"
            f"Правильный ответ: {question['correct_answer']}\n"
            f"Объяснение: {question['explanation']}"
        )
        
        # If this was the last question, show final results
        if current_index == len(questions) - 1:
            keyboard = build_results_keyboard()
            await query.message.edit_text(
                f"{result_text}\n\nТест завершен! Нажмите 'Показать результаты' для просмотра итогов.",
                reply_markup=keyboard
            )
        else:
            # Move to next question
            next_index = current_index + 1
            self.set_user_data(context, 'current_question_index', next_index)
            
            keyboard = build_continue_keyboard()
            await query.message.edit_text(
                f"{result_text}\n\nНажмите 'Продолжить' для следующего вопроса.",
                reply_markup=keyboard
            )

    async def handle_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle continue button callback."""
        query = update.callback_query
        await query.answer()
        
        questions = self.get_user_data(context).get('questions', [])
        current_index = self.get_user_data(context).get('current_question_index', 0)
        
        if not questions or current_index >= len(questions):
            logging.error("No questions found or invalid index")
            await query.message.edit_text(
                "Произошла ошибка. Пожалуйста, начните тест заново.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
        question = questions[current_index]
        keyboard = build_question_keyboard(current_index, len(questions))
        
        await query.message.edit_text(
            f"Вопрос {current_index + 1} из {len(questions)}:\n\n{question['question']}",
            reply_markup=keyboard
        )

    async def handle_show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle show results callback."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        topic = self.get_user_data(context).get('current_topic')
        
        if not topic:
            logging.error(f"No topic found for user {user_id}")
            await query.message.edit_text(
                "Произошла ошибка. Пожалуйста, начните тест заново.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
        # Get test results
        results = self.db.get_user_progress(user_id, topic)
        
        if not results:
            logging.error(f"No results found for user {user_id} and topic {topic}")
            await query.message.edit_text(
                "Произошла ошибка при получении результатов. Пожалуйста, попробуйте еще раз.",
                reply_markup=build_topic_selection_keyboard()
            )
            return
            
        # Calculate statistics
        total_questions = len(results)
        correct_answers = sum(1 for r in results if r['is_correct'])
        accuracy = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Format results text
        results_text = (
            f"📊 Результаты теста по теме '{topic}':\n\n"
            f"Всего вопросов: {total_questions}\n"
            f"Правильных ответов: {correct_answers}\n"
            f"Точность: {accuracy:.1f}%\n\n"
            f"Хотите попробовать еще раз?"
        )
        
        keyboard = build_topic_selection_keyboard()
        await query.message.edit_text(results_text, reply_markup=keyboard)
        
        # Clear user data
        self.clear_user_data(context)
        self.db.set_user_inactive(user_id) 