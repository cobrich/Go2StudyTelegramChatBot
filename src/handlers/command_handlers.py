from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging
from handlers.base_handler import BaseHandler
from utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard
from utils.translations import get_message, get_language_change_warning
from config.constants import HELP_TEXT, TOPICS
from services.random_test_service import RandomTestService
import sqlite3

class CommandHandlers(BaseHandler):
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_language = self.db.get_user_language(user.id)

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
            setup_result = self.db.auto_setup_user_from_whitelist(user.id, user.username)
            
            if setup_result['success'] and setup_result['auto_configured']:
                # Показываем сообщение об автоматической настройке
                auto_setup_message = f"✅ <b>Добро пожаловать!</b>\n\n"
                auto_setup_message += f"🔄 {setup_result['message']}\n\n"
                
                user_data = setup_result['user_data']
                if user_data['full_name']:
                    auto_setup_message += f"👤 <b>ФИО:</b> {user_data['full_name']}\n"
                if user_data['grade']:
                    auto_setup_message += f"🎓 <b>Класс:</b> {user_data['grade']}\n"
                if user_data['phone_number']:
                    auto_setup_message += f"📱 <b>Телефон:</b> {user_data['phone_number']}\n"
                
                auto_setup_message += f"\n📚 Теперь вы можете пользоваться ботом!"
                
                await update.message.reply_html(auto_setup_message)
            
            # Получаем информацию о пользователе после настройки
            user_info = self.db.get_user_info(user.id)
            
            # Проверяем номер телефона
            phone_number = self.db.get_user_phone(user.id)
            if not phone_number:
                # Если номер телефона не указан, предлагаем его ввести
                context.user_data['awaiting_phone_number'] = True
                phone_request_text = "📱 Для лучшей связи, пожалуйста, введите ваш номер телефона (например: +77771234567).\n\nИли нажмите /skip чтобы пропустить этот шаг." if user_language == 'ru' else "📱 Жақсы байланыс үшін телефон нөіріңізді енгізіңіз (мысалы: +77771234567).\n\nНемесе бұл қадамды өткізу үшін /skip басыңыз."
                await update.message.reply_text(phone_request_text)
                return
            
            # Для обычных пользователей - проверяем ФИО и класс (на случай если автонастройка не сработала)
            if not user_info or not user_info[0]:  # Нет ФИО
                context.user_data['awaiting_full_name'] = True
                fullname_request = "Пожалуйста, введите ваше ФИО:" if user_language == 'ru' else "Толық атыңызды енгізіңіз:"
                await update.message.reply_text(fullname_request)
                return
            elif not user_info[1]:  # Нет класса
                context.user_data['awaiting_grade'] = True
                context.user_data['full_name'] = user_info[0]
                grade_request = "Пожалуйста, введите ваш класс (4, 5 или 6):" if user_language == 'ru' else "Сыныбыңызды енгізіңіз (4, 5 немесе 6):"
                await update.message.reply_text(grade_request)
                return
            
            # Если все данные есть - показываем приветствие
            welcome_name = user_info[0] if user_info and user_info[0] else user.first_name or "пользователь"
            grade_text = f", {user_info[1]} класс" if user_info and user_info[1] else ""
            if user_language == 'kk':
                grade_text = f", {user_info[1]} сынып" if user_info and user_info[1] else ""
                welcome_text = get_message('welcome', user_language, name=welcome_name, grade=user_info[1] if user_info and user_info[1] else '') + "\n\n" + get_message('bot_description', user_language)
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

        self.db.set_all_users_inactive()

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
                error_text = "Произошла ошибка при загрузке меню. Пожалуйста, попробуйте еще раз немного позже или введите /start снова." if user_language == 'ru' else "Мәзірді жүктеуде қате орын алды. Сәл кейін қайталап көріңіз немесе /start енгізіңіз."
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
        
        stop_text = "🛑 Бот остановлен. Все данные очищены.\n\nДля нового старта используйте /start" if user_language == 'ru' else "🛑 Бот тоқтатылды. Барлық деректер тазаланды.\n\nЖаңа бастау үшін /start пайдаланыңыз"
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
        
        # Clear user activity
        self.db.set_user_inactive(user_id)
        
        # Clear context data
        context.user_data.clear()
        
        reset_text = "🔄 Состояние сброшено. Можете начать заново." if user_language == 'ru' else "🔄 Күй қалпына келтірілді. Қайта бастай аласыз."
        await update.message.reply_text(
            reset_text,
            reply_markup=get_main_menu_markup(user_id)
        )
    
    async def get_my_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать user_id пользователя (временная команда для настройки админа)."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        username = update.effective_user.username or "не указан"
        first_name = update.effective_user.first_name or "не указано"
        last_name = update.effective_user.last_name or ""
        
        full_name = f"{first_name} {last_name}".strip()
        
        if user_language == 'kk':
            id_text = f"🆔 **Сіздің деректеріңіз:**\n\n**User ID:** `{user_id}`\n**Username:** @{username}\n**Аты:** {full_name}\n\nӘкімші ретінде қосу үшін User ID `{user_id}` пайдаланыңыз."
        else:
            id_text = f"🆔 **Ваши данные:**\n\n**User ID:** `{user_id}`\n**Username:** @{username}\n**Имя:** {full_name}\n\nИспользуйте User ID `{user_id}` для добавления в качестве админа."
        
        await update.message.reply_text(id_text, parse_mode='Markdown')

    async def skip_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Пропустить ввод номера телефона."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        if context.user_data.get('awaiting_phone_number'):
            context.user_data['awaiting_phone_number'] = False
            skip_text = "✅ Ввод номера телефона пропущен.\n\n📚 Теперь вы можете пользоваться ботом!" if user_language == 'ru' else "✅ Телефон нөмірін енгізу өткізілді.\n\n📚 Енді ботты пайдалана аласыз!"
            await update.message.reply_text(
                skip_text,
                reply_markup=get_main_menu_markup(user_id)
            )
        else:
            skip_error_text = "Эта команда используется только при запросе номера телефона." if user_language == 'ru' else "Бұл команда тек телефон нөмірі сұралған кезде пайдаланылады."
            await update.message.reply_text(
                skip_error_text,
                reply_markup=get_main_menu_markup(user_id)
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Проверяем доступ пользователя перед обработкой любых сообщений
        if not self.db.check_user_access(user_id, update.effective_user.username):
            await update.message.reply_text(
                get_message('no_access', user_language, 
                          user_id=user_id, 
                          username=update.effective_user.username or 'не указан')
            )
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

        # Handle phone number input
        if context.user_data.get('awaiting_phone_number'):
            if self._is_valid_phone(text):
                self.db.update_user_phone(user_id, text)
                context.user_data['awaiting_phone_number'] = False
                phone_success_text = f"✅ Номер телефона {text} сохранен!\n\n📚 Теперь вы можете пользоваться ботом!" if user_language == 'ru' else f"✅ {text} телефон нөмірі сақталды!\n\n📚 Енді ботты пайдалана аласыз!"
                await update.message.reply_text(
                    phone_success_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
                return
            else:
                phone_error_text = "❌ Неверный формат номера телефона. Пожалуйста, введите номер в формате +77771234567 или 87771234567" if user_language == 'ru' else "❌ Телефон нөмірінің форматы дұрыс емес. +77771234567 немесе 87771234567 форматында енгізіңіз"
                await update.message.reply_text(phone_error_text)
                return

        # Handle full name input
        if context.user_data.get('awaiting_full_name'):
            if len(text) >= 2:
                context.user_data['full_name'] = text
                context.user_data['awaiting_full_name'] = False
                context.user_data['awaiting_grade'] = True
                grade_request = "Пожалуйста, введите ваш класс (4, 5 или 6):" if user_language == 'ru' else "Сыныбыңызды енгізіңіз (4, 5 немесе 6):"
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
                if grade in [4, 5, 6]:
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
                    grade_error_text = "❌ Пожалуйста, введите класс: 4, 5 или 6" if user_language == 'ru' else "❌ Сыныпты енгізіңіз: 4, 5 немесе 6"
                    await update.message.reply_text(grade_error_text)
                    return
            except ValueError:
                grade_format_error = "❌ Пожалуйста, введите число (4, 5 или 6)" if user_language == 'ru' else "❌ Санды енгізіңіз (4, 5 немесе 6)"
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
        my_progress_text_ru = "📊 Мой прогресс"
        my_progress_text_kk = "📊 Менің прогресім"
        help_text_ru = "❓ Помощь"
        help_text_kk = "❓ Көмек"
        
        if text in [select_topic_text_ru, select_topic_text_kk]:
            await self.handle_topic_selection(update, context)
        elif text in [my_progress_text_ru, my_progress_text_kk]:
            await self.handle_progress(update, context)
        elif text in [help_text_ru, help_text_kk]:
            await self.handle_help(update, context)
        elif text in ["🇷🇺 Русский", "🇰🇿 Қазақша"]:
            await self.handle_language_change(update, context, text)
        else:
            # Unknown command
            unknown_text = get_message('topic_not_selected', user_language)
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

    async def handle_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle topic selection from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
        
        # Clear any previous data
        self.clear_user_data(context)
        # Set flag that user is in topic selection
        context.user_data['in_topic_selection'] = True
        
        await update.message.reply_text(
            get_message('select_topic', user_language),
            reply_markup=build_topic_selection_keyboard(user_id),
            parse_mode='Markdown'
        )

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
            date = result['date']
            progress_text += f"📝 {topic}: {percentage:.1f}% ({date})\n"
        
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

    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        # Check if it starts with valid prefixes and has correct length
        if len(digits_only) == 11:
            return digits_only.startswith('7') or digits_only.startswith('8')
        elif len(digits_only) == 10:
            return True
        
        return False 