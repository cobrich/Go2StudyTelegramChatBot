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

        # Clear previous session data
        self.clear_user_data(context)
        logging.info(f"User {user.id} ({user.username}) executed /start. User data cleared for chat {chat_id}.")
        self.set_user_data(context, 'session_started', True)

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

        if not user:
            logging.warning("stop_command received update without effective_user.")
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Не удалось определить пользователя для остановки. Пожалуйста, убедитесь, что вы отправили команду из чата с ботом."
                )
            return

        user_id = user.id

        # Check if session was started
        if not self.get_user_data(context).get('session_started'):
            logging.info(f"User {user_id} ({user.username}) executed /stop before starting a session in chat {chat_id}.")
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Бот еще не был активирован командой /start. "
                    "Для вас нет сохраненных данных. Чтобы начать, отправьте /start."
                )
            )
            return

        # If session was started, continue with data deletion
        logging.info(f"User {user_id} ({user.username}) executed /stop command in chat {chat_id} (session was active).")

        # Delete all user data
        self.db.set_user_inactive(user_id)
        success = self.db.delete_all_user_data(user_id)

        if success:
            logging.info(f"Successfully deleted all data for user {user_id} from the database.")
            self.clear_user_data(context)
            logging.info(f"Cleared context.user_data for user {user_id}.")
            
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
        else:
            logging.error(f"Failed to delete data for user {user_id} from the database.")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при удалении ваших данных. Пожалуйста, попробуйте еще раз или свяжитесь с администратором, если проблема сохранится."
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        if text == "📚 Выбрать тему и начать":
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
            progress_text += f"Всего тестов: {total_tests}\n"
            progress_text += f"Средний результат: {avg_percentage:.1f}%\n\n"

            if recent_topics:
                progress_text += "Последние темы и результаты:\n"
                for topic, percent, timestamp in recent_topics:
                    progress_text += f"- {topic}: {percent:.1f}% ({timestamp})\n"
                progress_text += "\n"
            if error_topics:
                progress_text += "Темы с ошибками:\n"
                for topic, count in error_topics:
                    progress_text += f"- {topic}: {count} ошибок\n"
            else:
                progress_text += "Ошибок не найдено!\n"

            await update.message.reply_text(progress_text, reply_markup=self.main_menu_markup)
        elif text == "❓ Помощь":
            await update.message.reply_text(HELP_TEXT, reply_markup=self.main_menu_markup)
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