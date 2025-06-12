import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.request import HTTPXRequest
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
    
    # Create custom request with increased timeouts
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )
    
    # Create separate request for get_updates with longer timeouts
    get_updates_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=60.0
    )
    
    # Create the Application with custom requests
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).get_updates_request(get_updates_request).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("stop", command_handlers.stop))
    application.add_handler(CommandHandler("reset", command_handlers.reset))
    application.add_handler(CommandHandler("skip", command_handlers.skip_phone))
    application.add_handler(CommandHandler("change_fio", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_grade", command_handlers.handle_text))
    application.add_handler(CommandHandler("change_language", command_handlers.handle_text))
    application.add_handler(CommandHandler("myid", command_handlers.get_my_id))
    
    # Add admin command
    application.add_handler(CommandHandler("admin", admin_handlers.admin_panel))

    # Add text message handler for ReplyKeyboardMarkup and admin actions
    async def handle_text_with_admin(update: Update, context):
        # Сначала проверяем админские действия
        admin_handled = await admin_handlers.handle_admin_text(update, context)
        # Если админ-обработчик не обработал сообщение, вызываем обычный обработчик
        if not admin_handled:
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
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_student_details,
        pattern="^student_details_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_student_full_stats,
        pattern="^student_full_stats_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_class_statistics,
        pattern="^class_statistics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_student_start,
        pattern="^remove_student$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_student_confirm,
        pattern="^remove_student_(username|id)_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_student_execute,
        pattern="^remove_student_execute_"
    ))
    
    # Student confirmation handler
    application.add_handler(CallbackQueryHandler(
        admin_handlers.confirm_add_student,
        pattern="^confirm_add_student_"
    ))
    
    # Student editing handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_student_start,
        pattern="^edit_student_[0-9]+$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_student_name_start,
        pattern="^edit_student_name_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_student_grade_start,
        pattern="^edit_student_grade_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_student_phone_start,
        pattern="^edit_student_phone_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_student_status_toggle,
        pattern="^edit_student_status_"
    ))
    
    # Topic management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.topics_menu,
        pattern="^admin_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_topic_start,
        pattern="^add_topic$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_custom_topic_start,
        pattern="^add_custom_topic$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.select_main_topic_for_new,
        pattern="^select_main_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.show_section_topics,
        pattern="^show_section_topics_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_base_topics_start,
        pattern="^add_base_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_base_topic_execute,
        pattern="^add_base_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_all_missing_topics_execute,
        pattern="^add_all_missing_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.list_topics,
        pattern="^list_topics$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_topic_start,
        pattern="^edit_topic$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_topic_select,
        pattern="^edit_topic_select_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_topic_name_start,
        pattern="^edit_topic_name_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_topic_desc_start,
        pattern="^edit_topic_desc_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_topic_toggle_status,
        pattern="^edit_topic_(activate|deactivate)_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_topic_start,
        pattern="^remove_topic$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_topic_confirm,
        pattern="^remove_topic_confirm_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_topic_execute,
        pattern="^remove_topic_execute_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_topic_permanent_confirm,
        pattern="^remove_topic_permanent_confirm_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_topic_permanent,
        pattern="^remove_topic_permanent_(?!confirm_)"
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
    application.add_handler(CallbackQueryHandler(
        admin_handlers.admins_menu,
        pattern="^admins_menu$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_admin_start,
        pattern="^remove_admin$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_admin_confirm,
        pattern="^remove_admin_confirm_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.remove_admin_execute,
        pattern="^remove_admin_execute_"
    ))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_main_topic_selection,
        pattern="^main_topic_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_handlers.handle_main_menu,
        pattern="^main_menu$"
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
        callback_handlers.handle_back_to_results,
        pattern="^back_to_results$"
    ))
    
    # Base structure management handlers
    application.add_handler(CallbackQueryHandler(
        admin_handlers.manage_base_structure_menu,
        pattern="^manage_base_structure$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.view_base_structure,
        pattern="^view_base_structure$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.add_base_section_start,
        pattern="^add_base_section$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_base_section_start,
        pattern="^edit_base_section$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_base_section_start,
        pattern="^delete_base_section$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.edit_base_section_select,
        pattern="^edit_base_section_select_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_base_section_confirm,
        pattern="^delete_base_section_confirm_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.delete_base_section_execute,
        pattern="^delete_base_section_execute_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.list_topics,
        pattern="^list_topics_page_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.refresh_topics_stats,
        pattern="^refresh_topics_stats$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handlers.detailed_topics_stats,
        pattern="^detailed_topics_stats$"
    ))
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 