import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import random
import asyncio
from src.handlers.base_handler import BaseHandler
from src.utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard, build_question_keyboard
from src.utils.translations import get_message, get_language_change_warning
from src.config.constants import HELP_TEXT, TOPICS
from src.services.random_test_service import RandomTestService

class CommandHandlers(BaseHandler):
    def __init__(self, db=None, question_service=None):
        super().__init__()
        # Переопределяем db и question_service если переданы
        if db:
            self.db = db
        if question_service:
            self.question_service = question_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_language = self.db.get_user_language(user.id)

        # Создаем telegram_data для использования в различных функциях
        telegram_data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        # Автоматически обновляем username если он есть
        if user.username:
            self.db.auto_update_username_from_telegram(user.id, telegram_data)

        # Проверяем доступ пользователя (админ, whitelist по username или user_id)
        if not self.db.check_user_access(user.id, user.username):
            await update.message.reply_text(
                get_message('no_access', user_language, 
                          user_id=user.id, 
                          username=user.username or 'не указан')
            )
            return

        # Проверяем, является ли пользователь админом
        is_admin = self.db.is_admin(user.id)
        
        if not is_admin:
            # Для обычных пользователей - пытаемся автоматически настроить из whitelist
            setup_success = self.db.auto_setup_user_from_whitelist(user.id, telegram_data)
            
            if setup_success:
                # Показываем сообщение об автоматической настройке
                auto_setup_message = f"✅ <b>Добро пожаловать!</b>\n\n"
                auto_setup_message += f"🔄 Ваши данные автоматически настроены из whitelist\n\n"
                auto_setup_message += f"\n📚 Теперь вы можете пользоваться ботом!"
                
                await update.message.reply_html(auto_setup_message)
            
            # Получаем информацию о пользователе после настройки
            user_info = self.db.get_user_info(user.id)
            
            # Для обычных пользователей - проверяем ФИО и класс (на случай если автонастройка не сработала)
            if not user_info or not user_info.get('full_name'):  # Нет ФИО
                context.user_data['awaiting_full_name'] = True
                fullname_request = "Пожалуйста, введите ваше ФИО:" if user_language == 'ru' else "Толық атыңызды енгізіңіз:"
                await update.message.reply_text(fullname_request)
                return
            elif not user_info.get('grade'):  # Нет класса
                context.user_data['awaiting_grade'] = True
                context.user_data['full_name'] = user_info.get('full_name')
                grade_request = "Пожалуйста, введите ваш класс (5, 6 или 7):" if user_language == 'ru' else "Сыныбыңызды енгізіңіз (5, 6 немесе 7):"
                await update.message.reply_text(grade_request)
                return
            
            # Если все данные есть - показываем приветствие
            welcome_name = user_info.get('full_name') if user_info else user.first_name or "пользователь"
            grade_text = f", {user_info.get('grade')} класс" if user_info and user_info.get('grade') else ""
            if user_language == 'kk':
                grade_text = f", {user_info.get('grade')} сынып" if user_info and user_info.get('grade') else ""
                welcome_text = get_message('welcome', user_language, name=welcome_name, grade=user_info.get('grade') if user_info else '') + "\n\n" + get_message('bot_description', user_language)
            else:
                welcome_text = f"👋 Привет, {welcome_name}{grade_text}!\n\n📚 Я бот для изучения математики. Выбери действие:"
        else:
            # Для админов - проверяем ФИО из таблицы admins
            admin_info = self.db.get_admin_info(user.id)
            
            if not admin_info or not admin_info['full_name']:  # Нет ФИО в таблице admins
                context.user_data['awaiting_admin_full_name'] = True
                admin_fullname_request = "👨‍💼 Добро пожаловать, администратор! Пожалуйста, введите ваше ФИО:" if user_language == 'ru' else "👨‍💼 Қош келдіңіз, әкімші! Толық атыңызды енгізіңіз:"
                await update.message.reply_text(admin_fullname_request)
                return
            
            # Если ФИО есть в admins - показываем приветствие
            welcome_name = admin_info['full_name']
            if user_language == 'kk':
                welcome_text = f"👋 Қош келдіңіз, {welcome_name}!\n\n🔧 Сіз <b>әкімші</b> ретінде кірдіңіз.\n\nӘрекетті таңдаңыз:"
            else:
                welcome_text = f"👋 Добро пожаловать, {welcome_name}!\n\n🔧 Вы вошли как <b>администратор</b>.\n\nВыберите действие:"

        # Clear previous session data
        self.clear_user_data(context)
        self.set_user_data(context, 'session_started', True)

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
                reply_markup=get_main_menu_markup(user.id)
            )
        except Exception as e:
            logging.error(f"Error sending welcome message with main_menu_markup during /start for chat {chat_id}: {e}")
            try:
                error_text = get_message('menu_load_error', user_language)
                await update.message.reply_text(error_text)
            except Exception as e_fallback:
                logging.error(f"Error sending fallback error message during /start for chat {chat_id}: {e_fallback}")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Stop the bot and clear user data."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        username = update.effective_user.username or "unknown"
        
        # Clear user activity
        self.db.clear_user_activity(user_id)
        
        # Clear context data
        context.user_data.clear()
        
        stop_text = get_message('bot_stopped', user_language)
        await update.message.reply_text(
            stop_text,
            reply_markup=ReplyKeyboardRemove()
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reset user state if stuck in a test."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя
        if not self.db.check_user_access(user_id, update.effective_user.username):
            await update.message.reply_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=update.effective_user.username or 'не указан')
            )
            return
        
        # ПРИНУДИТЕЛЬНО очищаем состояние пользователя (даже если он в тесте)
        # Clear user activity (is_active status)
        self.db.set_user_inactive(user_id)
        
        # Clear current test topic
        self.db.clear_user_test_activity(user_id)
        
        # Clear context data
        context.user_data.clear()
        
        reset_text = get_message('state_reset', user_language)
        await update.message.reply_text(
            reset_text,
            reply_markup=get_main_menu_markup(user_id)
        )
    
    async def get_my_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать user_id пользователя (временная команда для настройки админа)."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        username = update.effective_user.username or get_message('not_specified', user_language)
        first_name = update.effective_user.first_name or get_message('not_specified', user_language)
        last_name = update.effective_user.last_name or ""
        
        full_name = f"{first_name} {last_name}".strip()
        
        id_text = get_message('user_id_info', user_language, 
                            user_id=user_id, username=username, full_name=full_name)
        
        await update.message.reply_text(id_text, parse_mode='Markdown')

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        text = update.message.text.strip()
        
        # Проверяем доступ пользователя перед обработкой любых сообщений
        if not self.db.check_user_access(user_id, update.effective_user.username):
            await update.message.reply_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=update.effective_user.username or 'не указан')
            )
            return

        # Проверяем, является ли это командой (начинается с /)
        if text.startswith('/'):
            # Список разрешенных команд для учеников
            allowed_student_commands = ['/start', '/reset', '/stop', '/help', '/myid']
            
            # Если пользователь не админ и команда не разрешена
            if not self.db.is_admin(user_id) and text not in allowed_student_commands:
                # Удаляем сообщение с неразрешенной командой
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Отправляем предупреждение и удаляем его через 3 секунды
                warning_text = (
                    "⚠️ Команда недоступна для учеников.\n\n"
                    "🔹 Доступные команды:\n"
                    "• /start - Главное меню\n"
                    "• /reset - Сбросить состояние\n"
                    "• /stop - Остановить бота\n"
                    "• /help - Помощь"
                )
                
                if user_language == 'kk':
                    warning_text = (
                        "⚠️ Команда оқушыларға қолжетімсіз.\n\n"
                        "🔹 Қолжетімді командалар:\n"
                        "• /start - Басты мәзір\n"
                        "• /reset - Күйді тастау\n"
                        "• /stop - Ботты тоқтату\n"
                        "• /help - Көмек"
                    )
                
                warning_msg = await update.message.reply_text(warning_text)
                
                # Асинхронно удаляем предупреждение через 5 секунды
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    warning_msg.chat_id, 
                    warning_msg.message_id, 
                    5
                ))
                return

        # Проверяем, находится ли пользователь в активном тесте
        if self.db.is_user_active(user_id):
            # Пользователь в активном тесте, даем инструкции
            test_instruction = get_message('in_active_test_help', user_language)
            
            # Удаляем сообщение пользователя
            try:
                await update.message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления
            
            # Отправляем инструкцию и удаляем её через 5 секунды (чуть дольше, так как текст больше)
            instruction_msg = await update.message.reply_text(test_instruction)
            
            # Асинхронно удаляем сообщение через 5 секунды
            asyncio.create_task(self._delete_message_after_delay(
                context.bot, 
                instruction_msg.chat_id, 
                instruction_msg.message_id, 
                5
            ))
            return

        # Handle language change confirmation
        if context.user_data.get('awaiting_language_confirmation'):
            if text.lower() in ['да', 'yes', 'ия', 'иә']:
                new_language = context.user_data.get('new_language', 'ru')
                
                # Clear user data when changing language
                self.db.clear_user_data_on_language_change(user_id)
                
                # Update user language
                self.db.update_user_language(user_id, new_language)
                
                # Clear context
                context.user_data.clear()
                
                success_text = "✅ Язык изменен на русский. Все данные очищены." if new_language == 'ru' else "✅ Тіл қазақшаға өзгертілді. Барлық деректер тазаланды."
                await update.message.reply_text(
                    success_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
                return
            else:
                # Cancel language change
                context.user_data.clear()
                cancel_text = "❌ Смена языка отменена." if user_language == 'ru' else "❌ Тіл ауыстыру болдырылмады."
                await update.message.reply_text(
                    cancel_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
                return

        # Handle full name input
        if context.user_data.get('awaiting_full_name'):
            if len(text) >= 2:
                context.user_data['full_name'] = text
                context.user_data['awaiting_full_name'] = False
                context.user_data['awaiting_grade'] = True
                grade_request = "Пожалуйста, введите ваш класс (5, 6 или 7):" if user_language == 'ru' else "Сыныбыңызды енгізіңіз (5, 6 немесе 7):"
                await update.message.reply_text(grade_request)
                return
            else:
                fullname_error_text = "❌ ФИО должно содержать минимум 2 символа. Попробуйте еще раз:" if user_language == 'ru' else "❌ Толық аты кемінде 2 таңбадан тұруы керек. Қайталап көріңіз:"
                await update.message.reply_text(fullname_error_text)
                return

        # Handle grade input
        if context.user_data.get('awaiting_grade'):
            try:
                grade = int(text)
                if grade in [5, 6, 7]:
                    full_name = context.user_data.get('full_name', '')
                    self.db.update_user_info(user_id, full_name, grade)
                    context.user_data.clear()
                    grade_success_text = f"✅ Данные сохранены!\n\n👤 ФИО: {full_name}\n🎓 Класс: {grade}\n\n📚 Теперь вы можете пользоваться ботом!" if user_language == 'ru' else f"✅ Деректер сақталды!\n\n👤 Толық аты: {full_name}\n🎓 Сынып: {grade}\n\n📚 Енді ботты пайдалана аласыз!"
                    await update.message.reply_text(
                        grade_success_text,
                        reply_markup=get_main_menu_markup(user_id)
                    )
                    return
                else:
                    grade_error_text = "❌ Пожалуйста, введите класс: 5, 6 или 7" if user_language == 'ru' else "❌ Сыныпты енгізіңіз: 5, 6 немесе 7"
                    await update.message.reply_text(grade_error_text)
                    return
            except ValueError:
                grade_format_error = "❌ Пожалуйста, введите число (5, 6 или 7)" if user_language == 'ru' else "❌ Санды енгізіңіз (5, 6 немесе 7)"
                await update.message.reply_text(grade_format_error)
                return

        # Handle admin full name input
        if context.user_data.get('awaiting_admin_full_name'):
            if len(text) >= 2:
                self.db.update_admin_info(user_id, text)
                context.user_data.clear()
                admin_success_text = f"✅ Добро пожаловать, {text}!\n\n🔧 Вы вошли как <b>администратор</b>.\n\nВыберите действие:" if user_language == 'ru' else f"✅ Қош келдіңіз, {text}!\n\n🔧 Сіз <b>әкімші</b> ретінде кірдіңіз.\n\nӘрекетті таңдаңыз:"
                await update.message.reply_html(
                    admin_success_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
                return
            else:
                admin_fullname_error = "❌ ФИО должно содержать минимум 2 символа. Попробуйте еще раз:" if user_language == 'ru' else "❌ Толық аты кемінде 2 таңбадан тұруы керек. Қайталап көріңіз:"
                await update.message.reply_text(admin_fullname_error)
                return

        # Handle main menu buttons
        select_topic_text_ru = "📚 Выбрать тему и начать"
        select_topic_text_kk = "📚 Тақырыпты таңдап, бастау"
        random_test_text_ru = "🎯 Начать рандомный тест"
        random_test_text_kk = "🎯 Кездейсоқ тестті бастау"
        my_progress_text_ru = "📊 Мой прогресс"
        my_progress_text_kk = "📊 Менің прогресім"
        help_text_ru = "❓ Помощь"
        help_text_kk = "❓ Көмек"
        admin_panel_text_ru = "🔧 Админ-панель"
        admin_panel_text_kk = "🔧 Әкімші панелі"
        
        if text in [select_topic_text_ru, select_topic_text_kk]:
            # Проверяем, не находится ли пользователь уже в активном тесте или в процессе выбора темы
            if self.db.is_user_active(user_id):
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Показываем инструкцию и удаляем через 4 секунды
                instruction_text = get_message('in_active_test_help', user_language)
                instruction_msg = await update.message.reply_text(instruction_text)
                
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    4
                ))
                return
            elif context.user_data.get('in_topic_selection'):
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Показываем инструкцию и удаляем через 6 секунд
                instruction_text = get_message('in_topic_selection_help', user_language)
                instruction_msg = await update.message.reply_text(instruction_text)
                
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    6
                ))
                return
            
            await self.handle_topic_selection(update, context)
        elif text in [random_test_text_ru, random_test_text_kk]:
            # Проверяем состояние пользователя
            if self.db.is_user_active(user_id) or context.user_data.get('in_topic_selection'):
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Определяем тип инструкции
                if self.db.is_user_active(user_id):
                    instruction_text = get_message('in_active_test_help', user_language)
                    delay = 4
                else:
                    instruction_text = get_message('in_topic_selection_help', user_language)
                    delay = 6
                
                instruction_msg = await update.message.reply_text(instruction_text)
                
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    delay
                ))
                return
            
            await self.handle_random_test(update, context)
        elif text in [my_progress_text_ru, my_progress_text_kk]:
            # Проверяем состояние пользователя
            if self.db.is_user_active(user_id) or context.user_data.get('in_topic_selection'):
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Определяем тип инструкции
                if self.db.is_user_active(user_id):
                    instruction_text = get_message('in_active_test_help', user_language)
                    delay = 4
                else:
                    instruction_text = get_message('in_topic_selection_help', user_language)
                    delay = 6
                
                instruction_msg = await update.message.reply_text(instruction_text)
                
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    delay
                ))
                return
            
            await self.handle_progress(update, context)
        elif text in [help_text_ru, help_text_kk]:
            # Проверяем состояние пользователя
            if self.db.is_user_active(user_id) or context.user_data.get('in_topic_selection'):
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass
                
                # Определяем тип инструкции
                if self.db.is_user_active(user_id):
                    instruction_text = get_message('in_active_test_help', user_language)
                    delay = 4
                else:
                    instruction_text = get_message('in_topic_selection_help', user_language)
                    delay = 6
                
                instruction_msg = await update.message.reply_text(instruction_text)
                
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    delay
                ))
                return
            
            await self.handle_help(update, context)
        elif text in [admin_panel_text_ru, admin_panel_text_kk]:
            # Проверяем, является ли пользователь админом
            if self.db.is_admin(user_id):
                # Проверяем состояние пользователя (админы тоже не должны иметь доступ во время теста/выбора)
                if self.db.is_user_active(user_id) or context.user_data.get('in_topic_selection'):
                    # Удаляем сообщение пользователя
                    try:
                        await update.message.delete()
                    except Exception:
                        pass
                    
                    # Определяем тип инструкции
                    if self.db.is_user_active(user_id):
                        instruction_text = get_message('in_active_test_help', user_language)
                        delay = 4
                    else:
                        instruction_text = get_message('in_topic_selection_help', user_language)
                        delay = 6
                    
                    instruction_msg = await update.message.reply_text(instruction_text)
                    
                    asyncio.create_task(self._delete_message_after_delay(
                        context.bot, 
                        instruction_msg.chat_id, 
                        instruction_msg.message_id, 
                        delay
                    ))
                    return
                
                # Импортируем админ-хендлеры
                from src.handlers.admin import AdminBaseHandler
                from src.services.question_service import QuestionService
                from src.services.ai_service import AIService
                
                ai_service = AIService()
                admin_handlers = AdminBaseHandler()
                await admin_handlers.admin_panel(update, context)
            else:
                no_admin_text = "❌ У вас нет прав администратора." if user_language == 'ru' else "❌ Сізде әкімші құқығы жоқ."
                await update.message.reply_text(no_admin_text, reply_markup=get_main_menu_markup(user_id))
        elif text in ["🇷🇺 Русский", "🇰🇿 Қазақша"]:
            await self.handle_language_change(update, context, text)
        else:
            # Проверяем, находится ли пользователь в процессе выбора темы
            if context.user_data.get('in_topic_selection'):
                # Пользователь в процессе выбора темы, даем понятные инструкции
                instruction_text = get_message('in_topic_selection_help', user_language)
                
                # Удаляем сообщение пользователя
                try:
                    await update.message.delete()
                except Exception:
                    pass  # Игнорируем ошибки удаления
                
                # Отправляем инструкцию и удаляем её через 6 секунд
                instruction_msg = await update.message.reply_text(instruction_text)
                
                # Асинхронно удаляем сообщение через 6 секунд
                asyncio.create_task(self._delete_message_after_delay(
                    context.bot, 
                    instruction_msg.chat_id, 
                    instruction_msg.message_id, 
                    6
                ))
                
            else:
                # Unknown command - обычное сообщение без автоудаления
                unknown_text = get_message('topic_not_selected', user_language)
                
                # НЕ удаляем сообщение пользователя в обычном режиме
                # Просто отвечаем обычным сообщением с клавиатурой
                await update.message.reply_text(
                    unknown_text,
                    reply_markup=get_main_menu_markup(user_id)
                )

    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language_text: str) -> None:
        """Handle language change request."""
        user_id = update.effective_user.id
        current_language = self.db.get_user_language(user_id)
        
        # Determine new language
        new_language = 'ru' if language_text == "🇷🇺 Русский" else 'kk'
        
        if current_language == new_language:
            # Same language selected
            same_lang_text = "Вы уже используете русский язык." if new_language == 'ru' else "Сіз қазірдің өзінде қазақ тілін пайдаланып жатырсыз."
            await update.message.reply_text(
                same_lang_text,
                reply_markup=get_main_menu_markup(user_id)
            )
            return
        
        # Show warning and ask for confirmation
        warning_text = get_language_change_warning(current_language)
        context.user_data['awaiting_language_confirmation'] = True
        context.user_data['new_language'] = new_language
        
        confirm_text = "\n\nОтветьте 'да' для подтверждения или любое другое сообщение для отмены." if current_language == 'ru' else "\n\nРастау үшін 'иә' деп жауап беріңіз немесе болдырмау үшін басқа хабарлама жіберіңіз."
        await update.message.reply_text(warning_text + confirm_text)

    async def _delete_previous_bot_message(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Удаляет предыдущее сообщение бота, если оно сохранено в контексте."""
        try:
            last_bot_message_id = context.user_data.get('last_bot_message_id')
            chat_id = context.user_data.get('chat_id')
            
            if last_bot_message_id and chat_id:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_bot_message_id)
                # Очищаем сохраненный ID после удаления
                context.user_data.pop('last_bot_message_id', None)
        except Exception as e:
            # Игнорируем ошибки удаления (сообщение могло быть уже удалено)
            logging.debug(f"Could not delete previous bot message: {e}")

    async def _save_bot_message_id(self, context: ContextTypes.DEFAULT_TYPE, message, chat_id: int) -> None:
        """Сохраняет ID сообщения бота для последующего удаления."""
        context.user_data['last_bot_message_id'] = message.message_id
        context.user_data['chat_id'] = chat_id

    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
        
        # Удаляем предыдущее сообщение бота ТОЛЬКО если пользователь НЕ в активном тесте
        if not self.db.is_user_active(user_id):
            await self._delete_previous_bot_message(context)
        
        # Clear any previous data
        self.clear_user_data(context)
        # Set flag that user is in topic selection
        context.user_data['in_topic_selection'] = True
        
        # Удаляем сообщение пользователя (кнопку "Выбрать тему")
        try:
            await update.message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        # Отправляем новое сообщение с выбором тем
        new_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=get_message('select_topic', user_language),
            reply_markup=build_topic_selection_keyboard(user_id),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID нового сообщения бота
        await self._save_bot_message_id(context, new_message, update.effective_chat.id)

    async def handle_progress(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle progress request from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Get user's test results
        results = self.db.get_user_test_results(user_id)
        
        if not results:
            await update.message.reply_text(
                get_message('no_test_results', user_language),
                reply_markup=get_main_menu_markup(user_id)
            )
            return
        
        # Format results
        progress_text = get_message('progress_title', user_language)
        
        for result in results[-10:]:  # Show last 10 results
            topic = result['topic']
            percentage = result['percentage']
            completed_at = result['completed_at']
            # Форматируем дату для отображения
            if completed_at:
                if hasattr(completed_at, 'strftime'):
                    date_str = completed_at.strftime('%d.%m.%Y')
                else:
                    date_str = str(completed_at)[:10]  # Берем первые 10 символов (дата)
            else:
                date_str = "Неизвестно"
            progress_text += f"📝 {topic}: {percentage:.1f}% ({date_str})\n"
        
        await update.message.reply_text(
            progress_text,
            reply_markup=get_main_menu_markup(user_id)
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle help request from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        await update.message.reply_text(
            get_message('help_text', user_language),
            reply_markup=get_main_menu_markup(user_id),
            parse_mode='Markdown'
        )

    async def handle_random_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle random test request from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
        
        # Удаляем предыдущее сообщение бота (если есть)
        await self._delete_previous_bot_message(context)
        
        # Clear any previous data
        self.clear_user_data(context)
        
        # Удаляем сообщение пользователя (кнопку "Начать рандомный тест")
        try:
            await update.message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        # Show preparing message
        preparing_text = get_message('preparing_random_test', user_language)
        preparing_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=preparing_text
        )
        
        # Generate random test using RandomTestService
        random_test_service = RandomTestService()
        questions_data = random_test_service.generate_random_test(user_id, 10)
        
        if not questions_data:
            error_text = get_message('random_test_error', user_language)
            # Удаляем preparing_msg и отправляем новое с клавиатурой
            try:
                await preparing_msg.delete()
            except:
                pass
            error_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_text,
                reply_markup=get_main_menu_markup(user_id)
            )
            # Сохраняем ID сообщения с ошибкой
            await self._save_bot_message_id(context, error_msg, update.effective_chat.id)
            return
        
        # Convert questions data to the format expected by the test system
        questions = []
        for q_data in questions_data:
            # Формируем список вариантов ответов как в QuestionService
            options = [q_data.get('answer', '')]  # Сначала правильный ответ
            
            # Добавляем неправильные варианты
            incorrect_options = q_data.get('incorrect_options', '')
            if incorrect_options:
                if isinstance(incorrect_options, str):
                    incorrect_opts = [opt.strip() for opt in incorrect_options.split('\n') if opt.strip()]
                    options.extend(incorrect_opts)
            
            # Убеждаемся, что есть минимум 2 варианта
            if len(options) < 2:
                default_option = "Вариант" if user_language == 'ru' else "Нұсқа"
                options.extend([f"{default_option} {i}" for i in range(len(options), 4)])
            
            # Перемешиваем варианты
            random.shuffle(options)
            
            # Format: (question_text, correct_answer, explanation, options_list, source, image_path, question_id)
            question_tuple = (
                q_data.get('question', ''),  # 0 - question_text
                q_data.get('answer', ''),    # 1 - correct_answer  
                q_data.get('explanation', ''),  # 2 - explanation (ИСПРАВЛЕНО!)
                options,  # 3 - options_list
                'random_test',  # 4 - source
                q_data.get('image_path', None),  # 5 - image_path
                q_data.get('id')  # 6 - question_id
            )
            questions.append(question_tuple)
        
        # Set user as active for random test
        random_test_topic_name = get_message('random_test_topic_name', user_language)
        self.db.set_user_active(user_id, random_test_topic_name)
        self.set_user_data(context, 'current_topic', random_test_topic_name)
        self.set_user_data(context, 'current_question_index', 0)
        self.set_user_data(context, 'questions', questions)
        self.set_user_data(context, 'answers', [q[1] for q in questions])
        self.set_user_data(context, 'is_random_test', True)
        
        # Display first question
        if questions:
            question = questions[0]
            keyboard = build_question_keyboard(question[3], 0, 0, len(questions), user_id, is_random_test=True)
            
            try:
                # If question has an image, send it first
                if len(question) > 5 and question[5]:  # question[5] is image_path
                    question_msg = await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=open(question[5], 'rb'),
                        caption=get_message('random_test_question', user_language, 
                                          current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    # Delete preparing message
                    try:
                        await preparing_msg.delete()
                    except:
                        pass
                    # Сохраняем ID сообщения с вопросом
                    await self._save_bot_message_id(context, question_msg, update.effective_chat.id)
                else:
                    await preparing_msg.edit_text(
                        get_message('random_test_question', user_language, 
                                  current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    # Сохраняем ID отредактированного сообщения
                    await self._save_bot_message_id(context, preparing_msg, update.effective_chat.id)
            except Exception as e:
                logging.error(f"Error displaying random test question: {e}")
                error_text = get_message('question_display_error', user_language)
                # Удаляем preparing_msg и отправляем новое с клавиатурой
                try:
                    await preparing_msg.delete()
                except:
                    pass
                error_msg = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
                # Сохраняем ID сообщения с ошибкой
                await self._save_bot_message_id(context, error_msg, update.effective_chat.id)
        else:
            error_text = get_message('questions_load_error', user_language)
            # Удаляем preparing_msg и отправляем новое с клавиатурой
            try:
                await preparing_msg.delete()
            except:
                pass
            error_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_text,
                reply_markup=get_main_menu_markup(user_id)
            )
            # Сохраняем ID сообщения с ошибкой
            await self._save_bot_message_id(context, error_msg, update.effective_chat.id)

    async def _delete_message_after_delay(self, bot, chat_id: int, message_id: int, delay_seconds: int) -> None:
        """Удаляет сообщение через указанное количество секунд."""
        try:
            await asyncio.sleep(delay_seconds)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            # Игнорируем ошибки удаления (сообщение могло быть уже удалено)
            logging.debug(f"Could not delete message {message_id} in chat {chat_id}: {e}") 

    async def language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show language selection menu."""
        user_id = update.effective_user.id
        current_language = self.db.get_user_language(user_id)
        
        current_lang_name = "Русский" if current_language == 'ru' else "Қазақша"
        
        text = f"🌐 **Выбор языка / Тіл таңдау**\n\n"
        text += f"Текущий язык / Ағымдағы тіл: {current_lang_name}\n\n"
        text += f"Выберите язык / Тілді таңдаңыз:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="change_lang_ru")],
            [InlineKeyboardButton("🇰🇿 Қазақша", callback_data="change_lang_kk")],
            [InlineKeyboardButton("🔙 Назад / Артқа", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_language_change_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle language change from inline keyboard."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = query.from_user.id
        current_language = self.db.get_user_language(user_id)
        
        # Extract new language from callback data
        new_language = query.data.split('_')[-1]  # ru or kk
        
        if current_language == new_language:
            # Same language selected
            same_lang_text = "Вы уже используете русский язык." if new_language == 'ru' else "Сіз қазірдің өзінде қазақ тілін пайдаланып жатырсыз."
            await query.edit_message_text(
                same_lang_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
            )
            return
        
        # Show warning and confirmation buttons
        warning_text = get_language_change_warning(current_language)
        
        keyboard = [
            [InlineKeyboardButton("✅ Да / Иә", callback_data=f"confirm_lang_{new_language}")],
            [InlineKeyboardButton("❌ Отмена / Болдырмау", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(warning_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_language_change_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Confirm and execute language change."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = query.from_user.id
        new_language = query.data.split('_')[-1]  # ru or kk
        
        # Clear user data when changing language
        self.db.clear_user_data_on_language_change(user_id)
        
        # Update user language
        self.db.update_user_language(user_id, new_language)
        
        # Clear context
        context.user_data.clear()
        
        success_text = "✅ Язык изменен на русский. Все данные очищены." if new_language == 'ru' else "✅ Тіл қазақшаға өзгертілді. Барлық деректер тазаланды."
        
        await query.edit_message_text(
            success_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню / Басты мәзір", callback_data="main_menu")]])
        ) 