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
from src.config.constants import TELEGRAM_BOT_TOKEN
from src.services.database import get_database_instance
from src.services.question_service import QuestionService
from src.services.ai_service import AIService
from src.handlers.command_handlers import CommandHandlers
from src.handlers.callback_handlers import CallbackHandlers
from src.handlers.admin import AdminHandlers
from src.init_app import initialize_app_if_needed
import sys
import threading
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def keep_db_alive():
    from src.db.sync_connection_manager import get_sync_connection_manager
    conn_manager = get_sync_connection_manager()
    while True:
        try:
            conn_manager.fetch_val("SELECT 1")
            logger.info("🟢 DB keep-alive ping successful")
        except Exception as e:
            logger.warning(f"🔴 DB keep-alive ping failed: {e}")
        time.sleep(120)  # 2 минут

def main() -> None:
    """Start the bot."""
    try:
        logger.info("🚀 Starting Go2Study Bot...")
        
        # При запуске приложения проверяем, нужно ли выполнить первичную настройку
        logger.info("🔧 Checking if app initialization is needed...")
        initialize_app_if_needed()
        logger.info("✅ App initialization check completed")

        # Initialize services
        logger.info("📊 Initializing database connection...")
        db = get_database_instance()
        # Логируем параметры подключения к БД
        try:
            from src.db.sync_connection_manager import get_sync_connection_manager
            conn_manager = get_sync_connection_manager()
            params = conn_manager._connection_params
            logger.info(f"🔗 DB connection params: host={params.get('host')}, port={params.get('port')}, db={params.get('database')}, user={params.get('user')}")
        except Exception as e:
            logger.warning(f"Не удалось получить параметры подключения к БД: {e}")
        logger.info("✅ Database connection established")
        
        logger.info("🤖 Initializing AI service...")
        ai_service = AIService()
        logger.info("✅ AI service initialized")
        
        logger.info("❓ Initializing question service...")
        question_service = QuestionService(db, ai_service)
        logger.info("✅ Question service initialized")
    
        # Initialize handlers
        logger.info("🎮 Initializing handlers...")
        command_handlers = CommandHandlers(db, question_service)
        callback_handlers = CallbackHandlers(db, question_service)
        admin_handlers = AdminHandlers(db, question_service)
        logger.info("✅ All handlers initialized")
    
        # Create custom request with increased timeouts
        logger.info("🌐 Creating HTTP request configuration...")
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
        logger.info("🔧 Building Telegram application...")
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).get_updates_request(get_updates_request).build()
        logger.info("✅ Telegram application built successfully")
    
        # Add command handlers
        logger.info("📝 Adding command handlers...")
        application.add_handler(CommandHandler("start", command_handlers.start))
        application.add_handler(CommandHandler("stop", command_handlers.stop))
        application.add_handler(CommandHandler("reset", command_handlers.reset))
        application.add_handler(CommandHandler("change_fio", command_handlers.handle_text))
        application.add_handler(CommandHandler("change_grade", command_handlers.handle_text))
        application.add_handler(CommandHandler("change_language", command_handlers.handle_text))
        application.add_handler(CommandHandler("language", command_handlers.language_menu))
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
        logger.info("🔗 Adding admin callback handlers...")
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
            admin_handlers.show_class_statistics,
            pattern="^class_statistics$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_student_start,
            pattern="^remove_student$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_student_confirm,
            pattern="^remove_student_confirm_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_student_execute,
            pattern="^remove_student_execute_"
        ))
    
        # Student editing handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_student_start,
            pattern="^edit_student_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_student_select,
            pattern="^edit_student_select_"
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
            admin_handlers.edit_student_status_toggle,
            pattern="^edit_student_status_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_student_language_start,
            pattern="^edit_student_language_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.set_student_language,
            pattern="^set_student_lang_(ru|kk)_"
        ))
    
        # Topic management handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.topics_menu,
            pattern="^admin_topics$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.sections_menu,
            pattern="^admin_sections$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.add_topic_start,
            pattern="^add_topic$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.list_topics,
            pattern="^list_topics$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.show_section_topics,
            pattern="^show_section_topics_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.sections_menu,
            pattern="^sections_menu$"
        ))
        # Sections management handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.list_all_sections,
            pattern="^list_all_sections$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.add_section_start,
            pattern="^add_section_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.add_section_language_selected,
            pattern="^add_section_lang_(ru|kk)$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_section_start,
            pattern="^edit_section_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_section_select,
            pattern="^edit_section_select_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_section_name_start,
            pattern="^edit_section_name$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_section_toggle_status,
            pattern="^edit_section_toggle_status$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.delete_section_start,
            pattern="^delete_section_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.delete_section_confirm,
            pattern="^delete_section_confirm_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.delete_section_execute,
            pattern="^delete_section_execute$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.select_main_topic_for_new,
            pattern="^select_main_topic_"
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
            pattern="^delete_questions_idx_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.delete_questions_execute,
            pattern="^delete_questions_execute_confirmed$"
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
            admin_handlers.add_question_main_topic_selected,
            pattern="^add_question_main_topic_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.add_question_topic_selected,
            pattern="^add_question_topic_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_start,
            pattern="^edit_question$"
        ))
    
        # Edit question handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.handle_edit_question_id,
            pattern="^edit_question_select_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_topic_start,
            pattern="^edit_question_topic_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_topic_select,
            pattern="^edit_question_topic_select_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_text_start,
            pattern="^edit_question_text_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_correct_start,
            pattern="^edit_question_correct_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_options_start,
            pattern="^edit_question_options_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_explanation_start,
            pattern="^edit_question_explanation_"
        ))
    
        # AI explanation generation handlers for question editing
        application.add_handler(CallbackQueryHandler(
            admin_handlers.generate_ai_explanation_for_edit,
            pattern="^generate_ai_explanation_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.manual_explanation_for_edit,
            pattern="^manual_explanation_"
        ))
    
        # Change section handlers for questions
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_change_section_start,
            pattern="^edit_question_change_section_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_section_select,
            pattern="^edit_question_section_select_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_question_move_to_topic,
            pattern="^edit_question_move_to_topic_"
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
            callback_handlers.handle_back_to_main_topics,
            pattern="^back_to_main$"
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
        application.add_handler(CallbackQueryHandler(
            callback_handlers.handle_retry_random_test,
            pattern="^retry_random_test$"
        ))
    
        # Additional topic handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.list_topics,
            pattern="^list_topics_page_"
        ))
    
        # Topic management handlers
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_topic_start,
            pattern="^edit_topic_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_section_topics,
            pattern="^edit_section_topics_"
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
            admin_handlers.edit_topic_section_select,
            pattern="^edit_topic_section_select_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_topic_section_start,
            pattern="^edit_topic_section_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.edit_topic_toggle_status,
            pattern="^edit_topic_toggle_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_topic_start,
            pattern="^remove_topic$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_topic_start,
            pattern="^remove_topic_start$"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_section_topics,
            pattern="^remove_section_topics_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_topic_confirm,
            pattern="^remove_topic_confirm_"
        ))
        application.add_handler(CallbackQueryHandler(
            admin_handlers.remove_topic_execute,
            pattern="^remove_topic_execute_"
        ))
    
        # Language change handlers
        application.add_handler(CallbackQueryHandler(
            command_handlers.handle_language_change_callback,
            pattern="^change_lang_(ru|kk)$"
        ))
        application.add_handler(CallbackQueryHandler(
            command_handlers.handle_language_change_confirm,
            pattern="^confirm_lang_(ru|kk)$"
        ))
    
        # Start the Bot
        logger.info("🎯 Starting bot polling...")
        # Запускаем keep-alive поток для Neon
        threading.Thread(target=keep_db_alive, daemon=True).start()
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Critical error starting the bot: {e}")
        logger.error("Stack trace:", exc_info=True)
        # Exit with error code to signal Railway that the application failed
        sys.exit(1)

if __name__ == '__main__':
    main() 