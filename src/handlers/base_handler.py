from telegram import Update
from telegram.ext import ContextTypes
from src.services.database import Database
from src.services.question_service import QuestionService
from src.utils.keyboards import get_main_menu_markup
import logging

class BaseHandler:
    def __init__(self, db: Database, question_service: QuestionService):
        self.db = db
        self.question_service = question_service
        self.main_menu_markup = get_main_menu_markup()

    async def check_user_active(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is active and handle accordingly."""
        user_id = update.effective_user.id
        if self.db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. "
                "Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста.",
                reply_markup=self.main_menu_markup
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
        logging.error(f"Error in handler: {error}")
        try:
            await update.message.reply_text(
                "Произошла ошибка. Пожалуйста, попробуйте еще раз или используйте /start для перезапуска бота.",
                reply_markup=self.main_menu_markup
            )
        except Exception as e:
            logging.error(f"Error sending error message: {e}") 