"""
Модуль админ-хендлеров.
Содержит все обработчики для админ-панели.
"""

from .base import AdminBaseHandler
from .questions import QuestionsHandler
from .students import StudentsHandler

# Функция для создания обработчиков
def create_admin_handlers():
    """Создает экземпляры всех админ-обработчиков."""
    return {
        'base': AdminBaseHandler(),
        'questions': QuestionsHandler(), 
        'students': StudentsHandler()
    }

__all__ = [
    'AdminBaseHandler',
    'QuestionsHandler', 
    'StudentsHandler',
    'create_admin_handlers'
] 