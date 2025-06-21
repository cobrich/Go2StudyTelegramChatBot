from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from src.config.constants import MAIN_MENU_KEYBOARD
from src.services.database import get_database_instance
from src.utils.translations import get_message, get_main_menu_keyboard

def _get_db():
    """Получить экземпляр базы данных (синглтон)."""
    return get_database_instance()

def build_topic_selection_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for main topic categories selection."""
    db = _get_db()
    
    # Получаем язык пользователя
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and db.is_admin(user_id)
    
    # Получаем основные разделы по языку пользователя
    if is_admin:
        # Админы видят все разделы (русские и казахские)
        russian_topics = db.get_main_topics_by_language('ru', active_only=True)
        kazakh_topics = db.get_main_topics_by_language('kk', active_only=True)
        main_topics = russian_topics + kazakh_topics
        # Сортируем по order_index
        main_topics.sort(key=lambda x: x['order_index'])
    else:
        # Ученики видят только разделы на своем языке
        main_topics = db.get_main_topics_by_language(user_language, active_only=True)
    
    keyboard = [
        [InlineKeyboardButton(topic['name'], callback_data=f"main_topic_{i}")]
        for i, topic in enumerate(main_topics)
    ]
    # Add "Back to main menu" button at the end
    keyboard.append([InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_subtopic_selection_keyboard(main_topic: str, main_topic_index: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for subtopic selection within a main topic."""
    db = _get_db()
    
    # Получаем язык пользователя и проверяем роль
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and db.is_admin(user_id)
    
    # Получаем полную структуру тем по языку
    ru_structure = {}
    kk_structure = {}
    
    if is_admin:
        # Для админов получаем структуру для обоих языков
        ru_structure = db.get_full_topic_structure_by_language('ru', active_only=True)
        kk_structure = db.get_full_topic_structure_by_language('kk', active_only=True)
        
        # Объединяем структуры
        full_structure = {**ru_structure, **kk_structure}
    else:
        # Для учеников только их язык
        full_structure = db.get_full_topic_structure_by_language(user_language, active_only=True)
        
        # Заполняем структуры для определения языка
        if user_language == 'ru':
            ru_structure = full_structure
        else:
            kk_structure = full_structure
    
    # Получаем подтемы для выбранного основного раздела
    subtopics_for_main = full_structure.get(main_topic, [])
    
    # Получаем активные темы из БД для получения индексов
    all_active_topics = db.get_topic_names(active_only=True)
    
    keyboard = []
    
    # Добавляем кнопки для подтем
    for subtopic_info in subtopics_for_main:
        subtopic_name = subtopic_info['name']
        question_count = subtopic_info.get('question_count', 0)
        has_questions = subtopic_info.get('has_questions', False)
        
        # Определяем язык подтемы через main_topic
        subtopic_language = 'ru'  # По умолчанию
        
        # Определяем язык по основному разделу
        if main_topic in ru_structure:
            subtopic_language = 'ru'
        elif main_topic in kk_structure:
            subtopic_language = 'kk'
        
        # Находим индекс темы в общем списке
        try:
            topic_index = all_active_topics.index(subtopic_name)
        except ValueError:
            continue  # Тема не найдена в активных
        
        # Формируем текст кнопки в зависимости от роли
        if is_admin:
            # Для админов: показываем количество вопросов и язык
            if has_questions:
                button_text = f"🟢 {subtopic_name} ({question_count}) [{subtopic_language}]"
            else:
                button_text = f"🟡 {subtopic_name} (ИИ) [{subtopic_language}]"
        else:
            # Для учеников: только название темы
            button_text = subtopic_name
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"topic_{topic_index}")])
    
    # Добавляем кнопку "Назад к разделам"
    back_text = "⬅️ Назад к разделам" if user_language == 'ru' else "⬅️ Бөлімдерге қайту"
    keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_main_topics")])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_markup(user_id: int = None) -> ReplyKeyboardMarkup:
    """Get the main menu keyboard markup with language support."""
    db = _get_db()
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and db.is_admin(user_id)
    
    # Получаем базовую клавиатуру для языка
    menu_keyboard = get_main_menu_keyboard(user_language)
    
    # Если пользователь админ, добавляем админские кнопки
    if is_admin:
        admin_button_text = "🔧 Админ-панель" if user_language == 'ru' else "🔧 Әкімші панелі"
        # Добавляем кнопку админ-панели в отдельной строке
        menu_keyboard = menu_keyboard + [[admin_button_text]]
    
    return ReplyKeyboardMarkup(
        menu_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def build_question_keyboard(options: list, q_num: int, max_reached: int, total_questions: int, user_id: int = None, is_random_test: bool = False) -> InlineKeyboardMarkup:
    """Build keyboard for question display with navigation buttons."""
    db = _get_db()
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    
    keyboard = [
        [InlineKeyboardButton(ans, callback_data=f"answer_{i}_{q_num}")]
        for i, ans in enumerate(options)
    ]
    
    navigation_buttons = []
    if q_num > 0:
        navigation_buttons.append(InlineKeyboardButton(get_message('previous', user_language), callback_data="prev_question"))
    
    if q_num < max_reached and q_num < total_questions - 1:
        navigation_buttons.append(InlineKeyboardButton(get_message('next', user_language), callback_data="next_question"))

    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    # Добавляем кнопку навигации в зависимости от типа теста
    if q_num == 0:
        if is_random_test:
            # Для случайных тестов показываем кнопку "В главное меню"
            main_menu_text = get_message('main_menu', user_language)
            keyboard.append([InlineKeyboardButton(f"{main_menu_text}", callback_data="main_menu")])
        else:
            # Для обычных тестов показываем кнопку "Назад к темам"
            back_to_topics_text = get_message('back_to_topics', user_language)
            keyboard.append([InlineKeyboardButton(f"⬅️ {back_to_topics_text}", callback_data="back_to_topics")])
    
    return InlineKeyboardMarkup(keyboard)

def build_results_keyboard(errors_list: list, current_topic: str, user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard for test results display."""
    db = _get_db()
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    
    buttons = [[InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")]]
    
    if errors_list:
        for err in errors_list:
            explanation_text = get_message('explanation_btn', user_language, num=err['q_num']+1)
            buttons.append([InlineKeyboardButton(
                explanation_text,
                callback_data=f"show_expl_{err['q_num']}"
            )])
    else:
        # Получаем темы на языке пользователя
        topics_dict = db.get_topics_by_language(user_language, active_only=True)
        
        # Создаем плоский список тем для поиска индекса
        user_topics = []
        for main_topic, subtopics in topics_dict.items():
            user_topics.extend([st['name'] for st in subtopics])
        
        if current_topic in user_topics:
            # Получаем общий список активных тем для индекса
            all_active_topics = db.get_topic_names(active_only=True)
            if current_topic in all_active_topics:
                topic_index = all_active_topics.index(current_topic)
                retake_text = get_message('retake_topic', user_language)
                buttons.append([InlineKeyboardButton(retake_text, 
                                                   callback_data=f"topic_retake_{topic_index}")])
    
    back_to_topics_text = get_message('back_to_topics', user_language)
    buttons.append([InlineKeyboardButton(back_to_topics_text, callback_data="back_to_topics")])
    return InlineKeyboardMarkup(buttons)

def build_continue_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard with continue button."""
    db = _get_db()
    user_language = db.get_user_language(user_id) if user_id else 'ru'
    continue_text = get_message('continue_btn', user_language)
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"➡️ {continue_text}", callback_data="continue_test")]]) 