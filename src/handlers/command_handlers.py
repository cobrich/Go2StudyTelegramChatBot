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

        # Проверяем доступ пользователя (админ, whitelist по username или user_id)
        if not self.db.check_user_access(user.id, user.username):
            await update.message.reply_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user.id}\n"
                f"Username: @{user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return

        # Регистрируем пользователя в базе, если его нет
        self.db.register_user(user.id, user.username)

        # Проверяем, является ли пользователь админом
        is_admin = self.db.is_admin(user.id)
        
        # Проверяем, есть ли ФИО и класс (для админов класс не обязателен)
        user_info = self.db.get_user_info(user.id)
        if not user_info or not user_info[0]:
            # Если нет ФИО - спрашиваем у всех (включая админов)
            context.user_data['awaiting_full_name'] = True
            await update.message.reply_text("Пожалуйста, введите ваше ФИО:")
            return
        elif not is_admin and not user_info[1]:
            # Если нет класса и пользователь НЕ админ - спрашиваем класс
            context.user_data['awaiting_grade'] = True
            context.user_data['full_name'] = user_info[0]  # Сохраняем ФИО
            await update.message.reply_text("Пожалуйста, введите ваш класс (4, 5 или 6):")
            return

        # Clear previous session data
        self.clear_user_data(context)
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
        except Exception as e:
            logging.error(f"Error sending ReplyKeyboardRemove during /start for chat {chat_id}: {e}")

        try:
            await update.message.reply_html(
                text=welcome_text,
                reply_markup=self.main_menu_markup
            )
        except Exception as e:
            logging.error(f"Error sending welcome message with main_menu_markup during /start for chat {chat_id}: {e}")
            try:
                await update.message.reply_text(
                    "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова."
                )
            except Exception as e_fallback:
                logging.error(f"Error sending fallback error message during /start for chat {chat_id}: {e_fallback}")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Stop the bot and clear user data."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        # Clear user activity
        self.db.clear_user_activity(user_id)
        
        # Clear context data
        context.user_data.clear()
        
        await update.message.reply_text(
            "🛑 Бот остановлен. Все данные очищены.\n\nДля нового старта используйте /start",
            reply_markup=ReplyKeyboardRemove()
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reset user state if stuck in a test."""
        user_id = update.effective_user.id
        
        # Проверяем доступ пользователя
        if not self.db.check_user_access(user_id, update.effective_user.username):
            await update.message.reply_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{update.effective_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return
        
        # Clear user activity
        self.db.set_user_inactive(user_id)
        
        # Clear context data
        context.user_data.clear()
        
        await update.message.reply_text(
            "🔄 Состояние сброшено. Можете начать заново.",
            reply_markup=self.main_menu_markup
        )
    
    async def get_my_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать user_id пользователя (временная команда для настройки админа)."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "не указан"
        first_name = update.effective_user.first_name or "не указано"
        last_name = update.effective_user.last_name or ""
        
        full_name = f"{first_name} {last_name}".strip()
        
        await update.message.reply_text(
            f"🆔 **Ваши данные:**\n\n"
            f"**User ID:** `{user_id}`\n"
            f"**Username:** @{username}\n"
            f"**Имя:** {full_name}\n\n"
            f"Используйте User ID `{user_id}` для добавления в качестве админа.",
            parse_mode='Markdown'
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Проверяем доступ пользователя перед обработкой любых сообщений
        if not self.db.check_user_access(user_id, update.effective_user.username):
            await update.message.reply_text(
                f"❌ Извините, у вас нет доступа к этому боту.\n\n"
                f"Ваш ID: {user_id}\n"
                f"Username: @{update.effective_user.username or 'не указан'}\n\n"
                f"Для получения доступа обратитесь к администратору."
            )
            return
        
        # Проверка на ввод ФИО
        if context.user_data.get('awaiting_full_name'):
            full_name = text
            db_info = self.db.get_user_info(user_id)
            grade = db_info[1] if db_info else None
            language = db_info[2] if db_info else 'ru'
            
            # Проверяем, является ли пользователь админом
            is_admin = self.db.is_admin(user_id)
            
            self.db.set_user_info_with_language(user_id, full_name, grade, language)
            context.user_data['awaiting_full_name'] = False
            
            if is_admin:
                # Для админов сразу разрешаем пользоваться ботом
                await update.message.reply_text(
                    f"Спасибо, {full_name}! Вы администратор системы. Теперь вы можете пользоваться ботом.",
                    reply_markup=self.main_menu_markup
                )
            elif grade:
                # Для обычных пользователей с уже указанным классом
                await update.message.reply_text(
                    f"Спасибо! Ваше новое ФИО: {full_name}. Ваш класс: {grade}.",
                    reply_markup=self.main_menu_markup
                )
            else:
                # Для обычных пользователей без класса - запрашиваем класс
                context.user_data['awaiting_grade'] = True
                context.user_data['full_name'] = full_name
                await update.message.reply_text("Спасибо! Теперь введите ваш класс (4, 5 или 6):")
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
            
        # Проверяем, находится ли пользователь в режиме выбора темы
        if context.user_data.get('in_topic_selection'):
            # Если пользователь в режиме выбора темы, возвращаем к списку тем
            await update.message.reply_text(
                "📚 **Выберите раздел математики:**",
                reply_markup=build_topic_selection_keyboard(),
                parse_mode='Markdown'
            )
            return
            
        if text == "📚 Выбрать тему и начать":
            # Устанавливаем флаг выбора темы
            context.user_data['in_topic_selection'] = True
            # Сначала убираем обычную клавиатуру
            await update.message.reply_text(
                "💬",
                reply_markup=ReplyKeyboardRemove()
            )
            # Затем отправляем сообщение с inline-кнопками
            await update.message.reply_text(
                "📚 **Выберите раздел математики:**",
                reply_markup=build_topic_selection_keyboard(),
                parse_mode='Markdown'
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