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

def build_subtopic_selection_keyboard(main_topic: str, main_topic_index: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for subtopic selection within a main topic."""
    # Получаем подтемы с количеством вопросов
    topics_with_counts = _db.get_topics_with_question_counts(active_only=True)
    
    # Фильтруем подтемы для выбранного основного раздела
    subtopics_for_main = [
        topic for topic in topics_with_counts 
        if topic['main_topic'] == main_topic
    ]
    
    # Получаем активные темы из БД для получения индексов
    all_active_topics = _db.get_topic_names(active_only=True)
    
    # Проверяем, является ли пользователь админом
    is_admin = user_id and _db.is_admin(user_id)
    
    keyboard = []
    for topic_info in subtopics_for_main:
        subtopic_name = topic_info['name']
        question_count = topic_info['question_count']
        has_questions = topic_info['has_questions']
        
        # Создаем текст кнопки в зависимости от роли пользователя
        if is_admin:
            # Для админов: показываем кружочки, количество вопросов и язык
            if has_questions:
                # 🟢 = есть вопросы в БД
                button_text = f"🟢 {subtopic_name} ({question_count}) [ru]"
            else:
                # 🟡 = ИИ генерация доступна
                button_text = f"🟡 {subtopic_name} (ИИ) [ru]"
        else:
            # Для учеников: только название темы без индикаторов
            button_text = subtopic_name
        
        # Находим индекс подтемы в общем списке активных тем
        try:
            subtopic_index = all_active_topics.index(subtopic_name)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"topic_{subtopic_index}")])
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