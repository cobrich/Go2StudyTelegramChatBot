from telegram import Update
from telegram.ext import ContextTypes
from src.db.sync_database_facade import get_sync_database_facade
from src.services.question_service import QuestionService
from src.utils.keyboards import get_main_menu_markup
from src.utils.translations import get_message
import logging

class BaseHandler:
    def __init__(self):
        self.db = get_sync_database_facade()
        self.question_service = QuestionService()

    async def safe_answer_callback(self, query) -> None:
        """Safely answer callback query, ignoring expired queries."""
        try:
            await query.answer()
        except Exception:
            # Игнорируем ошибки с устаревшими callback queries
            pass

    async def check_user_active(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is active and handle accordingly."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        msg = update.effective_message
        if self.db.is_user_active(user_id):
            # Check if we have valid test data in context
            questions = context.user_data.get('questions', [])
            current_topic = context.user_data.get('current_topic')
            
            # If user is marked as active but has no test data, clear the stale session
            if not questions or not current_topic:
                logging.warning(f"User {user_id} is marked as active but has no test data. Clearing stale session.")
                self.db.set_user_inactive(user_id)
                self.clear_user_data(context)
                return False
            
            active_test_message = get_message('active_test_warning', user_language)
            await msg.reply_text(
                active_test_message,
                reply_markup=get_main_menu_markup(user_id)
            )
            return True
        return False

    def get_user_data(self, context: ContextTypes.DEFAULT_TYPE) -> dict:
        """Get user data from context."""
        return context.user_data

    def set_user_data(self, context: ContextTypes.DEFAULT_TYPE, key: str, value: any) -> None:
        """Set user data in context."""
        context.user_data[key] = value

    def clear_user_data(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear all user data from context."""
        context.user_data.clear()

    async def handle_error(self, update: Update, error: Exception) -> None:
        """Handle errors in a consistent way."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        logging.error(f"Error in handler: {error}")
        try:
            error_message = get_message('general_error', user_language)
            await update.message.reply_text(
                error_message,
                reply_markup=get_main_menu_markup(user_id)
            )
        except Exception as e:
            logging.error(f"Error sending error message: {e}") 