import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import google.generativeai as genai
from database import Database
from constants import TOPICS, HELP_TEXT, MAIN_MENU
import re
import random
from html import escape
import telegram.error

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database()

# Инициализация Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel(os.getenv('GEMINI_MODEL'))

DEFAULT_QUESTIONS_PER_TEST = 10 # Определяем желаемое количество вопросов в тесте
MAX_EXPLANATION_PREVIEW_LENGTH = 700 # Макс. длина объяснения для немедленного показа

# ГЛАВНОЕ МЕНЮ - ReplyKeyboardMarkup
MAIN_MENU_KEYBOARD = [
    ["📚 Выбрать тему и начать"],
    ["📊 Мой прогресс"],
    ["❓ Помощь"]
]
main_menu_markup = ReplyKeyboardMarkup(
    MAIN_MENU_KEYBOARD,
    resize_keyboard=True,  # Делает кнопки более компактными
    one_time_keyboard=False # Клавиатура остается видимой
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главное меню при команде /start."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Очищаем данные сессии предыдущего теста (на случай, если пользователь перезапускает бота
    # или вводит /start во время другого активного процесса).
    context.user_data.clear()
    logging.info(f"User {user.id} ({user.username}) executed /start. User data cleared for chat {chat_id}.")

    welcome_text = f"👋 Привет, {user.mention_html()}! Я бот для изучения математики. Выбери действие:"

    # Шаг 1: Попытка удалить любую "зависшую" клавиатуру (на всякий случай).
    # try:
    #     await context.bot.send_message(
    #         chat_id=chat_id,
    #         text=".",  # ИЗМЕНЕНО: с \u200B на "." для предотвращения ошибки "Text must be non-empty"
    #         reply_markup=ReplyKeyboardRemove()
    #     )
    #     logging.info(f"Sent ReplyKeyboardRemove to chat {chat_id} as part of /start sequence.")
    # except Exception as e:
    #     logging.error(f"Error sending ReplyKeyboardRemove during /start for chat {chat_id}: {e}")

    # Шаг 2: Отправка приветственного сообщения с главным меню
    try:
        await update.message.reply_html(
            text=welcome_text,
            reply_markup=main_menu_markup  # <--- Ключевой момент: передача клавиатуры
        )
        logging.info(f"Welcome message with main_menu_markup sent to chat {chat_id} for user {user.id}.")
    except Exception as e:
        logging.error(f"Error sending welcome message with main_menu_markup during /start for chat {chat_id}: {e}")
        # Попытка отправить сообщение об ошибке пользователю, если основное не удалось
        try:
            await update.message.reply_text(
                "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова."
            )
        except Exception as e_fallback:
            logging.error(f"Error sending fallback error message during /start for chat {chat_id}: {e_fallback}")

async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(topic, callback_data=f"topic_{i}")]
        for i, topic in enumerate(TOPICS)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "📚 Выбери тему:",
        reply_markup=reply_markup
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Подтверждаем нажатие кнопки

    topic_index = int(query.data.replace("topic_", ""))
    topic = TOPICS[topic_index]
    context.user_data['current_topic'] = topic
    context.user_data['current_question'] = 0
    context.user_data['max_reached_question'] = 0 # Сбрасываем для нового теста
    context.user_data['correct_answers'] = 0
    context.user_data.pop('errors', None) # Очищаем ошибки предыдущего теста
    context.user_data['answered_questions'] = {} # Initialize storage for answered questions
    
    # Устанавливаем флаг загрузки и показываем сообщение о загрузке
    context.user_data['loading_questions'] = True
    try:
        await query.edit_message_text(
            "⏳ Загрузка вопросов... Пожалуйста, подождите.",
            reply_markup=None # Убираем кнопки с этого сообщения
        )
    except telegram.error.BadRequest as e:
        if "message is not modified" in str(e).lower():
            pass # Сообщение уже "загрузка", это нормально
        else:
            logging.warning(f"Error editing message to loading state in start_test: {e}")
    except Exception as e:
        logging.warning(f"Generic error editing message to loading state in start_test: {e}")

    try:
        # Attempt to delete the last explanation message shown on the results screen
        last_expl_info = context.user_data.pop('last_explanation_message_info_on_results', None)
        if last_expl_info:
            try:
                await context.bot.delete_message(
                    chat_id=last_expl_info['chat_id'],
                    message_id=last_expl_info['message_id']
                )
                logging.info(f"Deleted previous explanation message {last_expl_info['message_id']} from chat {last_expl_info['chat_id']}")
            except telegram.error.BadRequest as e:
                if "message to delete not found" in str(e).lower():
                    logging.info(f"Previous explanation message {last_expl_info.get('message_id')} not found for deletion (already deleted or too old).")
                else:
                    logging.warning(f"Could not delete previous explanation message {last_expl_info.get('message_id')}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error deleting previous explanation message {last_expl_info.get('message_id')}: {e}")

        user_id = update.effective_user.id
        # Получаем вопросы, где были ошибки (текст_вопроса, прав_ответ, объяснение)
        error_task_tuples = db.get_error_tasks_for_user(user_id, topic, limit=DEFAULT_QUESTIONS_PER_TEST)
        
        all_test_questions = []

        if not error_task_tuples:
            logging.info(f"User {user_id} has no outstanding error tasks for topic '{topic}'. Generating {DEFAULT_QUESTIONS_PER_TEST} new questions purely from AI.")
            all_test_questions = await get_or_generate_tasks(
                topic, 
                db, 
                needed=DEFAULT_QUESTIONS_PER_TEST, 
                force_ai=True
            )
        else:
            logging.info(f"User {user_id} has {len(error_task_tuples)} error tasks for topic '{topic}'. Prioritizing these.")
            # Преобразуем в формат (вопрос, ответ, объяснение, None для неверных вариантов)
            error_questions_formatted = []
            for error_task_tuple in error_task_tuples:
                if len(error_task_tuple) >= 3:
                    q_text, c_ans, expl = error_task_tuple[:3]
                    error_questions_formatted.append((q_text, c_ans, expl, None))
                else:
                    logging.warning(f"Skipping malformed error_task_tuple (not enough values): {error_task_tuple}")
            
            all_test_questions.extend(error_questions_formatted)
            
            current_question_texts = set(q_tuple[0] for q_tuple in error_questions_formatted)

            if len(all_test_questions) < DEFAULT_QUESTIONS_PER_TEST:
                needed_additionally = DEFAULT_QUESTIONS_PER_TEST - len(all_test_questions)
                logging.info(
                    f"Fetching {needed_additionally} additional unique questions for topic '{topic}', "
                    f"excluding {len(current_question_texts)} already selected error questions."
                )
                
                additional_unique_questions = await get_or_generate_tasks(
                    topic, 
                    db, 
                    needed=needed_additionally, 
                    force_ai=False, 
                    existing_question_texts_to_exclude=current_question_texts
                )
                
                all_test_questions.extend(additional_unique_questions)
                for q_tuple in additional_unique_questions:
                    current_question_texts.add(q_tuple[0])
            random.shuffle(all_test_questions) 
        
        context.user_data['questions'] = all_test_questions[:DEFAULT_QUESTIONS_PER_TEST]

    finally:
        context.user_data.pop('loading_questions', None) # Снимаем флаг загрузки

    if not context.user_data.get('questions'): # Используем .get для безопасной проверки
        logging.warning(f"Failed to load any questions for topic '{topic}' for user {user_id}.")
        try:
            # query здесь все еще доступен и ссылается на исходное сообщение
            await query.edit_message_text(
                "Не удалось загрузить вопросы для этой темы. Попробуйте позже или выберите другую тему.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics")]])
            )
        except Exception as e_edit_fail:
            logging.error(f"Failed to edit message for no questions in start_test: {e_edit_fail}")
        return
    
    final_question_count = len(context.user_data.get('questions', []))
    source_description = "All AI generated" if not error_task_tuples else "Prioritized error questions, supplemented with others"
    
    logging.info(
        f"Prepared {final_question_count}/{DEFAULT_QUESTIONS_PER_TEST} questions for topic '{topic}' for user {user_id}. "
        f"Source: {source_description} (Initial errors found: {len(error_task_tuples)})."
    )
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_num = context.user_data['current_question']
    max_reached = context.user_data.get('max_reached_question', 0)
    questions_data = context.user_data['questions'] # Список кортежей
    topic = context.user_data['current_topic']

    answered_questions_map = context.user_data.get('answered_questions', {})

    if q_num < len(questions_data):
        if q_num in answered_questions_map:
            # Question has been answered, show feedback instead of asking again
            answer_details = answered_questions_map[q_num]
            original_question_data = questions_data[q_num]
            question_text, correct_answer_text, explanation_text, _ = original_question_data
            
            selected_option_text = answer_details['selected_option_text']
            user_answer_correct = answer_details['is_correct']

            feedback_text = f"<b>Тема: {escape(topic)}</b>\n"
            feedback_text += f"<b>Вопрос {q_num + 1}/{len(questions_data)} (уже отвечен):</b>\n{escape(question_text)}\n\n"
            feedback_text += f"Ваш ответ: <i>{escape(selected_option_text)}</i>\n\n"

            if user_answer_correct:
                feedback_text += "✅ <b>Правильно!</b>\n"
            else:
                feedback_text += f"❌ <b>Неправильно.</b> Правильный ответ: <b>{escape(correct_answer_text)}</b>\n"
            
            if explanation_text:
                escaped_explanation = escape(explanation_text)
                feedback_text += f"\n<b>Объяснение:</b>\n{escaped_explanation}\n"
            else:
                feedback_text += "\nОбъяснение для этого вопроса отсутствует.\n"

            # Navigation buttons
            navigation_buttons_list = []
            if q_num > 0:
                navigation_buttons_list.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data="prev_question"))
            
            if q_num < len(questions_data) - 1:
                navigation_buttons_list.append(InlineKeyboardButton("➡️ Следующий", callback_data="next_question"))

            keyboard_layout = []
            if navigation_buttons_list:
                keyboard_layout.append(navigation_buttons_list)
            
            keyboard_layout.append([InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics")])
            reply_markup = InlineKeyboardMarkup(keyboard_layout)

            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        text=feedback_text,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                except telegram.error.BadRequest as e:
                    if "message is not modified" in str(e).lower():
                        await update.callback_query.answer() # Silently acknowledge if message is identical
                    else:
                        logging.warning(f"Failed to edit message in ask_question (answered view), sending new: {e}")
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=feedback_text,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logging.warning(f"Error editing message in ask_question (answered view), sending new: {e}")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=feedback_text,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=feedback_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            return # Important: exit after showing feedback for an answered question

        # Original logic for unanswered questions starts here
        question, correct_answer, explanation, ai_incorrect_options = questions_data[q_num]
        
        all_answers = []
        if ai_incorrect_options and len(ai_incorrect_options) > 0:
            all_answers = list(ai_incorrect_options) + [correct_answer] # Создаем копию списка
            random.shuffle(all_answers)
            logging.info(f"Using AI-generated options for Q: {question[:30]}...")
        else:
            logging.warning(f"Using universal options for Q: {question[:30]} (AI options missing or empty). CA: {correct_answer}")
            all_answers = generate_universal_options(correct_answer)

        # Убедимся, что у нас всегда 4 варианта, даже если generate_universal_options вернула меньше (маловероятно)
        # или если AI дал меньше. Дополним заглушками, если нужно.
        # Это больше подстраховка, т.к. generate_universal_options должна давать 4.
        # А AI мы просим 3 неверных + 1 верный.
        while len(all_answers) < 4:
            all_answers.append(f"Доп. вариант {len(all_answers) + 1}")
        all_answers = all_answers[:4] # Берем только первые 4, если вдруг оказалось больше
        random.shuffle(all_answers)

        keyboard = [
            [InlineKeyboardButton(ans, callback_data=f"ans_{i}_{q_num}")]
            for i, ans in enumerate(all_answers)
        ]
        
        navigation_buttons = []
        if q_num > 0:
            navigation_buttons.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data="prev_question"))
        
        # Кнопка "Следующий" для навигации/пропуска, если уже были дальше
        # Не показываем "Следующий", если это последний вопрос в тесте
        if q_num < max_reached and q_num < len(questions_data) - 1:
            navigation_buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data="next_question"))

        if navigation_buttons: # Добавляем строку с кнопками навигации, если они есть
            keyboard.append(navigation_buttons)
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"<b>Тема: {topic}</b>\n<b>Вопрос {q_num + 1}/{len(questions_data)}:</b>\n\n{question}"
        
        # Определяем, как отправлять сообщение: редактировать существующее или отправить новое
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            except Exception as e: # Если не удалось отредактировать (например, сообщение слишком старое)
                logging.warning(f"Failed to edit message in ask_question, sending new: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        else: # Если нет callback_query (например, первый вызов из команды /start) - невозможно, т.к. start_test вызывается по кнопке
             # Этот else маловероятен для ask_question в текущей логике, но оставим для полноты
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    else:
        await show_results(update, context)

def normalize_answer(ans: str) -> str:
    """Приводит ответ к стандартному виду для сравнения: убирает пробелы по краям и переводит в нижний регистр."""
    return str(ans).strip().lower()

def answers_equal(ans1: str, ans2: str) -> bool:
    """Сравнивает два ответа после их нормализации."""
    return normalize_answer(ans1) == normalize_answer(ans2)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Убираем "часики"

    data_parts = query.data.split("_")
    answer_index = int(data_parts[1])
    q_num_answered = int(data_parts[2]) # Номер вопроса, на который ответили

    # Проверяем, актуален ли этот ответ (на случай если пользователь нажал старую кнопку)
    # Также проверяем, не был ли этот вопрос уже отвечен и сохранен.
    # Если пользователь как-то умудрился нажать кнопку ответа на уже обработанный вопрос,
    # можно его просто проигнорировать или мягко уведомить.
    answered_questions_map = context.user_data.get('answered_questions', {})
    if q_num_answered != context.user_data['current_question'] or q_num_answered in answered_questions_map:
        # Если это ответ на старый вопрос ИЛИ на вопрос, который уже числится как отвеченный
        # (например, пользователь дважды кликнул очень быстро или вернулся и кликнул снова)
        # Просто ничего не делаем или даем короткое уведомление.
        # await query.message.reply_text("Этот вопрос уже был обработан или вы ответили на старый вопрос.")
        logging.info(f"Ignoring answer for q_num {q_num_answered} as it's not current or already processed.")
        return

    q_num = context.user_data['current_question']
    questions_data = context.user_data['questions']
    question_data = questions_data[q_num]
    question_text, correct_answer_text, explanation_text, ai_options = question_data

    # Получаем все варианты, которые были показаны пользователю, чтобы найти текст выбранного
    # Это немного избыточно, но гарантирует, что мы берем текст с кнопки
    options_shown = []
    if ai_options and len(ai_options) > 0:
        options_shown = list(ai_options) + [correct_answer_text]
    else:
        options_shown = generate_universal_options(correct_answer_text)
    
    while len(options_shown) < 4: # Добиваем до 4, если нужно (маловероятно)
        options_shown.append(f"Доп. вариант {len(options_shown) + 1}")
    options_shown = options_shown[:4]
    # Важно! Чтобы получить тот же порядок, что и в ask_question, нужно либо сохранить его,
    # либо здесь не перемешивать, а найти правильный ответ и сравнить с выбранным по индексу.
    # Проще всего передать сам текст ответа в callback_data или найти его по индексу из НЕперемешанного списка.
    # Однако, callback_data может стать слишком длинным.
    # Давайте найдем текст выбранного ответа из сообщения, если это возможно, или пересмотрим логику.

    # В ask_question мы создаем кнопки так:
    # keyboard = [
    #     [InlineKeyboardButton(ans, callback_data=f"ans_{i}_{q_num}")]
    #     for i, ans in enumerate(all_answers) # all_answers - это перемешанный список
    # ]
    # Значит, мы не знаем, какой текст был под индексом answer_index без сохранения all_answers.

    # Простой способ: в `ask_question` сохранять `all_answers` в `context.user_data` для текущего вопроса.
    # Или, что еще проще, `check_answer` должен знать, какой текст был выбран.
    # Мы можем получить это из `query.message.reply_markup`.
    
    selected_option_text = "Не удалось определить выбранный ответ" # Заглушка
    if query.message and query.message.reply_markup:
        # Проходим по кнопкам, чтобы найти текст выбранного варианта
        # Это предполагает, что callback_data f"ans_{answer_index}_{q_num}" уникален для кнопок-ответов
        # и что answer_index соответствует позиции в ряду кнопок.
        # В нашем случае у нас один столбец кнопок-ответов.
        flat_keyboard_buttons = [button for row in query.message.reply_markup.inline_keyboard for button in row]
        for btn_idx, button in enumerate(flat_keyboard_buttons):
            if button.callback_data == query.data: # Нашли нашу кнопку
                 selected_option_text = button.text
                 break
    
    user_answer_correct = answers_equal(selected_option_text, correct_answer_text)

    feedback_text = f"<b>Тема: {escape(context.user_data['current_topic'])}</b>\n"
    feedback_text += f"<b>Вопрос {q_num + 1}/{len(questions_data)}:</b>\n{escape(question_text)}\n\n"
    feedback_text += f"Ваш ответ: <i>{escape(selected_option_text)}</i>\n\n"

    if user_answer_correct:
        context.user_data['correct_answers'] += 1
        feedback_text += "✅ <b>Правильно!</b>\n"
    else:
        feedback_text += f"❌ <b>Неправильно.</b> Правильный ответ: <b>{escape(correct_answer_text)}</b>\n"
        if explanation_text:
            escaped_explanation = escape(explanation_text)
            if len(escaped_explanation) > MAX_EXPLANATION_PREVIEW_LENGTH:
                feedback_text += "\n<i>Подробное объяснение будет доступно на экране результатов.</i>\n"
            else:
                feedback_text += f"\n<b>Объяснение:</b>\n{escaped_explanation}\n"
        else:
            feedback_text += "\nОбъяснение для этого вопроса отсутствует.\n"
        
        errors_list_session = context.user_data.get('errors', [])
        errors_list_session.append({
            'q_num': q_num + 1,
            'question': question_text,
            'user_answer': selected_option_text,
            'correct_answer': correct_answer_text,
            'explanation': explanation_text
        })
        context.user_data['errors'] = errors_list_session

        # --- BEGIN EDIT: Save error to database ---
        try:
            user_id = update.effective_user.id
            topic = context.user_data['current_topic']
            # Assuming your Database class has a method like add_user_error
            # This method should store the error persistently.
            db.add_user_error(
                user_id=user_id,
                topic=topic,
                question_text=question_text,
                user_answer_text=selected_option_text, # Storing user's answer might be useful
                correct_answer_text=correct_answer_text,
                explanation_text=explanation_text
            )
            logging.info(f"User {user_id} error on topic '{topic}' for question '{question_text[:50]}' saved to DB.")
        except AttributeError as e:
            logging.error(f"Database object 'db' or method 'add_user_error' not found or attribute error: {e}")
        except Exception as e:
            logging.error(f"Failed to save user error to database: {e}")
        # --- END EDIT ---

    # Store that this question has been answered and the user's choice
    context.user_data.setdefault('answered_questions', {})[q_num] = {
        'selected_option_text': selected_option_text,
        'is_correct': user_answer_correct
    }

    # Кнопка для продолжения
    continue_button = [InlineKeyboardButton("➡️ Продолжить", callback_data="continue_test")]
    reply_markup = InlineKeyboardMarkup([continue_button])

    await query.edit_message_text(
        text=feedback_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def continue_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Продолжить'."""
    await update.callback_query.answer() # Убираем "часики"

    current_q_index = context.user_data['current_question']
    total_questions = len(context.user_data['questions'])

    # Переходим к следующему вопросу
    context.user_data['current_question'] += 1
    
    # Обновляем max_reached_question, чтобы пользователь мог вернуться к этому вопросу
    # и чтобы кнопка "Следующий" в ask_question работала корректно
    context.user_data['max_reached_question'] = max(
        context.user_data.get('max_reached_question', 0),
        context.user_data['current_question'] 
    )

    # Очищаем ID сообщения с объяснением, так как мы переходим к новому вопросу/результатам
    # Это теперь будет словарь, но pop его корректно удалит.
    context.user_data.pop('last_explanation_message_info_on_results', None)

    if context.user_data['current_question'] < total_questions:
        await ask_question(update, context)
    else:
        # Если это был последний вопрос, показываем результаты
        await show_results(update, context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    topic = context.user_data.get('current_topic', 'Неизвестная тема')
    correct_answers = context.user_data.get('correct_answers', 0)
    total_questions = len(context.user_data.get('questions', []))
    
    # Очищаем информацию о сообщении с объяснением от предыдущего просмотра результатов (если был)
    # Это гарантирует, что при первом запросе объяснения на ЭТОМ экране результатов будет создано новое сообщение
    # или если старое было удалено, новое будет создано без попытки редактирования несуществующего.
    context.user_data.pop('last_explanation_message_info_on_results', None)

    if total_questions == 0:
        text = "Вы еще не прошли ни одного вопроса в этом тесте."
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к темам", callback_data="back_to_topics")]])
    else:
        percentage = (correct_answers / total_questions) * 100
        # Сохраняем результат теста в базу данных
        # Передаем рассчитанный процент вместо количества правильных ответов
        db.add_test_result(user_id, topic, percentage)

        text = (
            f"📊 <b>Результаты теста по теме \"{topic}\":</b>\n\n"
            f"Правильных ответов: {correct_answers}/{total_questions}\n"
            f"Процент выполнения: {percentage:.1f}%\n"
        )

        errors_list = context.user_data.get('errors', [])
        buttons = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]] # main_menu возвращает к выбору тем/прогрессу
                                                                                        # back_to_topics - это если мы из вопроса вышли
        
        if errors_list:
            text += "\n<b>Ошибки:</b>\n"
            # Сортируем ошибки по номеру вопроса на всякий случай, хотя они должны добавляться по порядку
            errors_list.sort(key=lambda e: e['q_num']) 
            for i, err in enumerate(errors_list):
                text += f"{i + 1}. Вопрос {err['q_num']}\n" # err['q_num'] уже 1-based
                buttons.append([InlineKeyboardButton(
                    f"Показать объяснение к вопросу {err['q_num']}",
                    callback_data=f"show_expl_{err['q_num']}"
                )])
        else:
            text += "\n🎉 Отлично! Ошибок нет!"
        
        buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", callback_data=f"topic_{TOPICS.index(topic)}")])
        buttons.append([InlineKeyboardButton("📚 Выбрать другую тему", callback_data="back_to_topics")])
        reply_markup = InlineKeyboardMarkup(buttons)

    if query: # Если это callback от кнопки (например, "Завершить тест" или "Продолжить" с последнего вопроса)
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except telegram.error.BadRequest as e:
            if "message is not modified" in str(e).lower():
                logging.info(f"Message not modified in show_results for chat {query.message.chat.id}, no action needed.")
                # Сообщение не изменилось, ничего не делаем
            else:
                logging.warning(f"Failed to edit message in show_results (BadRequest), sending new: {e}")
                # Используем query.message.chat.id вместо query.effective_chat.id
                await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Failed to edit message in show_results (Other Exception), sending new: {e}")
            # Используем query.message.chat.id вместо query.effective_chat.id
            await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML")
    else: # Если show_results вызывается не из callback (маловероятно в текущем потоке)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    # Проверяем, идет ли загрузка вопросов
    if user_data.get('loading_questions'):
        await update.message.reply_text(
            "⏳ Пожалуйста, подождите, идет загрузка вопросов для теста...",
            reply_markup=main_menu_markup # Можно оставить меню или убрать его временно
        )
        return

    # Check if a test is actively in progress (questions loaded and not yet at results)
    is_test_active_for_message_handling = (
        user_data.get('questions') and
        user_data.get('current_question') is not None and
        # Check if current_question is a valid index for an ongoing question
        user_data.get('current_question', float('inf')) < len(user_data['questions'])
    )

    if text == "📚 Выбрать тему и начать":
        if is_test_active_for_message_handling:
            await update.message.reply_text(
                "Вы проходите тест. Чтобы начать новый, сначала завершите текущий. "
                "Для отмены теста и возврата к выбору тем, используйте кнопку '⬅️ Назад к темам' в сообщении с вопросом.",
                reply_markup=main_menu_markup
            )
        else:
            context.user_data.clear()
            await show_topics_from_message(update, context)
    elif text == "📊 Мой прогресс":
        if is_test_active_for_message_handling:
            await update.message.reply_text(
                "Чтобы посмотреть прогресс, пожалуйста, завершите текущий тест. "
                "Для отмены теста и возврата к выбору тем, используйте кнопку '⬅️ Назад к темам' в сообщении с вопросом.",
                reply_markup=main_menu_markup
            )
        else:
            context.user_data.clear()
            await show_progress_from_message(update, context)
    elif text == "❓ Помощь":
        if is_test_active_for_message_handling:
            await update.message.reply_text(
                "Вы проходите тест. Для помощи по боту, пожалуйста, завершите текущий тест. "
                "Для отмены теста и возврата к выбору тем, используйте кнопку '⬅️ Назад к темам' в сообщении с вопросом.",
                reply_markup=main_menu_markup
            )
        else:
            # Current behavior is to clear user_data for help, keeping it consistent
            context.user_data.clear()
            await update.message.reply_text(HELP_TEXT, reply_markup=main_menu_markup)
    else:
        # For any other text input not matching the main menu commands
        if is_test_active_for_message_handling:
            await update.message.reply_text(
                "Пожалуйста, используйте кнопки для ответа на вопрос или навигации в тесте.",
                reply_markup=main_menu_markup # Keep menu visible, but guide them
            )
        else:
            # Default reply if no test is active and text doesn't match commands
            await update.message.reply_text("Выбери действие из меню:", reply_markup=main_menu_markup)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()  # чтобы убрать "часики" на кнопке
    await update.callback_query.edit_message_text(
        HELP_TEXT
    )

async def show_topics_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(topic, callback_data=f"topic_{i}")]
        for i, topic in enumerate(TOPICS)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 Выбери тему:", reply_markup=reply_markup)

async def show_progress_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    progress = db.get_user_progress(user_id)
    recent = db.get_recent_topics(user_id)
    errors = db.get_error_topics(user_id)

    if not progress or not progress[0]:
        text = (
            "Вы пока не прошли ни одного теста.\n"
            "Пройденных тестов: 0\n"
            "Правильных ответов: 0\n"
            "Процент: 0%\n"
            "Ошибочных вопросов: 0"
        )
    else:
        total_tests = progress[0] or 0
        avg_result = int(progress[1] or 0)
        error_count = sum(e[1] for e in errors) if errors else 0
        text = (
            f"Пройденных тестов: {total_tests}\n"
            f"Средний результат: {avg_result}%\n"
            f"Ошибочных вопросов: {error_count}\n"
        )
        if recent:
            text += "\nПоследние темы:\n"
            for topic, result, date in recent:
                text += f"• {topic}: {int(result)}% ({date[:10]})\n"

    await update.message.reply_text(text, reply_markup=main_menu_markup)

async def generate_ai_task(topic):
    prompt_template = (
        "Сгенерируй один интересный вопрос по теме '{topic}' для ученика 5-6 класса. "
        "Дай только сам вопрос, правильный ответ и краткое объяснение. "
        "Ответ должен соответствовать единице измерения, указанной в вопросе. А также должен соответствовать теме. То есть "
        "если в вопросе указана единица измерения, то ответ должен быть в этой единице измерения и соответствовать теме. Например тема "
        "Натуральные числа' и единица измерения 'килограммы', то ответ должен быть в килограммах и соответствовать натуральным числам. "
        "Ответ не должен быть слишком сложным, чтобы его можно было решить в уме. И не должен быть слишком простым, чтобы не было смысла его решать."
        "Ответ не должен быть длинным, чтобы не превышало 60 символов."
        "Предоставь:\n"
        "1. Текст вопроса.\n"
        "2. Один правильный ответ.\n"
        "3. Три НЕПРАВИЛЬНЫХ, но правдоподобных варианта ответа.\n"
        "4. Краткое объяснение правильного ответа.\n\n"
        "Отформатируй ответ СТРОГО следующим образом, КАЖДЫЙ ПУНКТ С НОВОЙ СТРОКИ:\n"
        "ВОПРОС: [текст вопроса]\n"
        "ПРАВИЛЬНЫЙ ОТВЕТ: [правильный ответ]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [неправильный вариант 1]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [неправильный вариант 2]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [неправильный вариант 3]\n"
        "ОБЪЯСНЕНИЕ: [текст объяснения]"
    )
    
    prompt = prompt_template.format(topic=topic)

    try:
        response_text = model.generate_content(prompt).text
        logging.debug(f"AI Response for topic '{topic}':\n{response_text}")

        q_match = re.search(r"ВОПРОС:\s*(.*?)\s*ПРАВИЛЬНЫЙ ОТВЕТ:", response_text, re.DOTALL | re.IGNORECASE)
        correct_a_match = re.search(r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|\s*ОБЪЯСНЕНИЕ:)", response_text, re.DOTALL | re.IGNORECASE)
        
        q = q_match.group(1).strip() if q_match else None
        correct_a = correct_a_match.group(1).strip() if correct_a_match else None

        incorrect_options = []
        search_start_index = 0
        if correct_a_match: # Начинаем поиск неправильных ответов после правильного
            # Ищем начало первого неправильного ответа или объяснения
            first_incorrect_or_expl_match = re.search(r"НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:", response_text[correct_a_match.end():], re.IGNORECASE)
            if first_incorrect_or_expl_match:
                 search_start_index = correct_a_match.end() + first_incorrect_or_expl_match.start()

        for match in re.finditer(r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|\s*ОБЪЯСНЕНИЕ:|$)", response_text[search_start_index:], re.DOTALL | re.IGNORECASE):
            option_text = match.group(1).strip()
            if option_text: # Добавляем только непустые варианты
                 incorrect_options.append(option_text)

        e_match = re.search(r"ОБЪЯСНЕНИЕ:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        e = e_match.group(1).strip() if e_match else None

        if not (q and correct_a and e and len(incorrect_options) >= 1):
            logging.warning(
                f"AI response parsing failed or missing critical parts for topic '{topic}'. "
                f"Q:{bool(q)}, A:{bool(correct_a)}, E:{bool(e)}, Opts count:{len(incorrect_options)}. "
                f"Raw response snippet: {response_text[:500]}"
            )
            return None, None, None, None # Возвращаем 4 значения None

        return q, correct_a, incorrect_options, e
    except Exception as err:
        logging.error(f"Error in generate_ai_task for topic '{topic}': {err}\nResponse snippet: {response_text[:500] if 'response_text' in locals() else 'Response not available'}")
        return None, None, None, None # Возвращаем 4 значения None

async def get_or_generate_tasks(topic: str, db: Database, needed: int = DEFAULT_QUESTIONS_PER_TEST, force_ai: bool = False, existing_question_texts_to_exclude: set = set()) -> list:
    """
    Получает задачи из БД и/или генерирует новые с помощью ИИ,
    чтобы достичь 'needed' количества УНИКАЛЬНЫХ ПО ТЕКСТУ ВОПРОСА задач для указанной темы.
    Если force_ai=True, задачи из БД не запрашиваются, генерируются только новые.
    Сохраняет новые сгенерированные задачи в БД.
    Возвращает список кортежей: (question_text, correct_answer, explanation, incorrect_options_list)
    """
    
    final_tasks_list = []
    processed_texts = set() # Tracks texts of questions already added to final_tasks_list

    # Этап 1: Сбор уникальных задач из БД (только если не force_ai)
    if not force_ai:
        # Загружаем немного больше из БД, чтобы был запас.
        db_tasks_pool = db.get_tasks_for_topic(topic, limit=needed * 2) 

        for task_tuple in db_tasks_pool:
            if len(final_tasks_list) >= needed:
                break
            question_text = task_tuple[0]
            if question_text not in processed_texts and question_text not in existing_question_texts_to_exclude:
                final_tasks_list.append(task_tuple)
                processed_texts.add(question_text)
        logging.info(f"Topic '{topic}': Collected {len(final_tasks_list)} unique tasks from DB (target for this call: {needed}, force_ai={force_ai}).")
    else:
        logging.info(f"Topic '{topic}': Skipped DB task collection due to force_ai=True (target for this call: {needed}, current list size: {len(final_tasks_list)}).")


    # Этап 2: Генерация с помощью ИИ, если все еще необходимо
    num_still_needed_for_ai = needed - len(final_tasks_list)

    if num_still_needed_for_ai > 0:
        logging.info(f"Need to generate {num_still_needed_for_ai} more unique tasks via AI for topic '{topic}' (force_ai={force_ai}, current list size: {len(final_tasks_list)}).")
        generated_ai_count_successfully_added = 0
        
        max_total_ai_generation_attempts = num_still_needed_for_ai * 2 + 5 
        current_ai_generation_attempt = 0

        while len(final_tasks_list) < needed and current_ai_generation_attempt < max_total_ai_generation_attempts:
            current_ai_generation_attempt += 1
            logging.debug( # Изменено на debug для уменьшения количества логов при успешных попытках
                f"AI Generation Attempt {current_ai_generation_attempt}/{max_total_ai_generation_attempts} for topic '{topic}'. "
                f"(Target: {needed} unique, Current in list: {len(final_tasks_list)})"
            )
            
            ai_task_data = await generate_ai_task(topic) 
            
            if ai_task_data:
                question_text, correct_answer, incorrect_options, explanation = ai_task_data
                
                if question_text and question_text not in processed_texts and question_text not in existing_question_texts_to_exclude: # Убедимся, что question_text не None
                    db.add_task_from_ai(topic, question_text, correct_answer, incorrect_options, explanation)
                    new_task_tuple = (question_text, correct_answer, explanation, incorrect_options)
                    final_tasks_list.append(new_task_tuple)
                    processed_texts.add(question_text)
                    generated_ai_count_successfully_added += 1
                    logging.info(f"Successfully generated, saved, and added new unique AI task. Total unique tasks in list now: {len(final_tasks_list)}")
                elif not question_text:
                    logging.warning(f"AI task generation returned None for question_text on attempt {current_ai_generation_attempt}.")
                else: # question_text был дубликатом
                    logging.warning(f"AI generated a question text that is already in processed_texts: '{question_text[:70]}...' on attempt {current_ai_generation_attempt}")
            else:
                logging.warning(f"AI failed to generate a task (None or incomplete data returned) on AI attempt {current_ai_generation_attempt}.")
        
        if len(final_tasks_list) < needed:
            logging.warning(f"Could only gather {len(final_tasks_list)} unique tasks out of {needed} needed for topic '{topic}' after {max_total_ai_generation_attempts} AI attempts (force_ai={force_ai}).")
        logging.info(f"Finished AI generation phase for topic '{topic}'. Added {generated_ai_count_successfully_added} new unique AI tasks to the list during this phase (force_ai={force_ai}).")

    if not final_tasks_list and needed > 0:
        logging.error(f"No tasks found or generated for topic '{topic}' (force_ai={force_ai}, needed={needed}). Returning empty list.")
        return []

    random.shuffle(final_tasks_list) # Перемешиваем перед возвратом среза
    return final_tasks_list[:needed] # Гарантируем возврат не более 'needed' вопросов

async def back_to_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_topics(update, context)

async def prev_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['current_question'] > 0:
        context.user_data['current_question'] -= 1
    await ask_question(update, context)

async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_num = context.user_data['current_question']
    max_reached = context.user_data.get('max_reached_question', 0)
    if q_num < max_reached:
        context.user_data['current_question'] += 1
    await ask_question(update, context)

async def show_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # q_num_to_show будет 1-based, так как кнопки генерируются с 1-based номерами
    q_num_to_show = int(query.data.replace("show_expl_", "")) 
    
    errors = context.user_data.get('errors', [])
    error_info = None
    for err in errors:
        # err['q_num'] также 1-based
        if err['q_num'] == q_num_to_show:
            error_info = err
            break

    if error_info:
        question_text = error_info['question']
        explanation = error_info['explanation']
        
        full_explanation_text = (
            f"<b>Вопрос {q_num_to_show}:</b> {escape(question_text)}\n\n"
            f"<b>Объяснение:</b>\n{escape(explanation)}"
        )

        last_expl_info = context.user_data.get('last_explanation_message_info_on_results')
        chat_id_for_message = query.message.chat.id # Chat ID where the results message (and button) is
        message_handled = False

        if last_expl_info and isinstance(last_expl_info, dict):
            try:
                await context.bot.edit_message_text(
                    chat_id=last_expl_info['chat_id'],
                    message_id=last_expl_info['message_id'],
                    text=full_explanation_text,
                    parse_mode="HTML"
                )
                await query.answer()
                message_handled = True
            except telegram.error.BadRequest as e:
                if "message is not modified" in str(e).lower():
                    await query.answer("Это объяснение уже показано.")
                    message_handled = True
                elif "message to edit not found" in str(e).lower():
                    logging.warning(f"Message to edit explanation (ID: {last_expl_info.get('message_id')}) not found. Will send new.")
                    context.user_data.pop('last_explanation_message_info_on_results', None)
                else:
                    logging.warning(f"Failed to edit explanation message (ID: {last_expl_info.get('message_id')}), will send new: {e}")
                    context.user_data.pop('last_explanation_message_info_on_results', None)
            except Exception as e:
                logging.error(f"Unexpected error editing explanation (ID: {last_expl_info.get('message_id')}): {e}")
                context.user_data.pop('last_explanation_message_info_on_results', None)

        if not message_handled: 
            try:
                sent_message = await query.message.reply_text(
                    text=full_explanation_text,
                    parse_mode="HTML",
                    reply_to_message_id=query.message.message_id 
                )
                context.user_data['last_explanation_message_info_on_results'] = {
                    'message_id': sent_message.message_id,
                    'chat_id': sent_message.chat.id 
                }
                await query.answer()
            except Exception as e:
                logging.error(f"Failed to send new explanation message: {e}")
                await query.answer("Не удалось показать объяснение.", show_alert=True)
                
    else:
        await query.answer("Объяснение для этого вопроса не найдено.", show_alert=True)

def generate_universal_options(correct_answer_str: str, db=None, topic=None) -> list[str]:
    """
    Генерирует 4 варианта ответа, включая правильный.
    Если правильный ответ числовой (с единицей измерения или без), генерирует похожие числовые варианты.
    Иначе, использует общие фразы-дистракторы.
    Гарантирует, что правильный ответ всегда есть среди вариантов и всего 4 уникальных варианта.
    """
    import random
    import re

    correct_answer_str = str(correct_answer_str).strip()
    options = {correct_answer_str}  # Используем set для автоматической уникальности

    # Попытка распознать число и единицу измерения
    num_match = re.match(r"^(-?\d+([.,]\d+)?)\s*(.*)$", correct_answer_str.strip())
    
    generated_numeric_options = False # Флаг, что мы смогли сгенерировать числовые опции

    if num_match:
        num_val_str = num_match.group(1)
        unit = num_match.group(3).strip()
        try:
            num_val = float(num_val_str.replace(',', '.'))
            is_int_val = num_val == int(num_val)
            if is_int_val:
                num_val = int(num_val)

            # Генерация числовых дистракторов
            # Попробуем создать несколько вариантов, чтобы было из чего выбрать
            possible_distractors = set()
            for i in range(10): # Сгенерируем побольше кандидатов
                if len(options) + len(possible_distractors) >= 4 and i > 3: # Если уже набрали достаточно с правильным
                    break

                delta_abs = max(1, abs(num_val) * random.uniform(0.1, 0.5)) # Отклонение от 10% до 50%
                if is_int_val:
                    delta_abs = max(1, round(delta_abs))
                
                op_choice = random.choice([-1, 1, -2, 2]) # Разные операции

                if op_choice == 1 : # Сложение
                    dist_candidate_val = num_val + delta_abs * (1 + random.random())
                elif op_choice == -1: # Вычитание
                    dist_candidate_val = num_val - delta_abs * (1 + random.random())
                elif op_choice == 2 and num_val != 0: # Умножение (если не 0)
                    factor = random.choice([0.5, 1.5, 2, 0.75, 1.25])
                    dist_candidate_val = num_val * factor
                else: # Деление (если не 0) или альтернативное сложение/вычитание
                    if num_val != 0 and random.choice([True, False]):
                        factor = random.choice([2,3,4])
                        dist_candidate_val = num_val / factor
                    else: # еще одно смещение
                         dist_candidate_val = num_val + delta_abs * random.choice([-1.5, 1.5])


                # Обработка и форматирование дистрактора
                if is_int_val:
                    dist_candidate_val = round(dist_candidate_val)
                else:
                    dist_candidate_val = round(dist_candidate_val, 2)

                # Если исходное число положительное, стараемся делать дистракторы положительными
                if num_val > 0 and dist_candidate_val <= 0:
                    if num_val > 1 and is_int_val: # если было целое > 1, сделаем хотя бы 1
                         dist_candidate_val = max(1, round(num_val * random.uniform(0.1,0.5)))
                    elif not is_int_val and num_val > 0.01:
                         dist_candidate_val = round(max(0.01, num_val * random.uniform(0.1,0.5)),2)
                    else: # если было маленькое, просто возьмем по модулю или чуть больше
                        dist_candidate_val = abs(dist_candidate_val) + (1 if is_int_val else 0.01)


                option_str = f"{dist_candidate_val} {unit}".strip() if is_int_val else f"{dist_candidate_val:.2f} {unit}".strip()
                
                if option_str != correct_answer_str: # Не добавляем дистрактор, если он совпал с правильным
                    possible_distractors.add(option_str)

            # Добавляем уникальные дистракторы в основные опции, пока не наберем 3 (с CA будет 4)
            for distractor in list(possible_distractors):
                if len(options) < 4:
                    options.add(distractor)
                else:
                    break
            
            if len(options) > 1 : # Если мы добавили хотя бы один числовой дистрактор
                generated_numeric_options = True

        except ValueError:
            # Если не удалось преобразовать число (маловероятно после regex), переходим к общим дистракторам
            pass # Логика ниже обработает заполнение до 4 опций
    
    # Если числовые дистракторы не были сгенерированы ИЛИ их не хватило
    if not generated_numeric_options or len(options) < 4:
        generic_distractors_pool = [
            "Не уверен", "Другой вариант", "Нужно подумать", "Сложно сказать",
            "Проверю еще раз", "Затрудняюсь ответить", "Не знаю", "Это неверно"
        ]
        # Убедимся, что правильный ответ не похож на один из общих дистракторов
        generic_distractors_pool = [d for d in generic_distractors_pool if d.lower() != correct_answer_str.lower()]
        random.shuffle(generic_distractors_pool)
        
        idx = 0
        while len(options) < 4 and idx < len(generic_distractors_pool):
            options.add(generic_distractors_pool[idx])
            idx += 1

    # Если все еще не хватает (крайне маловероятно), добавляем нумерованные заглушки
    placeholder_idx = 1
    while len(options) < 4:
        options.add(f"Вариант {placeholder_idx + 100}") # +100 чтобы избежать случайных совпадений
        placeholder_idx += 1
        
    final_options_list = list(options)
    # Убедимся, что правильный ответ точно есть, если вдруг set его как-то вытеснил (не должен)
    if correct_answer_str not in final_options_list:
        if len(final_options_list) == 4: # Заменяем последний, если уже 4
            final_options_list[-1] = correct_answer_str
        else: # Добавляем, если меньше 4 (не должно быть по логике выше)
            final_options_list.append(correct_answer_str)


    random.shuffle(final_options_list)
    
    # Гарантируем, что вернется ровно 4 варианта
    return final_options_list[:4]

async def go_to_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает нажатие инлайн-кнопки 'main_menu', обычно с экрана результатов.
    Отправляет новое сообщение с основной ReplyKeyboardMarkup.
    """
    query = update.callback_query
    
    if not query or not query.message:
        logging.error("go_to_main_menu_callback: query или query.message отсутствует.")
        if query:
            try:
                await query.answer("Ошибка: не удалось вернуться в меню.", show_alert=True)
            except Exception as e_ans:
                logging.error(f"Ошибка при ответе на query в go_to_main_menu_callback (начальная проверка): {e_ans}")
        return

    try:
        await query.answer() # Убираем "часики" с инлайн-кнопки
    except Exception as e_ans:
        logging.error(f"Ошибка при ответе на query в go_to_main_menu_callback: {e_ans}")

    # Очищаем данные сессии теста
    context.user_data.clear()
    logging.info(f"Данные пользователя {query.from_user.id} очищены.")

    # Логируем тип и значение main_menu_markup для диагностики
    logging.info(f"Попытка отправить главное меню. Тип main_menu_markup: {type(main_menu_markup)}, значение: {main_menu_markup!r}")

    menu_message_text = "✅ Главное меню загружено. Выберите действие:"

    try:
        # --- BEGIN EDIT: Corrected ReplyKeyboardRemove instantiation ---
        # Сначала отправляем сообщение с ReplyKeyboardRemove, чтобы "очистить" клавиатуру
        # Это сообщение может быть невидимым или очень коротким, если клиент его быстро обработает.
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="...", # Можно использовать очень короткий текст или даже невидимый символ (например, \u200B)
            reply_markup=ReplyKeyboardRemove() # <--- ИСПРАВЛЕНО: без аргументов
        )
        logging.info(f"Отправлено ReplyKeyboardRemove в чат {query.message.chat.id}")
        # --- END EDIT ---

        # Затем отправляем новое сообщение с ReplyKeyboardMarkup
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=menu_message_text,
            reply_markup=main_menu_markup
        )
        logging.info(f"Сообщение '{menu_message_text}' с главным меню (ReplyKeyboardMarkup) отправлено в чат {query.message.chat.id}")
        
        # Удаляем предыдущее сообщение (с инлайн-кнопками)
        # Лучше делать это после успешной отправки нового меню
        try:
            await query.delete_message()
            logging.info(f"Предыдущее сообщение (ID: {query.message.message_id}) удалено в чате {query.message.chat.id}")
        except telegram.error.BadRequest as e_del:
            if "message to delete not found" in str(e_del).lower():
                logging.info(f"Сообщение {query.message.message_id} для удаления не найдено (возможно, уже удалено).")
            elif "message can't be deleted" in str(e_del).lower():
                 logging.warning(f"Сообщение {query.message.message_id} не может быть удалено (слишком старое или нет прав).")
            else:
                logging.error(f"Ошибка при удалении предыдущего сообщения {query.message.message_id}: {e_del}")
        except Exception as e_del_generic:
            logging.error(f"Непредвиденная ошибка при удалении предыдущего сообщения {query.message.message_id}: {e_del_generic}")

    except Exception as e:
        logging.error(f"Ошибка при отправке главного меню или удалении предыдущего сообщения в go_to_main_menu_callback: {e}")
        # Попытка отправить запасное сообщение пользователю, если что-то пошло не так с основным меню
        try:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Не удалось загрузить главное меню. Пожалуйста, попробуйте ввести команду /start"
            )
        except Exception as e_fallback:
            logging.error(f"Ошибка при отправке запасного сообщения в go_to_main_menu_callback: {e_fallback}")

def main():
    # Создаем приложение
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(show_topics, pattern="^start_test$"))
    application.add_handler(CallbackQueryHandler(show_help, pattern="^show_help$"))
    application.add_handler(CallbackQueryHandler(start_test, pattern="^topic_"))
    application.add_handler(CallbackQueryHandler(check_answer, pattern="^ans_"))
    # Изменяем обработчик для "main_menu"
    application.add_handler(CallbackQueryHandler(go_to_main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(back_to_topics, pattern="^back_to_topics$"))
    application.add_handler(CallbackQueryHandler(prev_question, pattern="^prev_question$"))
    application.add_handler(CallbackQueryHandler(next_question, pattern="^next_question$"))
    application.add_handler(CallbackQueryHandler(show_explanation, pattern="^show_expl_"))
    application.add_handler(CallbackQueryHandler(continue_test, pattern="^continue_test$"))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
