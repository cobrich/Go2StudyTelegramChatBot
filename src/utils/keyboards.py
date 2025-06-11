from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config.constants import MAIN_MENU_KEYBOARD
from services.database import Database

# Инициализируем БД для получения тем
_db = Database()

def build_topic_selection_keyboard() -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for main topic categories selection."""
    # Получаем основные разделы из БД
    base_structure = _db.get_base_topic_structure()
    main_topics = list(base_structure.keys())
    
    keyboard = [
        [InlineKeyboardButton(main_topic, callback_data=f"main_topic_{i}")]
        for i, main_topic in enumerate(main_topics)
    ]
    # Add "Back to main menu" button at the end
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_subtopic_selection_keyboard(main_topic: str, main_topic_index: int) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for subtopic selection within a main topic."""
    # Получаем подтемы из БД
    base_structure = _db.get_base_topic_structure()
    subtopics = base_structure.get(main_topic, [])
    
    # Получаем активные темы из БД  
    all_active_topics = _db.get_topic_names(active_only=True)
    
    keyboard = []
    for subtopic in subtopics:
        # Проверяем, активна ли подтема в БД
        if subtopic in all_active_topics:
            # Находим индекс подтемы в общем списке активных тем
            try:
                subtopic_index = all_active_topics.index(subtopic)
                keyboard.append([InlineKeyboardButton(subtopic, callback_data=f"topic_{subtopic_index}")])
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

def build_results_keyboard(errors_list: list, current_topic: str) -> InlineKeyboardMarkup:
    """Build keyboard for test results display."""
    buttons = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
    
    if errors_list:
        for err in errors_list:
            buttons.append([InlineKeyboardButton(
                f"Показать объяснение к вопросу {err['q_num']+1}",
                callback_data=f"show_expl_{err['q_num']}"
            )])
    else:
        topics = _db.get_topic_names(active_only=True)
        if current_topic in topics:
            topic_index = topics.index(current_topic)
            buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", 
                                               callback_data=f"topic_retake_{topic_index}")])
    
    buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
    return InlineKeyboardMarkup(buttons)

def build_continue_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with continue button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Продолжить", callback_data="continue_test")]]) 