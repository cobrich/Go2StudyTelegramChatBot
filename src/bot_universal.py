#!/usr/bin/env python3
"""
Universal Go2Study Bot - Works with any python-telegram-bot version
"""

import logging
from bot_compat import create_universal_bot
from config.constants import TELEGRAM_BOT_TOKEN
from services.database import Database
from services.question_service import QuestionService
from services.ai_service import AIService
from handlers.command_handlers import CommandHandlers
from handlers.callback_handlers import CallbackHandlers
from handlers.admin_handlers import AdminHandlers

# Import telegram handlers
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_handlers(application):
    """Setup all bot handlers"""
    # Initialize services
    db = Database()
    ai_service = AIService()
    question_service = QuestionService(db, ai_service)
    
    # Initialize handlers
    command_handlers = CommandHandlers(db, question_service)
    callback_handlers = CallbackHandlers(db, question_service)
    admin_handlers = AdminHandlers()
    
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
    async def handle_text_with_admin(update, context):
        # Сначала проверяем админские действия
        await admin_handlers.handle_admin_text(update, context)
        # Затем обычные действия
        await command_handlers.handle_text(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_with_admin))
    
    # Add document handler for admin PDF uploads
    async def handle_document_with_admin(update, context):
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
        admin_handlers.pdf_format_guide,
        pattern="^pdf_format_guide$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.questions_stats,
        pattern="^questions_stats$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.search_questions_start,
        pattern="^search_questions$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_questions_start,
        pattern="^delete_questions$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_questions_confirm,
        pattern="^delete_questions_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_questions_execute,
        pattern="^delete_questions_execute_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_single_question_start,
        pattern="^delete_single_question$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_single_question_confirm,
        pattern="^delete_single_question_confirm_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_single_question_execute,
        pattern="^delete_single_question_execute_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_question_start,
        pattern="^add_question$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_question_topic_selected,
        pattern="^add_question_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_question_start,
        pattern="^edit_question$"
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

def main():
    """Main function"""
    print("🚀 Starting Go2Study Bot (Universal Version)")
    
    # Create universal bot
    bot = create_universal_bot(TELEGRAM_BOT_TOKEN, setup_handlers)
    
    # Run bot (auto-detects version and uses appropriate method)
    bot.run()

if __name__ == '__main__':
    main()
