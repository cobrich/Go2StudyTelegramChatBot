from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging
from handlers.base_handler import BaseHandler
from utils.keyboards import get_main_menu_markup, build_topic_selection_keyboard
from utils.translations import get_message, get_language_change_warning
from config.constants import HELP_TEXT, TOPICS
from services.random_test_service import RandomTestService
import sqlite3
import random

class CommandHandlers(BaseHandler):
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_language = self.db.get_user_language(user.id)

        # Автоматически обновляем username если он есть
        if user.username:
            self.db.auto_update_username_from_telegram(user.id, user.username)

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
                
                auto_setup_message += f"\n📚 Теперь вы можете пользоваться ботом!"
                
                await update.message.reply_html(auto_setup_message)
            
            # Получаем информацию о пользователе после настройки
            user_info = self.db.get_user_info(user.id)
            
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
        random_test_text_ru = "🎯 Начать рандомный тест"
        random_test_text_kk = "🎯 Кездейсоқ тестті бастау"
        my_progress_text_ru = "📊 Мой прогресс"
        my_progress_text_kk = "📊 Менің прогресім"
        help_text_ru = "❓ Помощь"
        help_text_kk = "❓ Көмек"
        
        if text in [select_topic_text_ru, select_topic_text_kk]:
            await self.handle_topic_selection(update, context)
        elif text in [random_test_text_ru, random_test_text_kk]:
            await self.handle_random_test(update, context)
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

    async def handle_random_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle random test request from main menu."""
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Check if user is already taking a test
        if await self.check_user_active(update, context):
            return
        
        # Clear any previous data
        self.clear_user_data(context)
        
        # Show preparing message
        preparing_text = "🎯 Подготавливаю случайный тест из 10 вопросов..." if user_language == 'ru' else "🎯 10 сұрақтан тұратын кездейсоқ тестті дайындап жатырмын..."
        preparing_msg = await update.message.reply_text(preparing_text)
        
        # Generate random test using RandomTestService
        random_test_service = RandomTestService(self.db)
        questions_data = random_test_service.generate_random_test(user_id, 10)
        
        if not questions_data:
            error_text = "❌ Не удалось создать случайный тест. Попробуйте позже." if user_language == 'ru' else "❌ Кездейсоқ тест жасау мүмкін болмады. Кейінірек қайталап көріңіз."
            await preparing_msg.edit_text(
                error_text,
                reply_markup=get_main_menu_markup(user_id)
            )
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
                    incorrect_opts = [opt.strip() for opt in incorrect_options.split('|') if opt.strip()]
                    options.extend(incorrect_opts)
            
            # Убеждаемся, что есть минимум 2 варианта
            if len(options) < 2:
                options.extend([f"Вариант {i}" for i in range(len(options), 4)])
            
            # Перемешиваем варианты
            random.shuffle(options)
            
            # Format: (question_text, correct_answer, options, options_list, source, image_path)
            question_tuple = (
                q_data.get('question', ''),  # Исправлено: 'question' вместо 'question_text'
                q_data.get('answer', ''),    # Исправлено: 'answer' вместо 'correct_answer'
                q_data.get('incorrect_options', ''),  # Исправлено: 'incorrect_options' вместо 'options'
                options,  # Правильно сформированный список вариантов
                'random_test',  # source
                q_data.get('image_path', None)
            )
            questions.append(question_tuple)
        
        # Set user as active for random test
        random_test_topic_name = "Случайный тест" if user_language == 'ru' else "Кездейсоқ тест"
        self.db.set_user_active(user_id, random_test_topic_name)
        self.set_user_data(context, 'current_topic', random_test_topic_name)
        self.set_user_data(context, 'current_question_index', 0)
        self.set_user_data(context, 'questions', questions)
        self.set_user_data(context, 'answers', [q[1] for q in questions])
        self.set_user_data(context, 'is_random_test', True)
        
        # Display first question
        if questions:
            from utils.keyboards import build_question_keyboard
            
            question = questions[0]
            keyboard = build_question_keyboard(question[3], 0, 0, len(questions), user_id)
            
            try:
                # If question has an image, send it first
                if len(question) > 5 and question[5]:  # question[5] is image_path
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=open(question[5], 'rb'),
                        caption=get_message('random_test_question', user_language, 
                                          current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard
                    )
                    # Delete preparing message
                    try:
                        await preparing_msg.delete()
                    except:
                        pass
                else:
                    await preparing_msg.edit_text(
                        get_message('random_test_question', user_language, 
                                  current=1, total=len(questions), question=question[0]),
                        reply_markup=keyboard
                    )
            except Exception as e:
                logging.error(f"Error displaying random test question: {e}")
                error_text = "❌ Ошибка при отображении вопроса." if user_language == 'ru' else "❌ Сұрақты көрсетуде қате."
                await preparing_msg.edit_text(
                    error_text,
                    reply_markup=get_main_menu_markup(user_id)
                )
        else:
            error_text = "❌ Не удалось загрузить вопросы для теста." if user_language == 'ru' else "❌ Тест үшін сұрақтарды жүктеу мүмкін болмады."
            await preparing_msg.edit_text(
                error_text,
                reply_markup=get_main_menu_markup(user_id)
            ) 