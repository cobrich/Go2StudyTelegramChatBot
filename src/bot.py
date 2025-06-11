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
from handlers.admin_handlers import AdminHandlers

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
    admin_handlers = AdminHandlers(db, question_service)
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("stop", command_handlers.stop))
    application.add_handler(CommandHandler("reset", command_handlers.reset))
    application.add_handler(CommandHandler("change_fio", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_grade", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_language", command_handlers.handle_text))
    application.add_handler(CommandHandler("myid", command_handlers.get_my_id))
    
    # Add admin command
    application.add_handler(CommandHandler("admin", admin_handlers.admin_panel))

    # Add text message handler for ReplyKeyboardMarkup and admin actions
    async def handle_text_with_admin(update: Update, context):
        # Сначала проверяем админские действия
        await admin_handlers.handle_admin_text(update, context)
        # Затем обычные действия
        await command_handlers.handle_text(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_with_admin))
    
    # Add document handler for admin PDF uploads
    async def handle_document_with_admin(update: Update, context):
        # Проверяем админские действия с документами
        await admin_handlers.handle_admin_document(update, context)
    
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document_with_admin))
    
    # Add admin callback handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.admin_panel,
        pattern="^admin_panel$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.students_menu,
        pattern="^admin_students$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.topics_menu,
        pattern="^admin_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.questions_menu,
        pattern="^admin_questions$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.admins_menu,
        pattern="^admin_admins$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_stats,
        pattern="^admin_stats$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_user_history,
        pattern="^admin_user_history$"
    ))
    
    # Student management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_student_start,
        pattern="^add_student$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_student_by_id_start,
        pattern="^add_student_by_id$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.list_students,
        pattern="^list_students$"
    ))
    
    # Topic management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_topic_start,
        pattern="^add_topic$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.list_topics,
        pattern="^list_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.merge_topics_start,
        pattern="^merge_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.merge_topics_select_target,
        pattern="^merge_source_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.merge_topics_confirm,
        pattern="^merge_target_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.merge_topics_execute,
        pattern="^merge_execute_"
    ))
    
    # Questions management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.upload_pdf_start,
        pattern="^upload_pdf$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.questions_stats,
        pattern="^questions_stats$"
    ))
    
    # Admin management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_admin_start,
        pattern="^add_admin$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.list_admins,
        pattern="^list_admins$"
    ))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_main_topic_selection,
        pattern="^main_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_back_to_main_topics,
        pattern="^back_to_main_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_topic_selection,
        pattern=r'^(topic_|retake_)'
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_answer,
        pattern="^answer_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_continue,
        pattern="^continue_test$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_show_results,
        pattern="^show_results$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_show_explanation,
        pattern="^show_expl_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_back_to_topics,
        pattern="^back_to_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_prev_question,
        pattern="^prev_question$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_next_question,
        pattern="^next_question$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_main_menu,
        pattern="^main_menu$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_back_to_results,
        pattern="^back_to_results$"
    ))
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 