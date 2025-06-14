"""
Главный класс AdminHandlers, объединяющий все модули админ-панели.
"""

from .base import AdminBaseHandler
from .students import StudentsHandler
from .topics import TopicsHandler
from .questions import QuestionsHandler
from .admins import AdminsHandler
from .stats import StatsHandler
from telegram import Update
from telegram.ext import ContextTypes
from services.database import Database
from services.question_service import QuestionService

class AdminHandlers(AdminBaseHandler):
    """Главный класс для обработки всех админ-функций."""
    
    def __init__(self, db: Database, question_service: QuestionService):
        super().__init__(db, question_service)
        
        # Инициализируем все модули
        self.students = StudentsHandler(db, question_service)
        self.topics = TopicsHandler(db, question_service)
        self.questions = QuestionsHandler(db, question_service)
        self.admins = AdminsHandler(db, question_service)
        self.stats = StatsHandler(db, question_service)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ УПРАВЛЕНИЯ УЧЕНИКАМИ ===
    
    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        return await self.students.students_menu(update, context)
    
    async def add_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по username."""
        return await self.students.add_student_start(update, context)
    
    async def add_student_by_id_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по ID."""
        return await self.students.add_student_by_id_start(update, context)

    async def list_students(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех учеников с краткой статистикой."""
        return await self.students.list_students(update, context)

    async def show_student_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать детальную статистику ученика."""
        return await self.students.show_student_details(update, context)

    async def show_student_full_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать полную статистику ученика."""
        return await self.students.show_student_full_stats(update, context)

    async def show_class_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику по классам."""
        return await self.students.show_class_statistics(update, context)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ УПРАВЛЕНИЯ ТЕМАМИ ===
    
    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        return await self.topics.topics_menu(update, context)
    
    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы."""
        return await self.topics.add_topic_start(update, context)
    
    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем."""
        return await self.topics.list_topics(update, context)
    
    async def detailed_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Детальная статистика по темам."""
        return await self.topics.detailed_topics_stats(update, context)
    
    async def refresh_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обновить статистику тем."""
        return await self.topics.refresh_topics_stats(update, context)

    # Временные заглушки для тем
    async def add_custom_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.add_custom_topic_start(update, context)
    
    async def add_base_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.add_base_topics(update, context)
    
    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_start(update, context)
    
    async def merge_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.merge_topics_start(update, context)
    
    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.remove_topic_start(update, context)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ УПРАВЛЕНИЯ ВОПРОСАМИ ===
    
    async def questions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления вопросами."""
        return await self.questions.questions_menu(update, context)
    
    async def upload_pdf_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало загрузки PDF."""
        return await self.questions.upload_pdf_start(update, context)
    
    async def pdf_format_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Руководство по формату PDF."""
        return await self.questions.pdf_format_guide(update, context)
    
    async def questions_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Статистика вопросов."""
        return await self.questions.questions_stats(update, context)

    # Временные заглушки для вопросов
    async def add_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.add_question_start(update, context)
    
    async def edit_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.edit_question_start(update, context)
    
    async def search_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.search_questions_start(update, context)
    
    async def delete_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_questions_start(update, context)
    
    async def delete_single_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_single_question_start(update, context)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ УПРАВЛЕНИЯ АДМИНАМИ ===
    
    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами."""
        return await self.admins.admins_menu(update, context)
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа."""
        return await self.admins.add_admin_start(update, context)
    
    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        return await self.admins.list_admins(update, context)

    # Временные заглушки для админов
    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.admins.remove_admin_start(update, context)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ СТАТИСТИКИ ===
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать общую статистику."""
        return await self.stats.show_stats(update, context)
    
    async def show_user_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать историю пользователей."""
        return await self.stats.show_user_history(update, context)

    # === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
    
    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка текстовых сообщений в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return False
        
        action = context.user_data.get('admin_action')
        if not action:
            return False
            
        text = update.message.text.strip()
        
        # Обработка действий для учеников
        if action == 'add_student':
            await self.students.handle_add_student(update, context, text)
            return True
        elif action == 'add_student_by_id':
            await self.students.handle_add_student_by_id(update, context, text)
            return True
        elif action == 'student_fullname':
            await self.students.handle_student_fullname(update, context, text)
            return True
        elif action == 'student_by_id_fullname':
            await self.students.handle_student_by_id_fullname(update, context, text)
            return True
        elif action == 'student_phone':
            await self.students.handle_student_phone(update, context, text)
            return True
        elif action == 'student_by_id_phone':
            await self.students.handle_student_by_id_phone(update, context, text)
            return True
        elif action == 'student_grade':
            await self.students.handle_student_grade(update, context, text)
            return True
        elif action == 'student_by_id_grade':
            await self.students.handle_student_by_id_grade(update, context, text)
            return True
        
        # TODO: Добавить обработку других модулей
        
        return False

    # === ОБРАБОТКА CALLBACK ДАННЫХ ===
    
    async def handle_student_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора языка при добавлении ученика."""
        return await self.students.handle_student_language_selection(update, context)

    # === ВРЕМЕННАЯ ЗАГЛУШКА ДЛЯ БАЗОВОЙ СТРУКТУРЫ ===
    
    async def manage_base_structure_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для базовой структуры."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Модуль базовой структуры в разработке...") 