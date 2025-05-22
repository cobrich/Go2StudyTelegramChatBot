from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging
from handlers.base_handler import BaseHandler
from utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard
from config.constants import HELP_TEXT, TOPICS

class CommandHandlers(BaseHandler):
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Регистрируем пользователя в базе, если его нет
        self.db.register_user(user.id, user.username)

        # Clear previous session data
        self.clear_user_data(context)
        logging.info(f"User {user.id} ({user.username}) executed /start. User data cleared for chat {chat_id}.")
        self.set_user_data(context, 'session_started', True)

        self.db.set_all_users_inactive()

        welcome_text = f"👋 Привет, {user.mention_html()}! Я бот для изучения математики. Выбери действие:"

        try:
            # Try to remove any existing keyboard
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬",
                reply_markup=ReplyKeyboardRemove()
            )
            logging.info(f"Sent ReplyKeyboardRemove to chat {chat_id} as part of /start sequence.")
        except Exception as e:
            logging.error(f"Error sending ReplyKeyboardRemove during /start for chat {chat_id}: {e}")

        try:
            await update.message.reply_html(
                text=welcome_text,
                reply_markup=self.main_menu_markup
            )
            logging.info(f"Welcome message with main_menu_markup sent to chat {chat_id} for user {user.id}.")
        except Exception as e:
            logging.error(f"Error sending welcome message with main_menu_markup during /start for chat {chat_id}: {e}")
            try:
                await update.message.reply_text(
                    "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова."
                )
            except Exception as e_fallback:
                logging.error(f"Error sending fallback error message during /start for chat {chat_id}: {e_fallback}")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_id = user.id if user else None

        # Всегда сбрасываем активность и очищаем user_data
        if user_id:
            self.db.set_user_inactive(user_id)
            self.clear_user_data(context)
            self.db.delete_all_user_data(user_id)

        if not user:
            logging.warning("stop_command received update without effective_user.")
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Не удалось определить пользователя для остановки. Пожалуйста, убедитесь, что вы отправили команду из чата с ботом."
                )
            return

        response_text = (
            f"🗑️ Все ваши данные были удалены из моей памяти, {user.mention_html()}.\n\n"
            "Я не могу удалить историю этого чата самостоятельно, но вы можете сделать это вручную, если хотите.\n\n"
            "Если вы захотите начать заново, просто отправьте /start."
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e_remove_keyboard:
            logging.warning(f"Could not remove reply keyboard for user {user_id} during /stop: {e_remove_keyboard}")

        await context.bot.send_message(
            chat_id=chat_id,
            text=response_text,
            parse_mode='HTML'
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        # If user is in a test, block main menu actions
        if self.db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Для выбора других опций завершите тест или вернитесь к темам через кнопку 'Назад к темам' в тесте.",
                reply_markup=None
            )
            return
        if text == "📚 Выбрать тему и начать":
            # Сначала убираем обычную клавиатуру
            await update.message.reply_text(
                "💬",
                reply_markup=ReplyKeyboardRemove()
            )
            # Затем отправляем сообщение с inline-кнопками
            await update.message.reply_text(
                "Выберите тему:",
                reply_markup=build_topic_selection_keyboard()
            )
        elif text == "📊 Мой прогресс":
            total_tests, avg_percentage = self.db.get_user_progress(user_id)
            if avg_percentage is None:
                avg_percentage = 0.0
            recent_topics = self.db.get_recent_topics(user_id, limit=5)
            error_topics = self.db.get_error_topics(user_id)

            progress_text = f"📊 Ваш прогресс:\n\n"
            progress_text += f"Всего тестов: {total_tests//10}\n"
            progress_text += f"Средний результат: {avg_percentage:.1f}%\n\n"

            if recent_topics:
                # Считаем количество прохождений для каждой уникальной темы (по последним 20 попыткам)
                topic_counts = {}
                topic_order = []
                for t in recent_topics:
                    topic = t[0]
                    if topic not in topic_counts:
                        topic_counts[topic] = 1
                        topic_order.append(topic)
                    else:
                        topic_counts[topic] += 1
                # Показываем только последние 5 уникальных тем
                progress_text += "Недавние темы: " + ", ".join([f"{topic} ({topic_counts[topic]})" for topic in topic_order[:5]]) + "\n"
            if error_topics:
                progress_text += "Темы с ошибками: " + ", ".join([f"{t[0]} ({t[1]})" for t in error_topics]) + "\n"

            await update.message.reply_text(progress_text)
        elif text == "❓ Помощь":
            await update.message.reply_text(HELP_TEXT)
        else:
            await update.message.reply_text("Пожалуйста, выберите действие из меню.", reply_markup=self.main_menu_markup)

    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        topic_index = query.data.replace('topic_', '')
        try:
            topic_index = int(topic_index)
            topic = TOPICS[topic_index]
        except (ValueError, IndexError):
            logging.error(f"Invalid topic selected: {topic_index}")
            await query.message.edit_text(
                "Произошла ошибка при выборе темы. Пожалуйста, попробуйте еще раз.",
                reply_markup=build_topic_selection_keyboard()
            )
            return

        # Handle topic selection
        # ... (rest of the method remains unchanged)

        # ... (rest of the method remains unchanged) 