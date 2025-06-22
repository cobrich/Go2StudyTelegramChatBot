import asyncio
import logging
import os
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.request import HTTPXRequest
from src.config.constants import TELEGRAM_BOT_TOKEN
from src.db.sync_database_facade import get_sync_database_facade
from src.services.question_service import QuestionService
from src.services.ai_service import AIService
from src.handlers.command_handlers import CommandHandlers
from src.handlers.callback_handlers import CallbackHandlers
from src.handlers.admin.base import AdminBaseHandler
from src.handlers.admin.questions import QuestionsHandler
from src.handlers.admin.students import StudentsHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Create custom request with optimized timeouts
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=10.0,  # Уменьшено с 30 до 10 секунд
        read_timeout=15.0,     # Уменьшено с 30 до 15 секунд
        write_timeout=15.0,    # Уменьшено с 30 до 15 секунд
        pool_timeout=10.0      # Уменьшено с 30 до 10 секунд
    )
    
    # Create separate request for get_updates with reasonable timeouts
    get_updates_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=15.0,  # Уменьшено с 60 до 15 секунд
        read_timeout=30.0,     # Уменьшено с 60 до 30 секунд
        write_timeout=15.0,    # Уменьшено с 60 до 15 секунд
        pool_timeout=15.0      # Уменьшено с 60 до 15 секунд
    )
    
    # Create the Application with custom requests FIRST
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).get_updates_request(get_updates_request).build()
    
    # Initialize services
    db = get_sync_database_facade()
    ai_service = AIService()
    question_service = QuestionService(db, ai_service)
    
    # Initialize handlers
    command_handlers = CommandHandlers(db, question_service)
    callback_handlers = CallbackHandlers(db, question_service)
    
    # Initialize admin handlers
    admin_base = AdminBaseHandler()
    admin_questions = QuestionsHandler()
    admin_students = StudentsHandler()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("stop", command_handlers.stop))
    application.add_handler(CommandHandler("reset", command_handlers.reset))
    application.add_handler(CommandHandler("change_fio", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_grade", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_language", command_handlers.handle_text))
    application.add_handler(CommandHandler("myid", command_handlers.get_my_id))
    
    # Add admin command
    application.add_handler(CommandHandler("admin", admin_base.admin_panel))
    
    # Add text message handler for ReplyKeyboardMarkup and admin actions
    async def handle_text_with_admin(update: Update, context):
        # Сначала проверяем админские действия
        admin_handled = await admin_base.handle_admin_text(update, context)
        # Если админ-обработчик не обработал сообщение, вызываем обычный обработчик
        if not admin_handled:
            await command_handlers.handle_text(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_with_admin))
    
    # Add document handler for admin PDF uploads
    async def handle_document_with_admin(update: Update, context):
        # Проверяем админские действия с документами
        await admin_base.handle_admin_document(update, context)
    
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document_with_admin))
    
    # Add basic admin callback handlers
    application.add_handler(CallbackQueryHandler(admin_base.admin_panel, pattern="^admin_panel$"))
    
    # Students handlers
    application.add_handler(CallbackQueryHandler(admin_students.students_menu, pattern="^admin_students$"))
    application.add_handler(CallbackQueryHandler(admin_students.add_student_by_id_start, pattern="^add_student_by_id$"))
    application.add_handler(CallbackQueryHandler(admin_students.list_students, pattern="^list_students$"))
    application.add_handler(CallbackQueryHandler(admin_students.show_student_details, pattern="^student_details_"))
    application.add_handler(CallbackQueryHandler(admin_students.show_class_statistics, pattern="^class_statistics$"))
    application.add_handler(CallbackQueryHandler(admin_students.remove_student_start, pattern="^remove_student$"))
    application.add_handler(CallbackQueryHandler(admin_students.remove_student_confirm, pattern="^remove_student_confirm_"))
    application.add_handler(CallbackQueryHandler(admin_students.remove_student_execute, pattern="^remove_student_execute_"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_start, pattern="^edit_student_start$"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_select, pattern="^edit_student_select_"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_name_start, pattern="^edit_student_name_"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_grade_start, pattern="^edit_student_grade_"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_status_toggle, pattern="^edit_student_status_"))
    application.add_handler(CallbackQueryHandler(admin_students.edit_student_language_start, pattern="^edit_student_language_"))
    application.add_handler(CallbackQueryHandler(admin_students.set_student_language, pattern="^set_student_lang_(ru|kk)_"))
    
    # Questions handlers
    application.add_handler(CallbackQueryHandler(admin_questions.questions_menu, pattern="^admin_questions$"))
    application.add_handler(CallbackQueryHandler(admin_questions.upload_pdf_start, pattern="^upload_pdf$"))
    application.add_handler(CallbackQueryHandler(admin_questions.pdf_format_guide, pattern="^pdf_format_guide$"))
    application.add_handler(CallbackQueryHandler(admin_questions.questions_stats, pattern="^questions_stats$"))
    application.add_handler(CallbackQueryHandler(admin_questions.add_question_start, pattern="^add_question$"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_start, pattern="^edit_question$"))
    application.add_handler(CallbackQueryHandler(admin_questions.search_questions_start, pattern="^search_questions$"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_questions_start, pattern="^delete_questions$"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_single_question_start, pattern="^delete_single_question$"))
    
    # Question management specific handlers
    application.add_handler(CallbackQueryHandler(admin_questions.add_question_topic_selected, pattern="^add_question_topic_"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_questions_confirm, pattern="^delete_questions_idx_"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_questions_execute, pattern="^delete_questions_execute_confirmed$"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_single_question_confirm, pattern="^delete_single_question_confirm_"))
    application.add_handler(CallbackQueryHandler(admin_questions.delete_single_question_execute, pattern="^delete_single_question_execute_"))
    application.add_handler(CallbackQueryHandler(admin_questions.generate_ai_explanation_for_edit, pattern="^generate_ai_explanation_"))
    application.add_handler(CallbackQueryHandler(admin_questions.manual_explanation_for_edit, pattern="^manual_explanation_"))
    
    # Question editing handlers
    application.add_handler(CallbackQueryHandler(admin_questions.handle_edit_question_id, pattern="^edit_question_select_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_topic_start, pattern="^edit_question_topic_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_topic_select, pattern="^edit_topic_select_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_text_start, pattern="^edit_question_text_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_correct_start, pattern="^edit_question_correct_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_options_start, pattern="^edit_question_options_"))
    application.add_handler(CallbackQueryHandler(admin_questions.edit_question_explanation_start, pattern="^edit_question_explanation_"))
    
    # Add main callback handlers
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback, pattern="^(?!admin_|student_|edit_|delete_|add_|upload_|search_|generate_|manual_|confirm_|remove_|set_|class_|list_|questions_|pdf_|show_)"))
    
    # Database tables will be initialized lazily on first access
    logger.info("Bot starting - database tables will be initialized on first access...")
    
    # Run the bot until the user presses Ctrl-C
    # Используем синхронный метод для совместимости с python-telegram-bot 20.x
    try:
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
        raise

if __name__ == '__main__':
    main() 