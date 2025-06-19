"""
Главный класс AdminHandlers, объединяющий все модули админ-панели.
"""

from .base import AdminBaseHandler
from .topics import TopicsHandler
from .sections import SectionsHandler
from .students import StudentsHandler
from .admins import AdminsHandler
from .questions import QuestionsHandler
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
        self.topics = TopicsHandler(db, question_service)
        self.sections = SectionsHandler(db, question_service)
        self.students = StudentsHandler(db, question_service)
        self.admins = AdminsHandler(db, question_service)
        self.questions = QuestionsHandler(db, question_service)
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

    async def remove_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления ученика."""
        return await self.students.remove_student_start(update, context)

    async def remove_student_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления ученика."""
        return await self.students.remove_student_confirm(update, context)

    async def remove_student_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления ученика."""
        return await self.students.remove_student_execute(update, context)

    async def edit_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования ученика."""
        return await self.students.edit_student_start(update, context)

    async def edit_student_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор параметра для редактирования ученика."""
        return await self.students.edit_student_select(update, context)

    async def edit_student_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения ФИО ученика."""
        return await self.students.edit_student_name_start(update, context)

    async def edit_student_grade_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения класса ученика."""
        return await self.students.edit_student_grade_start(update, context)

    async def edit_student_phone_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения телефона ученика."""
        return await self.students.edit_student_phone_start(update, context)

    async def edit_student_language_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения языка ученика."""
        return await self.students.edit_student_language_start(update, context)

    async def set_student_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Установка языка ученика."""
        return await self.students.set_student_language(update, context)

    async def edit_student_status_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса ученика."""
        return await self.students.edit_student_status_toggle(update, context)

    # Дополнительные методы студентов
    async def _add_student_to_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     student_user_id: int, username: str, fullname: str, 
                                     grade: int, admin_id: int) -> bool:
        """Добавление ученика в базу данных."""
        return await self.students._add_student_to_database(update, context, student_user_id, username, fullname, grade, admin_id)

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

    # Временные заглушки для тем
    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_start(update, context)
    
    async def edit_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_section_topics(update, context)
    
    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.remove_topic_start(update, context)
    
    async def remove_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.remove_section_topics(update, context)

    # Дополнительные методы тем
    async def select_main_topic_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.select_main_topic_for_new(update, context)
    
    async def show_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.show_section_topics(update, context)
    
    async def edit_topic_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_select(update, context)
    
    async def edit_topic_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_name_start(update, context)
    
    async def edit_topic_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_section_start(update, context)
    
    async def edit_topic_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"[DEBUG] edit_topic_section_select в __init__.py ВЫЗВАН!")
        return await self.topics.edit_topic_section_select(update, context)
    
    async def edit_topic_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.edit_topic_toggle_status(update, context)
    
    async def remove_topic_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.remove_topic_confirm(update, context)
    
    async def remove_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.topics.remove_topic_execute(update, context)
    
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

    # Дополнительные методы вопросов
    async def process_pdf_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.process_pdf_file(update, context)
    
    async def delete_questions_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_questions_confirm(update, context)
    
    async def delete_questions_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_questions_execute(update, context)
    
    async def add_question_topic_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.add_question_topic_selected(update, context)
    
    async def delete_single_question_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_single_question_confirm(update, context)
    
    async def delete_single_question_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.delete_single_question_execute(update, context)
    
    async def generate_ai_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.generate_ai_explanation_for_edit(update, context)
    
    async def manual_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.questions.manual_explanation_for_edit(update, context)

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

    # Дополнительные методы админов
    async def remove_admin_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.admins.remove_admin_confirm(update, context)
    
    async def remove_admin_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await self.admins.remove_admin_execute(update, context)

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
        elif action == 'student_grade':
            await self.students.handle_student_grade(update, context, text)
            return True
        elif action == 'student_by_id_grade':
            await self.students.handle_student_by_id_grade(update, context, text)
            return True
        
        # Обработка редактирования учеников
        elif action == 'edit_student_name':
            await self.students.handle_edit_student_name(update, context, text)
            return True
        elif action == 'edit_student_grade':
            await self.students.handle_edit_student_grade(update, context, text)
            return True
        elif action == 'edit_student_phone':
            await self.students.handle_edit_student_phone(update, context, text)
            return True
        
        # Обработка действий для тем
        elif action == 'add_topic':
            await self.topics.handle_add_topic(update, context, text)
            return True
        elif action == 'edit_topic_name':
            await self.topics.handle_edit_topic_name(update, context, text)
            return True
        
        # Обработка действий для вопросов
        elif action == 'search_questions':
            await self.questions.handle_search_questions(update, context, text)
            return True
        elif action == 'add_question_text':
            await self.questions.handle_add_question_text(update, context, text)
            return True
        elif action == 'add_question_option_a':
            await self.questions.handle_add_question_option_a(update, context, text)
            return True
        elif action == 'add_question_option_b':
            await self.questions.handle_add_question_option_b(update, context, text)
            return True
        elif action == 'add_question_option_c':
            await self.questions.handle_add_question_option_c(update, context, text)
            return True
        elif action == 'add_question_option_d':
            await self.questions.handle_add_question_option_d(update, context, text)
            return True
        elif action == 'add_question_correct':
            await self.questions.handle_add_question_correct(update, context, text)
            return True
        elif action == 'add_question_explanation':
            await self.questions.handle_add_question_explanation(update, context, text)
            return True
        elif action == 'edit_question_search':
            await self.questions.handle_edit_question_search(update, context, text)
            return True
        elif action == 'edit_question_id':
            await self.questions.handle_edit_question_id(update, context, text)
            return True
        elif action == 'edit_question_explanation':
            await self.questions.handle_edit_question_explanation(update, context, text)
            return True
        elif action == 'delete_single_question_search':
            await self.questions.handle_delete_single_question_search(update, context, text)
            return True
        
        # New edit question handlers
        elif action == 'edit_question_text':
            await self.questions.handle_edit_question_text(update, context, text)
            return True
        elif action == 'edit_question_correct':
            await self.questions.handle_edit_question_correct_answer(update, context, text)
            return True
        elif action == 'edit_question_options':
            await self.questions.handle_edit_question_options(update, context, text)
            return True
        elif action == 'edit_question_explanation':
            await self.questions.handle_edit_question_explanation_manual(update, context, text)
            return True
        
        # Обработка действий для админов
        elif action == 'add_admin':
            await self.admins.handle_add_admin(update, context, text)
            return True
        elif action == 'add_admin_username':
            await self.admins.handle_add_admin_username(update, context, text)
            return True
        elif action == 'add_admin_fullname':
            await self.admins.handle_add_admin_fullname(update, context, text)
            return True
        
        # Обработка действий для разделов
        elif context.user_data.get('awaiting_section_name'):
            await self.sections.handle_section_name(update, context)
            return True
        elif context.user_data.get('awaiting_section_new_name'):
            await self.sections.handle_section_new_name(update, context)
            return True
        elif action == 'add_section_name':
            await self.sections.handle_section_name(update, context)
            return True
        elif action == 'edit_section_name':
            await self.sections.handle_section_new_name(update, context)
            return True
        
        # Обработка действий для базовой структуры
        elif action == 'add_base_section_name':
            await self.handle_add_base_section_name(update, context, text)
            return True
        elif action == 'add_base_section_subtopics':
            await self.handle_add_base_section_subtopics(update, context, text)
            return True
        
        return False

    # === ОБРАБОТКА CALLBACK ДАННЫХ ===
    
    async def handle_student_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора языка при добавлении ученика."""
        return await self.students.handle_student_language_selection(update, context)

    # === ОБРАБОТЧИКИ БАЗОВОЙ СТРУКТУРЫ ===
    
    async def handle_add_base_section_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, section_name: str) -> None:
        """Обработка названия базового раздела."""
        await update.message.reply_text("🚧 Функция обработки названия базового раздела в разработке...")

    async def handle_add_base_section_subtopics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, subtopics_text: str) -> None:
        """Обработка подтем базового раздела."""
        await update.message.reply_text("🚧 Функция обработки подтем базового раздела в разработке...")

    # === ВРЕМЕННАЯ ЗАГЛУШКА ДЛЯ БАЗОВОЙ СТРУКТУРЫ ===
    
    async def manage_base_structure_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для базовой структуры."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Модуль базовой структуры в разработке...")

    # Дополнительные методы базовой структуры
    async def view_base_structure(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().view_base_structure(update, context)
    
    async def add_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().add_base_section_start(update, context)
    
    async def edit_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().edit_base_section_start(update, context)
    
    async def delete_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().delete_base_section_start(update, context)
    
    async def edit_base_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().edit_base_section_select(update, context)
    
    async def delete_base_section_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().delete_base_section_confirm(update, context)
    
    async def delete_base_section_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().delete_base_section_execute(update, context)
    
    async def confirm_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().confirm_add_student(update, context)

    # === ДЕЛЕГИРОВАНИЕ МЕТОДОВ УПРАВЛЕНИЯ РАЗДЕЛАМИ ===
    
    async def sections_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Главное меню управления разделами."""
        return await self.sections.sections_menu(update, context)
    
    async def list_all_sections(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех разделов."""
        return await self.sections.list_all_sections(update, context)
    
    async def add_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать добавление раздела."""
        return await self.sections.add_section_start(update, context)
    
    async def add_section_language_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбран язык для нового раздела."""
        return await self.sections.add_section_language_selected(update, context)
    
    async def edit_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать редактирование раздела."""
        return await self.sections.edit_section_start(update, context)
    
    async def edit_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбрать раздел для редактирования."""
        return await self.sections.edit_section_select(update, context)
    
    async def edit_section_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать изменение названия раздела."""
        return await self.sections.edit_section_name_start(update, context)
    
    async def edit_section_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключить статус раздела."""
        return await self.sections.edit_section_toggle_status(update, context)
    
    async def delete_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать удаление раздела."""
        return await self.sections.delete_section_start(update, context)
    
    async def delete_section_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтвердить удаление раздела."""
        return await self.sections.delete_section_confirm(update, context)
    
    async def delete_section_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнить удаление раздела."""
        return await self.sections.delete_section_execute(update, context)
    
    async def confirm_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return await super().confirm_add_student(update, context) 