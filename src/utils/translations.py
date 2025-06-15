# -*- coding: utf-8 -*-
"""
Утилиты для работы с переводами интерфейса
"""

from config.constants import MAIN_MENU_KEYBOARD
from config.messages_kk import MESSAGES_KK, MAIN_MENU_KK, LANGUAGE_CHANGE_WARNING_KK

# Русские сообщения (по умолчанию)
MESSAGES_RU = {
    'welcome': "👋 Привет, {name}, {grade} класс!",
    'bot_description': "📚 Я бот для изучения математики. Выбери действие:",
    'select_topic': "📚 **Выберите раздел математики:**",
    'select_action': "📚 Выбрать тему и начать",
    'preparing_questions': "🔍 Подготавливаем вопросы...",
    'preparing_random_test': "🎯 Подготавливаю случайный тест из 10 вопросов...",
    'preparing_retry_test': "🎯 Подготавливаю тест на основе ваших ошибок...",
    'random_test_error': "❌ Не удалось создать случайный тест. Попробуйте позже.",
    'retry_test_error': "❌ Не удалось создать тест повторения. Попробуйте позже.",
    'random_test_topic_name': "Случайный тест",
    'retry_topic_name': "Повторение ошибок",
    'question_display_error': "❌ Ошибка при отображении вопроса.",
    'questions_load_error': "❌ Не удалось загрузить вопросы для теста.",
    'menu_load_error': "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова.",
    'bot_stopped': "🛑 Бот остановлен. Все данные очищены.\n\nДля нового старта используйте /start",
    'state_reset': "🔄 Состояние сброшено. Можете начать заново.",
    'not_specified': "не указан",
    'user_id_info': "🆔 **Ваши данные:**\n\n**User ID:** `{user_id}`\n**Username:** @{username}\n**Имя:** {full_name}\n\nИспользуйте User ID `{user_id}` для добавления в качестве админа.",
    'active_test_warning': "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста.",
    'general_error': "Произошла ошибка. Пожалуйста, попробуйте еще раз или используйте /start для перезапуска бота.",
    'no_access': "❌ Извините, у вас нет доступа к этому боту.\n\nВаш ID: {user_id}\nUsername: @{username}\n\nДля получения доступа обратитесь к администратору.",
    
    'topic_question': "Тема: {topic}\nВопрос {current} из {total}:\n\n{question}",
    'random_test_question': "🎯 Случайный тест\nВопрос {current} из {total}:\n\n{question}",
    'correct_answer': "✅ Правильно!",
    'incorrect_answer': "❌ Неправильно!\n\nПравильный ответ: {correct}",
    'test_completed': "Тест завершен! Нажмите 'Показать результаты' для просмотра полного разбора.",
    'continue_next': "Нажмите 'Продолжить' для следующего вопроса.",
    
    'test_results': "📊 Результаты теста по теме '{topic}':\n\nПравильных ответов: {correct} из {total} ({percentage:.1f}%)\n\n",
    'errors_section': "❌ Ошибки:\n",
    'no_errors': "🎉 Поздравляем! Все ответы верны!\n",
    'error_format': "Вопрос {num}: {user_answer} → {correct_answer}\n",
    
    'main_menu': "🏠 В главное меню",
    'show_results': "Показать результаты",
    'continue_btn': "Продолжить",
    'back_to_results': "⬅️ Назад к результатам",
    'back_to_topics': "📚 Выбрать другую тему",
    'retake_topic': "🔄 Пройти еще раз эту тему",
    'explanation_btn': "💡 Объяснение к вопросу {num}",
    'select_topic_btn': "📚 Выбрать тему и начать",
    'my_progress': "📊 Мой прогресс",
    'help': "❓ Помощь",
    'previous': "⬅️ Предыдущий",
    'next': "➡️ Следующий",
    
    'explanation_title': "💡 <b>Объяснение к вопросу {num}</b>\n\n",
    'explanation_question': "<b>Вопрос:</b> {question}\n\n",
    'explanation_user_answer': "❌ <b>Ваш ответ:</b> {answer}\n",
    'explanation_correct_answer': "✅ <b>Правильный ответ:</b> {answer}\n\n",
    'explanation_text': "📝 <b>Объяснение:</b>\n{explanation}",
    'question_not_found': "❌ Вопрос не найден.",
    
    'error_occurred': "Произошла ошибка. Пожалуйста, начните тест заново.",
    'error_topic_selection': "Произошла ошибка при выборе темы. Пожалуйста, попробуйте еще раз.",
    'no_questions': "Произошла ошибка при получении вопросов. Пожалуйста, попробуйте еще раз.",
    'topic_not_selected': "Тема не выбрана. Пожалуйста, выберите действие из меню.",
    
    'no_test_results': "У вас пока нет результатов тестов.",
    'progress_title': "📊 **Ваш прогресс:**\n\n",
    
    'help_text': """❓ **Помощь**

🎯 **О боте:**
Этот бот предоставляет тесты по математике для подготовки к НИШ.

📚 **Как использовать:**
1. Нажмите "📚 Выбрать тему и начать"
2. Выберите раздел математики
3. Выберите конкретную тему
4. Отвечайте на вопросы
5. Просматривайте результаты и разбирайте ошибки

🔄 **Повторение:**
Для повторения вопросов, на которые вы ответили неправильно, нажмите "🔄 Пройти еще раз эту тему".

📊 **Прогресс:**
Просматривайте свои результаты через "📊 Мой прогресс".

❓ Если у вас есть вопросы, обратитесь к администратору."""
}

def get_message(key: str, language: str = 'ru', **kwargs) -> str:
    """
    Получить переведенное сообщение
    
    Args:
        key: Ключ сообщения
        language: Язык ('ru' или 'kk')
        **kwargs: Параметры для форматирования
    
    Returns:
        Переведенное и отформатированное сообщение
    """
    messages = MESSAGES_KK if language == 'kk' else MESSAGES_RU
    message = messages.get(key, MESSAGES_RU.get(key, key))
    
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message
    return message

def get_main_menu_keyboard(language: str = 'ru') -> list:
    """
    Получить клавиатуру главного меню на нужном языке
    
    Args:
        language: Язык ('ru' или 'kk')
    
    Returns:
        Список кнопок главного меню
    """
    return MAIN_MENU_KK if language == 'kk' else MAIN_MENU_KEYBOARD

def get_language_change_warning(language: str = 'ru') -> str:
    """
    Получить предупреждение о смене языка
    
    Args:
        language: Язык ('ru' или 'kk')
    
    Returns:
        Текст предупреждения
    """
    if language == 'kk':
        return LANGUAGE_CHANGE_WARNING_KK
    else:
        return """🌐 **Смена языка**

⚠️ **Внимание!** При смене языка:
- Все ваши результаты тестов будут удалены
- История ошибок будет очищена
- Вы начнете заново на новом языке

Продолжить?""" 