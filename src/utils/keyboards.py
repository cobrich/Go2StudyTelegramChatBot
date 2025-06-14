from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config.constants import MAIN_MENU_KEYBOARD
from services.database import Database
from utils.translations import get_message, get_main_menu_keyboard

# Инициализируем БД для получения тем
_db = Database()

def build_topic_selection_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for main topic categories selection."""
    # Получаем язык пользователя
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and _db.is_admin(user_id)
    
    # Получаем основные разделы по языку пользователя
    if is_admin:
        # Админы видят все разделы (русские и казахские)
        russian_topics = _db.get_main_topics_by_language('ru', active_only=True)
        kazakh_topics = _db.get_main_topics_by_language('kk', active_only=True)
        main_topics = russian_topics + kazakh_topics
        # Сортируем по order_index
        main_topics.sort(key=lambda x: x['order_index'])
    else:
        # Ученики видят только разделы на своем языке
        main_topics = _db.get_main_topics_by_language(user_language, active_only=True)
    
    keyboard = [
        [InlineKeyboardButton(topic['name'], callback_data=f"main_topic_{i}")]
        for i, topic in enumerate(main_topics)
    ]
    # Add "Back to main menu" button at the end
    keyboard.append([InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_subtopic_selection_keyboard(main_topic: str, main_topic_index: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Create InlineKeyboardMarkup for subtopic selection within a main topic."""
    # Получаем язык пользователя и проверяем роль
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    is_admin = user_id and _db.is_admin(user_id)
    
    # Получаем полную структуру тем по языку
    if is_admin:
        # Для админов получаем структуру для обоих языков
        ru_structure = _db.get_full_topic_structure_by_language('ru', active_only=True)
        kk_structure = _db.get_full_topic_structure_by_language('kk', active_only=True)
        
        # Объединяем структуры
        full_structure = {**ru_structure, **kk_structure}
    else:
        # Для учеников только их язык
        full_structure = _db.get_full_topic_structure_by_language(user_language, active_only=True)
    
    # Получаем подтемы для выбранного основного раздела
    subtopics_for_main = full_structure.get(main_topic, [])
    
    # Получаем активные темы из БД для получения индексов
    all_active_topics = _db.get_topic_names(active_only=True)
    
    keyboard = []
    for topic_info in subtopics_for_main:
        subtopic_name = topic_info['name']
        question_count = topic_info['question_count']
        
        # Формируем отображаемое название в зависимости от роли
        if is_admin:
            # Для админов: показываем количество вопросов и индикатор наличия
            if question_count > 0:
                display_name = f"🟢 {subtopic_name} ({question_count})"
            else:
                display_name = f"🟡 {subtopic_name} (ИИ)"
        else:
            # Для учеников: только название темы
            display_name = subtopic_name
        
        # Находим индекс подтемы в общем списке активных тем
        try:
            subtopic_index = all_active_topics.index(subtopic_name)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"topic_{subtopic_index}")])
        except ValueError:
            continue
    
    # Add navigation buttons with translations
    back_to_sections = "🔙 Назад к разделам" if user_language == 'ru' else "🔙 Бөлімдерге қайту"
    keyboard.append([InlineKeyboardButton(back_to_sections, callback_data="back_to_main_topics")])
    keyboard.append([InlineKeyboardButton(get_message('main_menu', user_language), callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_markup(user_id: int = None) -> ReplyKeyboardMarkup:
    """Get the main menu keyboard markup with language support."""
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    menu_keyboard = get_main_menu_keyboard(user_language)
    return ReplyKeyboardMarkup(
        menu_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def build_question_keyboard(options: list, q_num: int, max_reached: int, total_questions: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard for question display with navigation buttons."""
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    
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
    
    if q_num == 0:
        back_to_topics_text = get_message('back_to_topics', user_language)
        keyboard.append([InlineKeyboardButton(f"⬅️ {back_to_topics_text}", callback_data="back_to_topics")])
    
    return InlineKeyboardMarkup(keyboard)

def build_results_keyboard(errors_list: list, current_topic: str, user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard for test results display."""
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    
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
                retake_text = get_message('retake_topic', user_language)
                buttons.append([InlineKeyboardButton(retake_text, 
                                                   callback_data=f"topic_retake_{topic_index}")])
    
    back_to_topics_text = get_message('back_to_topics', user_language)
    buttons.append([InlineKeyboardButton(back_to_topics_text, callback_data="back_to_topics")])
    return InlineKeyboardMarkup(buttons)

def build_continue_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Build keyboard with continue button."""
    user_language = _db.get_user_language(user_id) if user_id else 'ru'
    continue_text = get_message('continue_btn', user_language)
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"➡️ {continue_text}", callback_data="continue_test")]]) 