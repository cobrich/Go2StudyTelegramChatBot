import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from config.constants import TELEGRAM_BOT_TOKEN
from services.database import Database
from services.question_service import QuestionService
from services.ai_service import AIService
from handlers.command_handlers import CommandHandlers
from handlers.callback_handlers import CallbackHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Initialize services
    db = Database()
    ai_service = AIService()
    question_service = QuestionService(db, ai_service)
    
    # Initialize handlers
    command_handlers = CommandHandlers(db, question_service)
    callback_handlers = CallbackHandlers(db, question_service)
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("stop", command_handlers.stop))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_topic_selection,
        pattern="^topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_answer,
        pattern="^answer_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_continue,
        pattern="^continue$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_show_results,
        pattern="^show_results$"
    ))
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 