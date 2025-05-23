from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging
from handlers.base_handler import BaseHandler
from utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard
from config.constants import HELP_TEXT, TOPICS

class CommandHandlers(BaseHandler):
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Регистрируем пользователя в базе, если его нет
        self.db.register_user(user.id, user.username)

        # Проверяем, есть ли ФИО и класс
        user_info = self.db.get_user_info(user.id)
        if not user_info or not user_info[0] or not user_info[1] or not user_info[2]:
            context.user_data['awaiting_full_name'] = True
            await update.message.reply_text("Пожалуйста, введите ваше ФИО:")
            return

        # Clear previous session data
        self.clear_user_data(context)
        logging.info(f"User {user.id} ({user.username}) executed /start. User data cleared for chat {chat_id}.")
        self.set_user_data(context, 'session_started', True)

        self.db.set_all_users_inactive()

        welcome_text = f"👋 Привет, {user.mention_html()}! Я бот для изучения математики. Выбери действие:"

        try:
            # Try to remove any existing keyboard
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬",
                reply_markup=ReplyKeyboardRemove()
            )
            logging.info(f"Sent ReplyKeyboardRemove to chat {chat_id} as part of /start sequence.")
        except Exception as e:
            logging.error(f"Error sending ReplyKeyboardRemove during /start for chat {chat_id}: {e}")

        try:
            await update.message.reply_html(
                text=welcome_text,
                reply_markup=self.main_menu_markup
            )
            logging.info(f"Welcome message with main_menu_markup sent to chat {chat_id} for user {user.id}.")
        except Exception as e:
            logging.error(f"Error sending welcome message with main_menu_markup during /start for chat {chat_id}: {e}")
            try:
                await update.message.reply_text(
                    "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова."
                )
            except Exception as e_fallback:
                logging.error(f"Error sending fallback error message during /start for chat {chat_id}: {e_fallback}")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_id = user.id if user else None

        # Всегда сбрасываем активность и очищаем user_data
        if user_id:
            self.db.set_user_inactive(user_id)
            self.clear_user_data(context)
            self.db.delete_all_user_data(user_id)

        if not user:
            logging.warning("stop_command received update without effective_user.")
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Не удалось определить пользователя для остановки. Пожалуйста, убедитесь, что вы отправили команду из чата с ботом."
                )
            return

        response_text = (
            f"🗑️ Все ваши данные были удалены из моей памяти, {user.mention_html()}.\n\n"
            "Я не могу удалить историю этого чата самостоятельно, но вы можете сделать это вручную, если хотите.\n\n"
            "Если вы захотите начать заново, просто отправьте /start."
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e_remove_keyboard:
            logging.warning(f"Could not remove reply keyboard for user {user_id} during /stop: {e_remove_keyboard}")

        await context.bot.send_message(
            chat_id=chat_id,
            text=response_text,
            parse_mode='HTML'
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        # Проверка на ввод ФИО
        if context.user_data.get('awaiting_full_name'):
            full_name = text
            db_info = self.db.get_user_info(user_id)
            grade = db_info[1] if db_info else None
            language = db_info[2] if db_info else 'ru'
            self.db.set_user_info_with_language(user_id, full_name, grade, language)
            context.user_data['awaiting_full_name'] = False
            await update.message.reply_text(
                f"Спасибо! Ваше новое ФИО: {full_name}. Ваш класс: {grade}.",
                reply_markup=self.main_menu_markup
            )
            return
        # Проверка на ввод класса
        if context.user_data.get('awaiting_grade'):
            try:
                grade = int(text)
                if grade not in [4, 5, 6]:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("Пожалуйста, введите корректный класс: 4, 5 или 6.")
                return
            context.user_data['grade'] = grade
            context.user_data['awaiting_grade'] = False
            context.user_data['awaiting_language'] = True
            await update.message.reply_text("Спасибо! Теперь выберите язык для вопросов:\n\n1 - Русский\n2 - Қазақша")
            return
        # Проверка на ввод языка
        if context.user_data.get('awaiting_language'):
            if text == "1":
                language = "ru"
                language_name = "Русский"
            elif text == "2":
                language = "kk"
                language_name = "Қазақша"
            else:
                await update.message.reply_text("Пожалуйста, выберите 1 для русского или 2 для казахского языка.")
                return
            full_name = context.user_data.get('full_name')
            grade = context.user_data.get('grade')
            self.db.set_user_info_with_language(user_id, full_name, grade, language)
            context.user_data['awaiting_language'] = False
            await update.message.reply_text(f"Спасибо, {full_name}! Ваш класс: {grade}, язык: {language_name}. Теперь вы можете пользоваться ботом.", reply_markup=self.main_menu_markup)
            return
        # CRUD команды для изменения ФИО и класса
        if text.lower() == "/change_fio":
            context.user_data['awaiting_full_name'] = True
            await update.message.reply_text("Введите новое ФИО:")
            return
        if text.lower() == "/change_grade":
            context.user_data['awaiting_grade_only'] = True
            await update.message.reply_text("Введите новый класс (4, 5 или 6):")
            return
        if text.lower() == "/change_language":
            context.user_data['awaiting_language_only'] = True
            await update.message.reply_text("Выберите язык для вопросов:\n\n1 - Русский\n2 - Қазақша")
            return
        # Проверка на изменение только класса
        if context.user_data.get('awaiting_grade_only'):
            try:
                grade = int(text)
                if grade not in [4, 5, 6]:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("Пожалуйста, введите корректный класс: 4, 5 или 6.")
                return
            # Получаем ФИО и язык: из базы
            db_info = self.db.get_user_info(user_id)
            full_name = db_info[0] if db_info else None
            language = db_info[2] if db_info else 'ru'
            self.db.set_user_info_with_language(user_id, full_name, grade, language)
            context.user_data['awaiting_grade_only'] = False
            await update.message.reply_text(f"Спасибо, {full_name}! Ваш класс: {grade}. Теперь вы можете пользоваться ботом.", reply_markup=self.main_menu_markup)
            return
        # Проверка на изменение только языка
        if context.user_data.get('awaiting_language_only'):
            if text == "1":
                language = "ru"
                language_name = "Русский"
            elif text == "2":
                language = "kk"
                language_name = "Қазақша"
            else:
                await update.message.reply_text("Пожалуйста, выберите 1 для русского или 2 для казахского языка.")
                return
            # Получаем ФИО и класс из базы
            db_info = self.db.get_user_info(user_id)
            full_name = db_info[0] if db_info else None
            grade = db_info[1] if db_info else None
            self.db.set_user_info_with_language(user_id, full_name, grade, language)
            context.user_data['awaiting_language_only'] = False
            await update.message.reply_text(f"Спасибо, {full_name}! Язык изменен на: {language_name}.", reply_markup=self.main_menu_markup)
            return
        # If user is in a test, block main menu actions
        if self.db.is_user_active(user_id):
            await update.message.reply_text(
                "Вы проходите тест. Для выбора других опций завершите тест или вернитесь к темам через кнопку 'Назад к темам' в тесте.",
                reply_markup=None
            )
            return
        if text == "📚 Выбрать тему и начать":
            # Сначала убираем обычную клавиатуру
            await update.message.reply_text(
                "💬",
                reply_markup=ReplyKeyboardRemove()
            )
            # Затем отправляем сообщение с inline-кнопками
            await update.message.reply_text(
                "Выберите тему:",
                reply_markup=build_topic_selection_keyboard()
            )
        elif text == "📊 Мой прогресс":
            total_tests, avg_percentage = self.db.get_user_progress(user_id)
            if avg_percentage is None:
                avg_percentage = 0.0
            recent_topics = self.db.get_recent_unique_topics(user_id, unique_limit=5, history_limit=20)
            error_topics = self.db.get_error_topics(user_id)

            progress_text = f"📊 Ваш прогресс:\n\n"
            progress_text += f"Всего тестов: {total_tests}\n"
            progress_text += f"Средний результат: {avg_percentage:.1f}%\n\n"

            if recent_topics:
                progress_text += "Недавние темы: " + ", ".join([f"{topic} ({count})" for topic, count in recent_topics]) + "\n"
            if error_topics:
                progress_text += "Темы с ошибками: " + ", ".join([f"{t[0]} ({t[1]})" for t in error_topics]) + "\n"

            await update.message.reply_text(progress_text)
        elif text == "❓ Помощь":
            await update.message.reply_text(HELP_TEXT)
        else:
            await update.message.reply_text("Пожалуйста, выберите действие из меню.", reply_markup=self.main_menu_markup)

    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        topic_index = query.data.replace('topic_', '')
        try:
            topic_index = int(topic_index)
            topic = TOPICS[topic_index]
        except (ValueError, IndexError):
            logging.error(f"Invalid topic selected: {topic_index}")
            await query.message.edit_text(
                "Произошла ошибка при выборе темы. Пожалуйста, попробуйте еще раз.",
                reply_markup=build_topic_selection_keyboard()
            )
            return

        # Handle topic selection
        # ... (rest of the method remains unchanged)

        # ... (rest of the method remains unchanged) 