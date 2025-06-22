"""
Модуль админ-хендлеров.
Содержит все обработчики для админ-панели.
"""

from .base import AdminBaseHandler
from .questions import QuestionsHandler
from .students import StudentsHandler
from .topics import TopicsHandler
from .sections import SectionsHandler
from .stats import StatsHandler
from .admins import AdminsHandler

class AdminHandlers:
    """Unified admin handlers class that combines all admin functionality."""
    
    def __init__(self, db, question_service):
        self.db = db
        self.question_service = question_service
        
        # Initialize all admin handlers
        self.base = AdminBaseHandler()
        self.questions = QuestionsHandler()
        self.students = StudentsHandler()
        self.topics = TopicsHandler()
        self.sections = SectionsHandler()
        self.stats = StatsHandler()
        self.admins = AdminsHandler()
    
    # Delegate methods to appropriate handlers
    def admin_panel(self, update, context):
        return self.base.admin_panel(update, context)
    
    def handle_admin_text(self, update, context):
        return self.base.handle_admin_text(update, context)
    
    def handle_admin_document(self, update, context):
        return self.base.handle_admin_document(update, context)
    
    # Students methods
    def students_menu(self, update, context):
        return self.students.students_menu(update, context)
    
    def add_student_by_id_start(self, update, context):
        return self.students.add_student_by_id_start(update, context)
    
    def list_students(self, update, context):
        return self.students.list_students(update, context)
    
    def show_student_details(self, update, context):
        return self.students.show_student_details(update, context)
    
    def show_class_statistics(self, update, context):
        return self.students.show_class_statistics(update, context)
    
    def remove_student_start(self, update, context):
        return self.students.remove_student_start(update, context)
    
    def remove_student_confirm(self, update, context):
        return self.students.remove_student_confirm(update, context)
    
    def remove_student_execute(self, update, context):
        return self.students.remove_student_execute(update, context)
    
    def edit_student_start(self, update, context):
        return self.students.edit_student_start(update, context)
    
    def edit_student_select(self, update, context):
        return self.students.edit_student_select(update, context)
    
    def edit_student_name_start(self, update, context):
        return self.students.edit_student_name_start(update, context)
    
    def edit_student_grade_start(self, update, context):
        return self.students.edit_student_grade_start(update, context)
    
    def edit_student_status_toggle(self, update, context):
        return self.students.edit_student_status_toggle(update, context)
    
    def edit_student_language_start(self, update, context):
        return self.students.edit_student_language_start(update, context)
    
    def set_student_language(self, update, context):
        return self.students.set_student_language(update, context)
    
    # Topics methods
    def topics_menu(self, update, context):
        return self.topics.topics_menu(update, context)
    
    def add_topic_start(self, update, context):
        return self.topics.add_topic_start(update, context)
    
    def list_topics(self, update, context):
        return self.topics.list_topics(update, context)
    
    def show_section_topics(self, update, context):
        return self.topics.show_section_topics(update, context)
    
    def select_main_topic_for_new(self, update, context):
        return self.topics.select_main_topic_for_new(update, context)
    
    def edit_topic_start(self, update, context):
        return self.topics.edit_topic_start(update, context)
    
    def edit_topic_select(self, update, context):
        return self.topics.edit_topic_select(update, context)
    
    def edit_topic_name_start(self, update, context):
        return self.topics.edit_topic_name_start(update, context)
    
    def edit_topic_section_start(self, update, context):
        return self.topics.edit_topic_section_start(update, context)
    
    def edit_topic_section_select(self, update, context):
        return self.topics.edit_topic_section_select(update, context)
    
    def edit_topic_toggle_status(self, update, context):
        return self.topics.edit_topic_toggle_status(update, context)
    
    def remove_topic_start(self, update, context):
        return self.topics.remove_topic_start(update, context)
    
    def remove_section_topics(self, update, context):
        return self.topics.remove_section_topics(update, context)
    
    def remove_topic_confirm(self, update, context):
        return self.topics.remove_topic_confirm(update, context)
    
    def remove_topic_execute(self, update, context):
        return self.topics.remove_topic_execute(update, context)
    
    def edit_section_topics(self, update, context):
        return self.topics.edit_section_topics(update, context)
    
    # Sections methods
    def sections_menu(self, update, context):
        return self.sections.sections_menu(update, context)
    
    def list_all_sections(self, update, context):
        return self.sections.list_all_sections(update, context)
    
    def add_section_start(self, update, context):
        return self.sections.add_section_start(update, context)
    
    def add_section_language_selected(self, update, context):
        return self.sections.add_section_language_selected(update, context)
    
    def edit_section_start(self, update, context):
        return self.sections.edit_section_start(update, context)
    
    def edit_section_select(self, update, context):
        return self.sections.edit_section_select(update, context)
    
    def edit_section_name_start(self, update, context):
        return self.sections.edit_section_name_start(update, context)
    
    def edit_section_toggle_status(self, update, context):
        return self.sections.edit_section_toggle_status(update, context)
    
    def delete_section_start(self, update, context):
        return self.sections.delete_section_start(update, context)
    
    def delete_section_confirm(self, update, context):
        return self.sections.delete_section_confirm(update, context)
    
    def delete_section_execute(self, update, context):
        return self.sections.delete_section_execute(update, context)
    
    # Questions methods
    def questions_menu(self, update, context):
        return self.questions.questions_menu(update, context)
    
    def upload_pdf_start(self, update, context):
        return self.questions.upload_pdf_start(update, context)
    
    def pdf_format_guide(self, update, context):
        return self.questions.pdf_format_guide(update, context)
    
    def questions_stats(self, update, context):
        return self.questions.questions_stats(update, context)
    
    def search_questions_start(self, update, context):
        return self.questions.search_questions_start(update, context)
    
    def delete_questions_start(self, update, context):
        return self.questions.delete_questions_start(update, context)
    
    def delete_questions_confirm(self, update, context):
        return self.questions.delete_questions_confirm(update, context)
    
    def delete_questions_execute(self, update, context):
        return self.questions.delete_questions_execute(update, context)
    
    def delete_single_question_start(self, update, context):
        return self.questions.delete_single_question_start(update, context)
    
    def delete_single_question_confirm(self, update, context):
        return self.questions.delete_single_question_confirm(update, context)
    
    def delete_single_question_execute(self, update, context):
        return self.questions.delete_single_question_execute(update, context)
    
    def add_question_start(self, update, context):
        return self.questions.add_question_start(update, context)
    
    def add_question_main_topic_selected(self, update, context):
        return self.questions.add_question_main_topic_selected(update, context)
    
    def add_question_topic_selected(self, update, context):
        return self.questions.add_question_topic_selected(update, context)
    
    def edit_question_start(self, update, context):
        return self.questions.edit_question_start(update, context)
    
    def handle_edit_question_id(self, update, context):
        # Извлекаем question_id из callback_data
        query = update.callback_query
        if query and query.data.startswith('edit_question_select_'):
            question_id = query.data.replace('edit_question_select_', '')
            return self.questions.handle_edit_question_id(update, context, question_id)
        else:
            # Если это не callback, то это ошибка
            return None
    
    def edit_question_topic_start(self, update, context):
        return self.questions.edit_question_topic_start(update, context)
    
    def edit_question_topic_select(self, update, context):
        return self.questions.edit_question_topic_select(update, context)
    
    def edit_question_text_start(self, update, context):
        return self.questions.edit_question_text_start(update, context)
    
    def edit_question_correct_start(self, update, context):
        return self.questions.edit_question_correct_start(update, context)
    
    def edit_question_options_start(self, update, context):
        return self.questions.edit_question_options_start(update, context)
    
    def edit_question_explanation_start(self, update, context):
        return self.questions.edit_question_explanation_start(update, context)
    
    def generate_ai_explanation_for_edit(self, update, context):
        return self.questions.generate_ai_explanation_for_edit(update, context)
    
    def manual_explanation_for_edit(self, update, context):
        return self.questions.manual_explanation_for_edit(update, context)
    
    # Admins methods
    def admins_menu(self, update, context):
        return self.admins.admins_menu(update, context)
    
    def add_admin_start(self, update, context):
        return self.admins.add_admin_start(update, context)
    
    def list_admins(self, update, context):
        return self.admins.list_admins(update, context)
    
    def remove_admin_start(self, update, context):
        return self.admins.remove_admin_start(update, context)
    
    def remove_admin_confirm(self, update, context):
        return self.admins.remove_admin_confirm(update, context)
    
    def remove_admin_execute(self, update, context):
        return self.admins.remove_admin_execute(update, context)
    
    # Stats methods
    def show_stats(self, update, context):
        return self.stats.show_stats(update, context)
    
    def show_user_history(self, update, context):
        return self.stats.show_user_history(update, context)

# Функция для создания обработчиков
def create_admin_handlers():
    """Создает экземпляры всех админ-обработчиков."""
    return {
        'base': AdminBaseHandler(),
        'questions': QuestionsHandler(), 
        'students': StudentsHandler(),
        'topics': TopicsHandler(),
        'sections': SectionsHandler(),
        'stats': StatsHandler(),
        'admins': AdminsHandler()
    }

__all__ = [
    'AdminBaseHandler',
    'QuestionsHandler', 
    'StudentsHandler',
    'TopicsHandler',
    'SectionsHandler',
    'StatsHandler',
    'AdminsHandler',
    'AdminHandlers',
    'create_admin_handlers'
] 