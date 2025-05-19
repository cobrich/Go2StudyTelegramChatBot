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
import asyncio

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
MAX_QUESTIONS_PER_TEST = 10 # Убедимся, что эта константа есть, или используем DEFAULT_QUESTIONS_PER_TEST

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

# НОВАЯ ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ для создания клавиатуры выбора тем
def _build_topic_selection_keyboard() -> InlineKeyboardMarkup:
    """Создает InlineKeyboardMarkup для выбора темы, включая кнопку 'В главное меню'."""
    keyboard = [
        [InlineKeyboardButton(topic, callback_data=f"topic_{i}")]
        for i, topic in enumerate(TOPICS)
    ]
    # Добавляем кнопку "В главное меню" в конец списка
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главное меню при команде /start."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Очищаем данные сессии предыдущего теста (на случай, если пользователь перезапускает бота
    # или вводит /start во время другого активного процесса).
    context.user_data.clear()
    logging.info(f"User {user.id} ({user.username}) executed /start. User data cleared for chat {chat_id}.")
    context.user_data['session_started'] = True # Устанавливаем флаг начала сессии

    welcome_text = f"👋 Привет, {user.mention_html()}! Я бот для изучения математики. Выбери действие:"

    # Шаг 1: Попытка удалить любую "зависшую" клавиатуру (на всякий случай).
    # try:
    #     await context.bot.send_message(
    #         chat_id=chat_id,
    #         text="💬",  # ИЗМЕНЕНО: с \u200B на "." для предотвращения ошибки "Text must be non-empty"
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
    """Отображает список тем для выбора, редактируя существующее сообщение."""
    reply_markup = _build_topic_selection_keyboard() # Используем новую вспомогательную функцию
    
    query = update.callback_query # Эта функция обычно вызывается из callback
    if query:
        try:
            await query.edit_message_text(
                "📚 Выбери тему:",
                reply_markup=reply_markup
            )
        except telegram.error.BadRequest as e:
            if "message is not modified" in str(e).lower():
                await query.answer() # Сообщение не изменилось, просто подтверждаем
            else:
                logging.error(f"Ошибка редактирования сообщения в show_topics: {e}")
                # Попытка отправить новое сообщение, если редактирование не удалось
                if query.message:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="📚 Выбери тему: (ошибка редактирования)",
                        reply_markup=reply_markup
                    )
        except Exception as e:
            logging.error(f"Неожиданная ошибка в show_topics: {e}")
            # Попытка отправить новое сообщение в случае серьезной ошибки
            if query and query.message:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📚 Выбери тему: (неожиданная ошибка)",
                    reply_markup=reply_markup
                )
    else:
        # Эта ветка маловероятна, если show_topics вызывается только из колбэков,
        # таких как back_to_topics.
        logging.warning("show_topics вызвана без callback_query. Попытка отправить новое сообщение.")
        chat_id = update.effective_chat.id
        if chat_id:
             await context.bot.send_message(
                chat_id=chat_id,
                text="📚 Выбери тему:",
                reply_markup=reply_markup
            )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Проверяем, не активен ли уже пользователь
    if db.is_user_active(user_id):
        try:
            await query.answer("Вы уже проходите тест. Пожалуйста, завершите текущий тест перед началом нового.")
        except telegram.error.BadRequest as e:
            if "Query is too old" in str(e):
                logging.info(f"Old callback query ignored in start_test for user {user_id}")
            else:
                raise
        return

    topic_idx = int(query.data.split('_')[1])
    topic = TOPICS[topic_idx]

    # Показываем сообщение о загрузке вопросов сразу
    try:
        await query.edit_message_text("⏳ Загрузка вопросов...", reply_markup=None)
    except Exception as e:
        logging.warning(f"Не удалось показать сообщение о загрузке: {e}")

    # Запускаем генерацию вопросов и старт теста в фоне, чтобы не блокировать event loop
    asyncio.create_task(continue_start_test(update, context, user_id, topic))

async def continue_start_test(update, context, user_id, topic):
    # Очищаем user_data для чистого старта теста
    context.user_data.clear()
    context.user_data['current_topic'] = topic
    context.user_data['current_question'] = 0
    context.user_data['correct_answers'] = 0
    context.user_data['errors'] = []
    context.user_data['answered_questions'] = {}
    context.user_data['max_reached_question'] = 0

    # Устанавливаем пользователя как активного
    db.set_user_active(user_id, topic)

    # Получаем или генерируем задачи
    tasks = await get_or_generate_tasks(
        user_id=user_id,
        topic=topic,
        db=db,
        needed=DEFAULT_QUESTIONS_PER_TEST,
        force_ai=False
    )

    if not tasks:
        # Отправляем новое сообщение об ошибке (так как edit_message_text уже был вызван)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Извините, произошла ошибка при подготовке теста. Пожалуйста, попробуйте позже."
        )
        db.set_user_inactive(user_id)
        return

    context.user_data['tasks'] = tasks

    # Начинаем тест с первого вопроса
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_num = context.user_data['current_question']
    max_reached = context.user_data.get('max_reached_question', 0)
    questions_data = context.user_data['tasks'] # Список кортежей
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
            
            # Эта кнопка остается всегда для уже отвеченных вопросов при навигации
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
        
        # ИЗМЕНЕНИЕ: Кнопка "Назад к темам" только для первого вопроса (когда он еще не отвечен)
        if q_num == 0: 
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
    user_id = update.effective_user.id
    
    # Проверяем, активен ли пользователь
    if not db.is_user_active(user_id):
        await query.answer("Ваша сессия истекла. Пожалуйста, начните тест заново.")
        return
    
    # Обновляем время последней активности
    db.update_user_activity(user_id)
    
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
    questions_data = context.user_data['tasks']
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
    total_questions = len(context.user_data['tasks'])

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
    user_id = update.effective_user.id
    
    # Делаем пользователя неактивным
    db.set_user_inactive(user_id)
    
    # Очищаем user_data после завершения теста
    context.user_data.clear()
    
    correct_answers = context.user_data.get('correct_answers', 0)
    total_questions = len(context.user_data.get('tasks', []))
    
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
        db.add_test_result(user_id, context.user_data['current_topic'], percentage)

        text = (
            f"📊 <b>Результаты теста по теме \"{context.user_data['current_topic']}\":</b>\n\n"
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
        
        buttons.append([InlineKeyboardButton("🔄 Пройти еще раз эту тему", callback_data=f"topic_{TOPICS.index(context.user_data['current_topic'])}")])
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
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, не активен ли пользователь
    if db.is_user_active(user_id):
        await update.message.reply_text(
            "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. "
            "Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста."
        )
        return
    
    # Остальной код handle_message остается без изменений
    if text == "📚 Выбрать тему и начать":
        if db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. "
                "Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста.",
                reply_markup=main_menu_markup
            )
        else:
            await show_topics_from_message(update, context)
    elif text == "📊 Мой прогресс":
        if db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. "
                "Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста.",
                reply_markup=main_menu_markup
            )
        else:
            await show_progress_from_message(update, context)
    elif text == "❓ Помощь":
        if db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Чтобы выбрать другую опцию, пожалуйста, завершите текущий тест. "
                "Для возврата к выбору тем без завершения теста, перейдите к первому вопросу теста.",
                reply_markup=main_menu_markup
            )
        else:
            context.user_data.clear()
            await update.message.reply_text(HELP_TEXT, reply_markup=main_menu_markup)
    else:
        # For any other text input not matching the main menu commands
        if db.is_user_active(user_id):
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
    # --- BEGIN EDIT: Attempt to remove ReplyKeyboardMarkup FIRST ---
    # Сначала отправляем команду на удаление основной клавиатуры
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💬",
            reply_markup=ReplyKeyboardRemove()
        )
        logging.info(f"Sent ReplyKeyboardRemove command for chat {update.effective_chat.id} before showing topics.")
    except Exception as e:
        # Логируем ошибку, если не удалось отправить команду удаления, но продолжаем работу
        logging.error(f"Error sending ReplyKeyboardRemove in show_topics_from_message: {e}")
    # --- END EDIT ---

    reply_markup = _build_topic_selection_keyboard() # Используем новую вспомогательную функцию
    # Затем отправляем сообщение с выбором тем (инлайн-кнопки)
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

# Синхронная функция генерации AI-вопроса
def generate_ai_task_sync(topic):
    prompt_template = (
        "Твоя задача - быть экспертом по созданию обучающих математических задач для учеников 5-6 классов.\n"
        "Тебе нужно сгенерировать ОДИН уникальный и интересный вопрос по теме '{topic}'.\n"
        "Вопрос должен быть не просто на вычисление, а, по возможности, представлять собой небольшую текстовую задачу, логическую головоломку или задачу на применение математических концепций в жизненной ситуации, соответствующей теме. Избегай создания однотипных вопросов, отличающихся только числами.\n\n"
        "ТРЕБОВАНИЯ К ЗАДАЧЕ:\n"
        "1.  **Целевая аудитория:** Ученики 5-6 класса.\n"
        "2.  **Тема:** '{topic}'.\n"
        "3.  **Сложность:** Вопрос должен быть решаем в уме или с минимальными записями, обычно не более 2-3 логических шагов или математических операций. Он должен быть достаточно сложным, чтобы требовать размышлений, но не чрезмерно трудным.\n"
        "4.  **Уникальность:** Вопрос должен быть новым, не повторяющим предыдущие.\n"
        "5.  **Контекст и единицы:** Если в вопросе используются единицы измерения, ответ также должен быть в этих единицах. Все числовые значения и условия должны быть реалистичными и соответствовать теме.\n"
        "6.  **Правильный ответ:** Должен быть четким, однозначным и не превышать 60 символов.\n"
        "7.  **Неправильные ответы (3 шт.):** Должны быть правдоподобными, отражать типичные ошибки или заблуждения учеников по данной теме. Они не должны быть очевидно неверными.\n"
        "8.  **Объяснение:** Должно быть кратким, ясным, пошаговым (если применимо) и помогать понять логику решения и концепцию.\n\n"
        "СТРОГИЙ ФОРМАТ ВЫВОДА (КАЖДЫЙ ПУНКТ С НОВОЙ СТРОКИ, ЗАГОЛОВКИ ЗАГЛАВНЫМИ БУКВАМИ):\n"
        "ВОПРОС: [текст вопроса]\n"
        "ПРАВИЛЬНЫЙ ОТВЕТ: [текст правильного ответа]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: [текст первого неправильного варианта]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: [текст второго неправильного варианта]\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: [текст третьего неправильного варианта]\n"
        "ОБЪЯСНЕНИЕ: [текст объяснения правильного ответа]\n\n"
        "Пример структуры вопроса, который нужно СТРЕМИТЬСЯ создать (НЕ КОПИРОВАТЬ):\n"
        "Тема: 'Дроби'\n"
        "ВОПРОС: Маша испекла пирог и разрезала его на 8 равных частей. Она съела 1 часть, а ее брат Петя съел 3 части. Какая часть пирога осталась?\n"
        "ПРАВИЛЬНЫЙ ОТВЕТ: 4/8 (или 1/2)\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 1: 4 части\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 2: 1/8\n"
        "НЕПРАВИЛЬНЫЙ ОТВЕТ 3: 5/8\n"
        "ОБЪЯСНЕНИЕ: Всего было 8/8 пирога. Маша съела 1/8, Петя съел 3/8. Вместе они съели 1/8 + 3/8 = 4/8 пирога. Осталось 8/8 - 4/8 = 4/8 пирога. Дробь 4/8 можно сократить до 1/2.\n\n"
        "Убедись, что генерируемые вопросы разнообразны по своей структуре и типу (например, задачи на движение, на части, логические, геометрические элементы в рамках темы и т.д.), а не просто подстановка разных чисел в один и тот же шаблон."
    )
    prompt = prompt_template.format(topic=topic)
    try:
        response_text = model.generate_content(prompt).text
        import re
        q_match = re.search(r"ВОПРОС:\s*(.*?)\s*ПРАВИЛЬНЫЙ ОТВЕТ:", response_text, re.DOTALL | re.IGNORECASE)
        correct_a_match = re.search(r"ПРАВИЛЬНЫЙ ОТВЕТ:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|\s*ОБЪЯСНЕНИЕ:)", response_text, re.DOTALL | re.IGNORECASE)
        q = q_match.group(1).strip() if q_match else None
        correct_a = correct_a_match.group(1).strip() if correct_a_match else None
        incorrect_options = []
        search_start_index = 0
        if correct_a_match:
            first_incorrect_or_expl_match = re.search(r"НЕПРАВИЛЬНЫЙ ОТВЕТ 1:|ОБЪЯСНЕНИЕ:", response_text[correct_a_match.end():], re.IGNORECASE)
            if first_incorrect_or_expl_match:
                search_start_index = correct_a_match.end() + first_incorrect_or_expl_match.start()
        for match in re.finditer(r"НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:\s*(.*?)(?=\s*НЕПРАВИЛЬНЫЙ ОТВЕТ \d+:|\s*ОБЪЯСНЕНИЕ:|$)", response_text[search_start_index:], re.DOTALL | re.IGNORECASE):
            option_text = match.group(1).strip()
            if option_text:
                incorrect_options.append(option_text)
        e_match = re.search(r"ОБЪЯСНЕНИЕ:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        e = e_match.group(1).strip() if e_match else None
        if not (q and correct_a and e and len(incorrect_options) >= 1):
            return None, None, None, None
        return q, correct_a, incorrect_options, e
    except Exception as err:
        return None, None, None, None

# Асинхронная обёртка для генерации AI-вопроса
async def generate_ai_task(topic):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, generate_ai_task_sync, topic)

async def get_or_generate_tasks(
    user_id: int,
    topic: str, 
    db: Database, 
    needed: int = DEFAULT_QUESTIONS_PER_TEST, 
    force_ai: bool = False, 
    existing_question_texts_to_exclude: set = None
) -> list:
    if existing_question_texts_to_exclude is None:
        existing_question_texts_to_exclude = set()

    final_tasks_list = []
    processed_texts_this_call = set(existing_question_texts_to_exclude)

    logging.info(
        f"get_or_generate_tasks: user_id={user_id}, topic='{topic}', needed={needed}, force_ai={force_ai}, "
        f"exclude_count={len(existing_question_texts_to_exclude)}"
    )

    generate_all_via_ai_flow = force_ai
    error_tasks_collected_count = 0

    if not force_ai:
        error_tasks_raw = db.get_error_tasks_for_user(user_id, topic, limit=needed)
        
        temp_error_tasks_tuples = []
        for q_text, ans, expl, inc_opt_json in error_tasks_raw:
            if q_text not in processed_texts_this_call:
                try:
                    inc_opt_list = json.loads(inc_opt_json) if inc_opt_json else []
                except json.JSONDecodeError:
                    logging.warning(f"Failed to parse incorrect_options JSON for error task '{q_text[:50]}...'. Skipping.")
                    continue
                temp_error_tasks_tuples.append((q_text, ans, expl, inc_opt_list))
        
        if not temp_error_tasks_tuples:
            logging.info(f"User {user_id} has no usable unique error tasks for topic '{topic}'. Switching to full AI generation for {needed} questions.")
            generate_all_via_ai_flow = True
        else:
            logging.info(f"Prioritizing {len(temp_error_tasks_tuples)} unique error tasks for user {user_id}, topic '{topic}'.")
            for task_tuple in temp_error_tasks_tuples:
                if len(final_tasks_list) >= needed:
                    break
                final_tasks_list.append(task_tuple)
                processed_texts_this_call.add(task_tuple[0])
                error_tasks_collected_count += 1

    if not generate_all_via_ai_flow and len(final_tasks_list) < needed:
        num_needed_from_general_db = needed - len(final_tasks_list)
        db_tasks_pool_raw = db.get_tasks_for_topic(topic, limit=num_needed_from_general_db * 2 + len(processed_texts_this_call))
        
        for q_text, ans, expl, inc_opt_json_or_list in db_tasks_pool_raw:
            if len(final_tasks_list) >= needed:
                break
            if q_text not in processed_texts_this_call:
                inc_opt_list = []
                if isinstance(inc_opt_json_or_list, str):
                    try:
                        inc_opt_list = json.loads(inc_opt_json_or_list) if inc_opt_json_or_list else []
                    except json.JSONDecodeError:
                        continue
                elif isinstance(inc_opt_json_or_list, list):
                    inc_opt_list = inc_opt_json_or_list
                elif inc_opt_json_or_list is None:
                    inc_opt_list = []
                else:
                    continue

                task_tuple = (q_text, ans, expl, inc_opt_list)
                final_tasks_list.append(task_tuple)
                processed_texts_this_call.add(q_text)

    num_still_needed_for_ai = needed - len(final_tasks_list)

    if num_still_needed_for_ai > 0:
        # Генерируем вопросы параллельно (через run_in_executor)
        tasks = []
        for _ in range(num_still_needed_for_ai):
            tasks.append(generate_ai_task(topic))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, tuple) and len(result) == 4:
                question_text, correct_answer, incorrect_options, explanation = result
                if question_text and question_text not in processed_texts_this_call:
                    db.add_task_from_ai(topic, question_text, correct_answer, incorrect_options, explanation)
                    final_tasks_list.append((question_text, correct_answer, explanation, incorrect_options))
                    processed_texts_this_call.add(question_text)
                    if len(final_tasks_list) >= needed:
                        break

    if not final_tasks_list and needed > 0:
        logging.error(f"No tasks found or generated for topic '{topic}' (force_ai={force_ai}, needed={needed}). Returning empty list.")
        return []

    random.shuffle(final_tasks_list)
    return final_tasks_list[:needed]

async def back_to_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Attempt to delete the last explanation message shown on the results screen first
    last_expl_info = context.user_data.pop('last_explanation_message_info_on_results', None)
    if last_expl_info and isinstance(last_expl_info, dict): # Ensure it's the expected dict
        try:
            chat_id_for_log = update.effective_chat.id if update.effective_chat else "unknown_chat"
            await context.bot.delete_message(
                chat_id=last_expl_info['chat_id'],
                message_id=last_expl_info['message_id']
            )
            logging.info(f"Deleted previous explanation message {last_expl_info.get('message_id')} from chat {last_expl_info.get('chat_id')} via back_to_topics for chat {chat_id_for_log}.")
        except telegram.error.BadRequest as e:
            if "message to delete not found" in str(e).lower():
                logging.info(f"Previous explanation message {last_expl_info.get('message_id')} not found for deletion (back_to_topics).")
            else:
                logging.warning(f"Could not delete previous explanation message {last_expl_info.get('message_id')} (back_to_topics): {e}")
        except Exception as e:
            logging.error(f"Unexpected error deleting previous explanation message {last_expl_info.get('message_id')} (back_to_topics): {e}")

    # Очищаем все данные пользователя и делаем неактивным
    user_id = update.effective_user.id
    context.user_data.clear()
    db.set_user_inactive(user_id)
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

async def go_to_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user = update.effective_user # Получаем пользователя для возможного упоминания

    if query:
        await query.answer()
        try:
            # Попытка убрать инлайн-клавиатуру с предыдущего сообщения (например, с результатов теста)
            await query.edit_message_reply_markup(reply_markup=None)
        except telegram.error.BadRequest as e:
            if "message is not modified" in str(e).lower() or "message to edit not found" in str(e).lower():
                # Это нормально, если клавиатура уже убрана или сообщение не найдено
                pass
            else:
                logging.warning(f"Не удалось изменить разметку сообщения в go_to_main_menu_callback: {e}")
        except Exception as e:
            logging.error(f"Неожиданная ошибка при изменении разметки сообщения в go_to_main_menu_callback: {e}")
    
    # Attempt to delete the last explanation message shown on the results screen
    last_expl_info = context.user_data.pop('last_explanation_message_info_on_results', None)
    if last_expl_info and isinstance(last_expl_info, dict): # Ensure it's the expected dict
        try:
            await context.bot.delete_message(
                chat_id=last_expl_info['chat_id'],
                message_id=last_expl_info['message_id']
            )
            logging.info(f"Deleted previous explanation message {last_expl_info.get('message_id')} from chat {last_expl_info.get('chat_id')} via main_menu.")
        except telegram.error.BadRequest as e:
            if "message to delete not found" in str(e).lower():
                logging.info(f"Previous explanation message {last_expl_info.get('message_id')} not found for deletion (main_menu).")
            else:
                logging.warning(f"Could not delete previous explanation message {last_expl_info.get('message_id')} (main_menu): {e}")
        except Exception as e:
            logging.error(f"Unexpected error deleting previous explanation message {last_expl_info.get('message_id')} (main_menu): {e}")

    # Текст для сообщения с главным меню
    menu_text = f"✅ {user.mention_html()}, вы снова в главном меню. Выберите действие:"
    # Альтернативный, более простой текст:
    # menu_text = "Главное меню. Выберите действие:"

    try:
        # Лог перед отправкой, похожий на тот, что у вас уже есть
        logging.info(f"Попытка отправить главное меню для чата {chat_id}. Тип main_menu_markup: {type(main_menu_markup)}, значение: {main_menu_markup}")
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=menu_text,  # <--- ИЗМЕНЕНИЕ: Добавлен непустой текст
            reply_markup=main_menu_markup,
            parse_mode="HTML" # Если используете user.mention_html()
        )
        logging.info(f"Главное меню успешно отправлено в чат {chat_id} из go_to_main_menu_callback.")
    except Exception as e:
        # Эта ошибка соответствует той, что вы видите в логах
        logging.error(f"Ошибка при отправке главного меню в go_to_main_menu_callback для чата {chat_id}: {e}")
        try:
            # Отправка запасного сообщения пользователю
            await context.bot.send_message(
                chat_id=chat_id,
                text="Ошибка: Не удалось загрузить главное меню. Пожалуйста, попробуйте ввести команду /start"
            )
        except Exception as e_fallback:
            logging.error(f"Не удалось отправить сообщение об ошибке (fallback) в go_to_main_menu_callback для чата {chat_id}: {e_fallback}")
    logging.info(f"User {user.id} returned to main menu from an inline keyboard in chat {chat_id}.") # Ensure this existing log line is present

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not user:
        logging.warning("stop_command received update without effective_user.")
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Не удалось определить пользователя для остановки. Пожалуйста, убедитесь, что вы отправили команду из чата с ботом."
            )
        return

    user_id = user.id

    # Проверяем, была ли сессия начата
    if not context.user_data.get('session_started'):
        logging.info(f"User {user_id} ({user.username}) executed /stop before starting a session in chat {chat_id}.")
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Бот еще не был активирован командой /start. "
                "Для вас нет сохраненных данных. Чтобы начать, отправьте /start."
            )
        )
        return

    # Если сессия была начата, продолжаем с удалением данных
    logging.info(f"User {user_id} ({user.username}) executed /stop command in chat {chat_id} (session was active).")

    # Удаляем все данные пользователя, включая активные сессии
    db.set_user_inactive(user_id)
    success = db.delete_all_user_data(user_id)

    if success:
        logging.info(f"Successfully deleted all data for user {user_id} from the database.")
        context.user_data.clear()
        logging.info(f"Cleared context.user_data for user {user_id}.")
        
        response_text = (
            f"🗑️ Все ваши данные были удалены из моей памяти, {user.mention_html()}.\n\n"
            "Я не могу удалить историю этого чата самостоятельно, но вы можете сделать это вручную, если хотите.\n\n"
            "Если вы захотите начать заново, просто отправьте /start."
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬", # Dummy text for removing keyboard
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e_remove_keyboard:
            logging.warning(f"Could not remove reply keyboard for user {user_id} during /stop: {e_remove_keyboard}")

        await context.bot.send_message(
            chat_id=chat_id,
            text=response_text,
            parse_mode='HTML'
        )
    else:
        logging.error(f"Failed to delete data for user {user_id} from the database.")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка при удалении ваших данных. Пожалуйста, попробуйте еще раз или свяжитесь с администратором, если проблема сохранится."
        )

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
    application.add_handler(CallbackQueryHandler(show_explanation, pattern=r"^show_expl_\d+$")) # Corrected pattern
    application.add_handler(CallbackQueryHandler(continue_test, pattern="^continue_test$"))
    
    # Handler for /stop command
    application.add_handler(CommandHandler("stop", stop_command))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
