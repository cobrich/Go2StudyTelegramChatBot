"""
Admin Base Handler

Provides base functionality for admin operations.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.db.sync_database_facade import get_sync_database_facade
from src.utils.translations import get_message
from src.services.pdf_processor import PDFProcessor
from src.utils.message_manager import MessageManager

logger = logging.getLogger(__name__)

class AdminBaseHandler:
    """Базовый класс для всех админ-обработчиков."""
    
    def __init__(self, db, question_service, ai_service):
        # Используем database facade вместо прямого SQLite подключения
        self.db = db
        self.question_service = question_service
        self.ai_service = ai_service
        self.message_manager = MessageManager(self.db)
    
    async def safe_answer_callback(self, query) -> None:
        """Безопасно отвечаем на callback query."""
        try:
            await query.answer()
        except Exception as e:
            logging.warning(f"Could not answer callback query: {e}")
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Главная админ-панель."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            if update.message:
                await update.message.reply_text("❌ У вас нет прав администратора.")
            else:
                await update.callback_query.answer("❌ У вас нет прав администратора.")
            return
        
        query = update.callback_query
        if query:
            await self.safe_answer_callback(query)
        
        # Получаем статистику для админ-панели
        try:
            students_count = len(self.db.get_all_allowed_users())
            topics = self.db.get_all_topics(active_only=True)
            topics_count = len(topics)
            questions = self.db.get_all_questions()
            questions_count = len(questions)
            admins = self.db.get_all_admins()
            admins_count = len(admins)
        except Exception as e:
            logging.error(f"Error getting admin panel stats: {e}")
            students_count = topics_count = questions_count = admins_count = 0
        
        text = f"🔧 <b>Панель администратора</b>\n\n"
        text += f"📊 <b>Статистика:</b>\n"
        text += f"👥 Учеников: {students_count}\n"
        text += f"📚 Тем: {topics_count}\n"
        text += f"❓ Вопросов: {questions_count}\n"
        text += f"👨‍💼 Админов: {admins_count}\n\n"
        text += f"Выберите раздел для управления:"
        
        is_super = self.db.is_super_admin(user_id)
        
        keyboard = [
            [InlineKeyboardButton("👥 Управление учениками", callback_data="admin_students")],
            [InlineKeyboardButton("📑 Управление разделами", callback_data="admin_sections")],
            [InlineKeyboardButton("📚 Управление темами", callback_data="admin_topics")],
            [InlineKeyboardButton("❓ Управление вопросами", callback_data="admin_questions")],
        ]
        
        # Функции только для суперадмина
        if is_super:
            keyboard.append([InlineKeyboardButton("👑 Управление админами", callback_data="admin_admins")])
        
        keyboard.extend([
            [InlineKeyboardButton("📊 Статистика и отчеты", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Назад к выбору тем", callback_data="back_to_main")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.message_manager.send_managed_message(
            update=update,
            context=context,
            text=text,
            reply_markup=reply_markup,
            message_type="admin_panel"
        )

    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка текстовых сообщений в админ-режиме."""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if not self.db.is_admin(user_id):
            return False

        # Обработка входа в админ-панель по текстовой кнопке
        if text in ['Панель администратора', 'Әкімші панелі']:
            await self.admin_panel(update, context)
            return True
        
        action = context.user_data.get('admin_action')
        if not action:
            return False
            
        # text = update.message.text.strip() # Already defined
        
        # Делегируем обработку в соответствующие модули
        if action in ['search_questions', 'add_question_text', 'add_question_option_a', 
                      'add_question_option_b', 'add_question_option_c', 'add_question_option_d',
                      'add_question_correct', 'add_question_explanation', 'edit_question_search',
                      'edit_question_id', 'edit_question_explanation', 'delete_single_question_search',
                      'edit_question_text', 'edit_question_correct', 'edit_question_options']:
            from .questions import QuestionsHandler
            questions_handler = QuestionsHandler(self.db, self.question_service, self.ai_service)
            
            if action == 'search_questions':
                await questions_handler.handle_search_questions(update, context, text)
            elif action == 'add_question_text':
                await questions_handler.handle_add_question_text(update, context, text)
            elif action == 'add_question_option_a':
                await questions_handler.handle_add_question_option_a(update, context, text)
            elif action == 'add_question_option_b':
                await questions_handler.handle_add_question_option_b(update, context, text)
            elif action == 'add_question_option_c':
                await questions_handler.handle_add_question_option_c(update, context, text)
            elif action == 'add_question_option_d':
                await questions_handler.handle_add_question_option_d(update, context, text)
            elif action == 'add_question_correct':
                await questions_handler.handle_add_question_correct(update, context, text)
            elif action == 'add_question_explanation':
                await questions_handler.handle_add_question_explanation(update, context, text)
            elif action == 'edit_question_search':
                await questions_handler.handle_edit_question_search(update, context, text)
            elif action == 'edit_question_id':
                await questions_handler.handle_edit_question_id(update, context, text)
            elif action == 'edit_question_explanation':
                await questions_handler.handle_edit_question_explanation_manual(update, context, text)
            elif action == 'edit_question_text':
                await questions_handler.handle_edit_question_text(update, context, text)
            elif action == 'edit_question_correct':
                await questions_handler.handle_edit_question_correct_answer(update, context, text)
            elif action == 'edit_question_options':
                await questions_handler.handle_edit_question_options(update, context, text)
            elif action == 'delete_single_question_search':
                await questions_handler.handle_delete_single_question_search(update, context, text)
            
            return True
        
        # Обработка для студентов
        if action in ['add_student_by_id', 'student_by_id_fullname', 'student_by_id_grade',
                      'edit_student_name', 'edit_student_grade']:
            from .students import StudentsHandler
            students_handler = StudentsHandler(self.db, self.question_service, self.ai_service)
            
            if action == 'add_student_by_id':
                await students_handler.handle_add_student_by_id(update, context, text)
            elif action == 'student_by_id_fullname':
                await students_handler.handle_student_by_id_fullname(update, context, text)
            elif action == 'student_by_id_grade':
                await students_handler.handle_student_by_id_grade(update, context, text)
            elif action == 'edit_student_name':
                await students_handler.handle_edit_student_name(update, context, text)
            elif action == 'edit_student_grade':
                await students_handler.handle_edit_student_grade(update, context, text)
            
            return True
        
        # Обработка для разделов
        if action in ['add_section_name', 'edit_section_name']:
            from .sections import SectionsHandler
            sections_handler = SectionsHandler(self.db, self.question_service, self.ai_service)
            
            if action == 'add_section_name':
                await sections_handler.handle_section_name(update, context)
            elif action == 'edit_section_name':
                await sections_handler.handle_section_new_name(update, context)
            
            return True
        
        # Обработка для тем
        if action in ['add_topic', 'add_topic_name', 'edit_topic_name']:
            from .topics import TopicsHandler
            topics_handler = TopicsHandler(self.db, self.question_service, self.ai_service)
            
            if action in ['add_topic', 'add_topic_name']:
                await topics_handler.handle_add_topic(update, context, text)
            elif action == 'edit_topic_name':
                await topics_handler.handle_edit_topic_name(update, context, text)
            
            return True
        
        # Обработка для админов
        if action in ['add_admin', 'add_admin_username', 'add_admin_fullname']:
            from .admins import AdminsHandler
            admins_handler = AdminsHandler(self.db, self.question_service, self.ai_service)
            
            if action == 'add_admin':
                await admins_handler.handle_add_admin(update, context, text)
            elif action == 'add_admin_username':
                await admins_handler.handle_add_admin_username(update, context, text)
            elif action == 'add_admin_fullname':
                await admins_handler.handle_add_admin_fullname(update, context, text)
            
            return True
        
        return False

    async def handle_admin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка документов в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        # Проверяем, ожидается ли PDF файл
        if context.user_data.get('admin_action') == 'upload_pdf':
            from .questions import QuestionsHandler
            questions_handler = QuestionsHandler(self.db, self.question_service, self.ai_service)
            await questions_handler.process_pdf_file(update, context) 