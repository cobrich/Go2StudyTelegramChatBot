from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config.constants import MAIN_MENU_KEYBOARD
from services.database import Database

# Инициализируем БД для получения тем
_db = Database()

def build_topic_selection_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for main topic categories selection."""
    # Получаем язык пользователя
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and _db.is_admin(user_id)
    
    # Получаем темы с информацией о языке
    topics_dict = _db.get_topics_with_language_info(active_only=True, for_admin=is_admin)
    
    # Фильтруем темы по языку пользователя (для учеников) или показываем все (для админов)
    if is_admin:
        # Админы видят все темы с индикаторами языка
        main_topics = list(topics_dict.keys())
    else:
        # Ученики видят только темы на своем языке
        filtered_topics = {}
        for main_topic, subtopics in topics_dict.items():
            filtered_subtopics = [st for st in subtopics if st['language'] == user_language]
            if filtered_subtopics:
                filtered_topics[main_topic] = filtered_subtopics
        main_topics = list(filtered_topics.keys())
    
    keyboard = [
        [InlineKeyboardButton(main_topic, callback_data=f"main_topic_{i}")]
        for i, main_topic in enumerate(main_topics)
    ]
    # Add "Back to main menu" button at the end
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_subtopic_selection_keyboard(main_topic: str, main_topic_index: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for subtopic selection within a main topic."""
    # Получаем язык пользователя и проверяем роль
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and _db.is_admin(user_id)
    
    # Получаем темы с информацией о языке
    topics_dict = _db.get_topics_with_language_info(active_only=True, for_admin=is_admin)
    
    # Получаем подтемы для выбранного основного раздела
    subtopics_for_main = topics_dict.get(main_topic, [])
    
    # Фильтруем по языку для учеников
    if not is_admin:
        subtopics_for_main = [st for st in subtopics_for_main if st['language'] == user_language]
    
    # Получаем активные темы из БД для получения индексов
    all_active_topics = _db.get_topic_names(active_only=True)
    
    keyboard = []
    for topic_info in subtopics_for_main:
        subtopic_name = topic_info['name']
        display_name = topic_info['display_name']  # Уже сформировано в зависимости от роли
        
        # Находим индекс подтемы в общем списке активных тем
        try:
            subtopic_index = all_active_topics.index(subtopic_name)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"topic_{subtopic_index}")])
        except ValueError:
            continue
    
    # Add navigation buttons
    keyboard.append([InlineKeyboardButton("🔙 Назад к разделам", callback_data="back_to_main_topics")])
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_markup() -> ReplyKeyboardMarkup:
    """Get the main menu keyboard markup."""
    return ReplyKeyboardMarkup(
        MAIN_MENU_KEYBOARD,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def build_question_keyboard(options: list, q_num: int, max_reached: int, total_questions: int) -> InlineKeyboardMarkup:
    """Build keyboard for question display with navigation buttons."""
    keyboard = [
        [InlineKeyboardButton(ans, callback_data=f"answer_{i}_{q_num}")]
        for i, ans in enumerate(options)
    ]
    
    navigation_buttons = []
    if q_num > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data="prev_question"))
    
    if q_num < max_reached and q_num < total_questions - 1:
        navigation_buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data="next_question"))

    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    if q_num == 0:
        keyboard.append([InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics")])
    
    return InlineKeyboardMarkup(keyboard)

def build_results_keyboard(errors_list: list, current_topic: str, user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard for test results display."""
    buttons = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
    
    if errors_list:
        for err in errors_list:
            buttons.append([InlineKeyboardButton(
                f"Показать объяснение к вопросу {err['q_num']+1}",
                callback_data=f"show_expl_{err['q_num']}"
            )])
    else:
        # Получаем темы на языке пользователя
        user_language = _db.get_user_language(user_id) if user_id else 'ru'
        topics_dict = _db.get_topics_by_language(user_language, active_only=True)
        
        # Создаем плоский список тем для поиска индекса
        user_topics = []
        for main_topic, subtopics in topics_dict.items():
            user_topics.extend([st['name'] for st in subtopics])
        
        if current_topic in user_topics:
            # Получаем общий список активных тем для индекса
            all_active_topics = _db.get_topic_names(active_only=True)
            if current_topic in all_active_topics:
                topic_index = all_active_topics.index(current_topic)
                buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", 
                                                   callback_data=f"topic_retake_{topic_index}")])
    
    buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
    return InlineKeyboardMarkup(buttons)

def build_continue_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with continue button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Продолжить", callback_data="continue_test")]]) 