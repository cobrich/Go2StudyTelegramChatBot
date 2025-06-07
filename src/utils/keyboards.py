from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config.constants import MAIN_MENU_KEYBOARD, get_active_topics

def build_topic_selection_keyboard() -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for topic selection, including 'Back to main menu' button."""
    topics = get_active_topics()
    keyboard = [
        [InlineKeyboardButton(topic, callback_data=f"topic_{i}")]
        for i, topic in enumerate(topics)
    ]
    # Add "Back to main menu" button at the end
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
        topics = get_active_topics()
        if current_topic in topics:
            topic_index = topics.index(current_topic)
            buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", 
                                               callback_data=f"topic_retake_{topic_index}")])
    
    buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
    return InlineKeyboardMarkup(buttons)

def build_continue_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with continue button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Продолжить", callback_data="continue_test")]]) 