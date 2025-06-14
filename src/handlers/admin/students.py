"""
Модуль для управления учениками в админ-панели.
Включает добавление, редактирование, удаление учеников и выбор языка.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging

class StudentsHandler(AdminBaseHandler):
    """Обработчик для управления учениками."""

    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"👥 <b>Управление учениками</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
            [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
            [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
            [InlineKeyboardButton("✏️ Редактировать ученика", callback_data="edit_student_start")],
            [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по username."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"👤 <b>Добавление ученика</b>\n\nВведите username ученика (с @ или без):"
        
        context.user_data['admin_action'] = 'add_student'
        
        await query.edit_message_text(text, parse_mode='HTML')

    async def add_student_by_id_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по ID."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"🆔 <b>Добавление ученика по ID</b>\n\nВведите Telegram ID ученика:"
        
        context.user_data['admin_action'] = 'add_student_by_id'
        
        await query.edit_message_text(text, parse_mode='HTML')

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ ДОБАВЛЕНИЯ УЧЕНИКА ===

    async def handle_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка добавления ученика - этап 1 (username)."""
        if username.startswith('@'):
            username = username[1:]
        
        context.user_data['new_student_username'] = username
        context.user_data['admin_action'] = 'student_fullname'
        
        await update.message.reply_text(f"Введите ФИО ученика @{username}:")

    async def handle_add_student_by_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления ученика по ID - этап 1 (user_id)."""
        try:
            student_user_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text("❌ Введите корректный user_id (число). Попробуйте еще раз:")
            return
        
        # Проверяем, что этот пользователь еще не добавлен
        if self.db.check_user_access(student_user_id):
            await update.message.reply_text(f"❌ Пользователь с ID {student_user_id} уже имеет доступ к боту.")
            context.user_data.pop('admin_action', None)
            return
        
        context.user_data['new_student_user_id'] = student_user_id
        context.user_data['admin_action'] = 'student_by_id_fullname'
        
        await update.message.reply_text(f"Введите ФИО ученика с ID {student_user_id}:")

    async def handle_student_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_phone'
        
        await update.message.reply_text("📱 Введите номер телефона ученика (например: +77771234567) или напишите 'пропустить' чтобы не указывать:")

    async def handle_student_by_id_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика по ID - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_by_id_phone'
        
        await update.message.reply_text("📱 Введите номер телефона ученика (например: +77771234567) или напишите 'пропустить' чтобы не указывать:")

    async def handle_student_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка добавления ученика - этап 3 (телефон)."""
        phone_number = phone_text.strip() if phone_text.lower() != 'пропустить' else ""
        context.user_data['new_student_phone'] = phone_number
        context.user_data['admin_action'] = 'student_grade'
        
        await update.message.reply_text("🎓 Введите класс ученика (от 1 до 11):")

    async def handle_student_by_id_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка добавления ученика по ID - этап 3 (телефон)."""
        phone_number = phone_text.strip() if phone_text.lower() != 'пропустить' else ""
        context.user_data['new_student_phone'] = phone_number
        context.user_data['admin_action'] = 'student_by_id_grade'
        
        await update.message.reply_text("🎓 Введите класс ученика (от 1 до 11):")

    async def handle_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика - этап 4 (класс) - переход к выбору языка."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        # Сохраняем класс и переходим к выбору языка
        context.user_data['new_student_grade'] = grade
        context.user_data['admin_action'] = 'student_language'
        
        # Показываем выбор языка
        text = f"🌐 <b>Выбор языка для ученика</b>\n\n"
        text += f"Выберите язык интерфейса для нового ученика:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="student_lang_ru")],
            [InlineKeyboardButton("🇰🇿 Қазақша", callback_data="student_lang_kk")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_student_by_id_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика по ID - этап 4 (класс) - переход к выбору языка."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        # Сохраняем класс и переходим к выбору языка
        context.user_data['new_student_grade'] = grade
        context.user_data['admin_action'] = 'student_by_id_language'
        
        # Показываем выбор языка
        text = f"🌐 <b>Выбор языка для ученика</b>\n\n"
        text += f"Выберите язык интерфейса для нового ученика:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="student_lang_ru")],
            [InlineKeyboardButton("🇰🇿 Қазақша", callback_data="student_lang_kk")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ОБРАБОТЧИКИ CALLBACK ДЛЯ ВЫБОРА ЯЗЫКА ===

    async def handle_student_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора языка при добавлении ученика - финальный этап."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем выбранный язык из callback_data
        # Формат: student_lang_ru или student_lang_kk
        language = query.data.split('_')[-1]  # ru или kk
        
        # Получаем все сохраненные данные
        student_user_id = context.user_data.get('new_student_user_id')
        username = context.user_data.get('new_student_username')
        fullname = context.user_data.get('new_student_fullname')
        phone_number = context.user_data.get('new_student_phone', "")
        grade = context.user_data.get('new_student_grade')
        admin_id = update.effective_user.id
        
        if not all([fullname, grade]):
            await query.edit_message_text("❌ Ошибка: не все данные ученика сохранены. Попробуйте заново.")
            return
        
        # Определяем тип добавления (по username или по ID)
        if student_user_id:
            # Добавление по ID
            success = await self._add_student_by_id_with_language(
                student_user_id, fullname, grade, admin_id, phone_number, language, context
            )
        elif username:
            # Добавление по username
            success = await self._add_student_by_username_with_language(
                username, fullname, grade, admin_id, phone_number, language, context
            )
        else:
            await query.edit_message_text("❌ Ошибка: не найден ни ID, ни username ученика.")
            return
        
        if success:
            # Показываем сообщение об успехе и возвращаемся в меню управления учениками
            keyboard = [
                [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
                [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
                [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            language_name = 'Русский' if language == 'ru' else 'Қазақша'
            
            text = f"✅ Ученик успешно добавлен!\n\n"
            text += f"ФИО: {fullname}\nКласс: {grade}\n"
            text += f"🌐 Язык: {language_name}\n"
            if phone_number:
                text += f"📱 Телефон: {phone_number}\n"
            if student_user_id:
                text += f"🆔 ID: {student_user_id}\n"
            if username:
                text += f"👤 Username: @{username}\n"
            
            text += f"\n👥 <b>Управление учениками</b>\n\nВыберите действие:"
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_user_id', None)
        context.user_data.pop('new_student_username', None)
        context.user_data.pop('new_student_fullname', None)
        context.user_data.pop('new_student_phone', None)
        context.user_data.pop('new_student_grade', None)

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    async def _add_student_by_id_with_language(self, student_user_id: int, fullname: str, grade: int, 
                                             admin_id: int, phone_number: str, language: str, 
                                             context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Добавление ученика по ID с установкой языка."""
        # Пытаемся получить username пользователя через Telegram API
        username = None
        try:
            user_info = await context.bot.get_chat(student_user_id)
            if user_info and user_info.username:
                username = user_info.username
                logging.info(f"Found username @{username} for user_id {student_user_id}")
        except Exception as e:
            # Если не удалось получить через API, проверяем локальную базу
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT username FROM users WHERE user_id = ?', (student_user_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        username = result[0]
                        logging.info(f"Found username @{username} for user_id {student_user_id} in local database")
            except Exception as e2:
                logging.warning(f"Could not find username for user_id {student_user_id}: {e2}")
        
        # Добавляем ученика в базу данных
        success = self.db.add_allowed_user_by_id(student_user_id, fullname, grade, admin_id, username, phone_number)
        
        if success:
            # Устанавливаем язык пользователя
            self.db.update_user_language(student_user_id, language)
            
            # Синхронизируем данные в таблице users
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (user_id, username, full_name, grade, phone_number, language)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (student_user_id, username, fullname, grade, phone_number, language))
                    conn.commit()
                    logging.info(f"Synced user data in users table for user_id {student_user_id} with language {language}")
            except Exception as e:
                logging.error(f"Error syncing user data for user_id {student_user_id}: {e}")
        
        return success

    async def _add_student_by_username_with_language(self, username: str, fullname: str, grade: int, 
                                                   admin_id: int, phone_number: str, language: str, 
                                                   context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Добавление ученика по username с установкой языка."""
        # Получаем user_id через Telegram API
        student_user_id = None
        try:
            chat_info = await context.bot.get_chat(f"@{username}")
            if chat_info and chat_info.id:
                student_user_id = chat_info.id
                logging.info(f"Found user_id {student_user_id} for username @{username}")
        except Exception as e:
            logging.warning(f"Telegram API verification failed for @{username}: {e}")
            return False
        
        if not student_user_id:
            return False
        
        # Добавляем ученика в базу данных
        success = self.db.add_allowed_user_by_id(student_user_id, fullname, grade, admin_id, username, phone_number)
        
        if success:
            # Устанавливаем язык пользователя
            self.db.update_user_language(student_user_id, language)
            
            # Синхронизируем данные в таблице users
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (user_id, username, full_name, grade, phone_number, language)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (student_user_id, username, fullname, grade, phone_number, language))
                    conn.commit()
                    logging.info(f"Synced user data in users table for user_id {student_user_id} with language {language}")
            except Exception as e:
                logging.error(f"Error syncing user data for user_id {student_user_id}: {e}")
        
        return success

    # === МЕТОДЫ ПРОСМОТРА И УПРАВЛЕНИЯ УЧЕНИКАМИ ===

    async def list_students(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех учеников с краткой статистикой."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        students = self.db.get_all_students_summary()
        
        if not students:
            text = "📋 <b>Список учеников</b>\n\nУченики не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        else:
            text = "📋 <b>Список учеников</b>\n\n"
            keyboard = []
            
            for i, student in enumerate(students[:15], 1):  # Показываем первых 15
                status = "✅" if student['is_active'] else "❌"
                
                # Определяем идентификатор
                if student.get('username'):
                    identifier = f"@{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                else:
                    identifier = "Неизвестен"
                
                # Краткая статистика
                stats = f"Тестов: {student['total_tests']}, Балл: {student['avg_score']}%"
                if student['unique_errors'] > 0:
                    stats += f", Ошибок: {student['unique_errors']}"
                
                text += f"{i}. {status} <b>{identifier}</b>\n"
                text += f"   {student['full_name']} ({student['grade']} класс)\n"
                text += f"   {stats}\n"
                text += f"   Статус: {student['status']}\n\n"
                
                # Кнопка для детального просмотра
                if student.get('user_id'):
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {identifier} - детали", 
                        callback_data=f"student_details_{student['user_id']}"
                    )])
            
            if len(students) > 15:
                text += f"... и еще {len(students) - 15} учеников\n\n"
            
            # Кнопки управления
            keyboard.extend([
                [InlineKeyboardButton("📈 Статистика по классам", callback_data="class_statistics")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_student_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать детальную статистику ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем user_id из callback_data
        user_id = int(query.data.split('_')[-1])
        
        stats = self.db.get_student_detailed_statistics(user_id)
        
        if not stats:
            text = "❌ Ученик не найден или нет данных."
            keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="list_students")]]
        else:
            user_info = stats['user_info']
            test_stats = stats['test_statistics']
            
            text = f"📊 <b>Детальная статистика ученика</b>\n\n"
            text += f"👤 <b>Информация:</b>\n"
            text += f"• ID: {user_info['user_id']}\n"
            text += f"• Username: @{user_info['username'] or 'не указан'}\n"
            text += f"• ФИО: {user_info['full_name'] or 'не указано'}\n"
            text += f"• Класс: {user_info['grade'] or 'не указан'}\n"
            language_display = 'Русский' if user_info['language'] == 'ru' else ('Қазақша' if user_info['language'] == 'kk' else user_info['language'])
            text += f"• Язык: {language_display}\n"
            
            if user_info['last_activity']:
                text += f"• Последняя активность: {user_info['last_activity'][:16]}\n"
            if user_info['added_to_whitelist']:
                text += f"• Добавлен в whitelist: {user_info['added_to_whitelist'][:10]}\n"
            
            text += f"\n📝 <b>Статистика тестов:</b>\n"
            text += f"• Всего тестов: {test_stats['total_tests']}\n"
            text += f"• Средний балл: {test_stats['avg_score']}%\n"
            
            if test_stats['total_tests'] > 0:
                text += f"• Лучший результат: {test_stats['max_score']}%\n"
                text += f"• Худший результат: {test_stats['min_score']}%\n"
                text += f"• Первый тест: {test_stats['first_test'][:10] if test_stats['first_test'] else 'н/д'}\n"
                text += f"• Последний тест: {test_stats['last_test'][:10] if test_stats['last_test'] else 'н/д'}\n"
            
            # Показываем топ-5 тем по активности
            if stats['topic_performance']:
                text += f"\n🎯 <b>Активность по темам (топ-5):</b>\n"
                for i, topic in enumerate(stats['topic_performance'][:5], 1):
                    text += f"{i}. {topic['topic']}: {topic['tests_count']} тестов, {topic['avg_score']}%\n"
            
            # Показываем проблемные темы
            if stats['error_analysis']:
                text += f"\n❌ <b>Проблемные темы:</b>\n"
                for i, error in enumerate(stats['error_analysis'][:3], 1):
                    text += f"{i}. {error['topic']}: {error['unique_errors']} ошибок ({error['total_errors']} всего)\n"
            
            keyboard = [
                [InlineKeyboardButton("📈 Подробная статистика", callback_data=f"student_full_stats_{user_id}")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_student_{user_id}")],
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_students")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_student_full_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать полную статистику ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        stats = self.db.get_student_detailed_statistics(user_id)
        
        if not stats:
            text = "❌ Данные не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"student_details_{user_id}")]]
        else:
            user_info = stats['user_info']
            text = f"📈 <b>Полная статистика: {user_info['full_name'] or 'ID_' + str(user_id)}</b>\n\n"
            
            # Прогресс по дням (последние 10 дней)
            if stats['daily_progress']:
                text += f"📅 <b>Активность (последние дни):</b>\n"
                for day in stats['daily_progress'][:10]:
                    text += f"• {day['date']}: {day['tests_count']} тестов, {day['avg_score']}%\n"
                text += "\n"
            
            # Все темы с результатами
            if stats['topic_performance']:
                text += f"🎯 <b>Результаты по всем темам:</b>\n"
                for topic in stats['topic_performance']:
                    text += f"• {topic['topic']}: {topic['tests_count']} тестов, {topic['avg_score']}%\n"
                text += "\n"
            
            # Последние ошибки
            if stats['recent_errors']:
                text += f"❌ <b>Последние ошибки:</b>\n"
                for i, error in enumerate(stats['recent_errors'][:5], 1):
                    text += f"{i}. [{error['topic']}] {error['question']}\n"
                    text += f"   Ошибок: {error['error_count']}, {error['timestamp'][:10]}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к краткой статистике", callback_data=f"student_details_{user_id}")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_class_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику по классам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        class_stats = self.db.get_class_statistics()
        
        if not class_stats['class_stats']:
            text = "📈 <b>Статистика по классам</b>\n\nДанных нет."
        else:
            text = "📈 <b>Статистика по классам</b>\n\n"
            
            total_students = 0
            total_active = 0
            total_tests = 0
            
            for cls in class_stats['class_stats']:
                if cls['grade']:  # Пропускаем записи без класса
                    text += f"🎓 <b>{cls['grade']} класс:</b>\n"
                    text += f"• Учеников: {cls['students_count']}\n"
                    text += f"• Активных: {cls['active_students']} ({cls['activity_rate']}%)\n"
                    text += f"• Тестов: {cls['total_tests']}\n"
                    text += f"• Средний балл: {cls['avg_score']}%\n\n"
                    
                    total_students += cls['students_count']
                    total_active += cls['active_students']
                    total_tests += cls['total_tests']
            
            text += f"📊 <b>Общая статистика:</b>\n"
            text += f"• Всего учеников: {total_students}\n"
            text += f"• Активных: {total_active}\n"
            text += f"• Всего тестов: {total_tests}\n"
            overall_activity = round((total_active / total_students * 100) if total_students > 0 else 0, 1)
            text += f"• Общая активность: {overall_activity}%\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку учеников", callback_data="list_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === УДАЛЕНИЕ УЧЕНИКОВ ===

    async def remove_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        students = self.db.get_all_students_summary()
        
        if not students:
            text = "🗑️ <b>Удаление ученика</b>\n\nУченики не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        else:
            text = "🗑️ <b>Удаление ученика</b>\n\nВыберите ученика для удаления:\n\n"
            keyboard = []
            
            for student in students[:20]:  # Показываем первых 20
                status = "✅" if student['is_active'] else "❌"
                
                if student.get('username'):
                    identifier = f"@{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                else:
                    identifier = "Неизвестен"
                
                text += f"{status} <b>{identifier}</b> - {student['full_name']} ({student['grade']} класс)\n"
                
                if student.get('user_id'):
                    keyboard.append([InlineKeyboardButton(
                        f"🗑️ {identifier}", 
                        callback_data=f"remove_student_confirm_{student['user_id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_students")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_student_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        # Получаем информацию об ученике
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, full_name, grade 
                    FROM allowed_users 
                    WHERE user_id = ?
                ''', (user_id,))
                student = cursor.fetchone()
                
                if not student:
                    await query.edit_message_text("❌ Ученик не найден.")
                    return
                
                username, full_name, grade = student
                
                text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
                text += f"Вы действительно хотите удалить ученика?\n\n"
                text += f"👤 <b>Информация:</b>\n"
                if username:
                    text += f"• Username: @{username}\n"
                text += f"• ID: {user_id}\n"
                text += f"• ФИО: {full_name or 'не указано'}\n"
                text += f"• Класс: {grade or 'не указан'}\n\n"
                text += f"❗ <b>Внимание:</b> Это действие нельзя отменить!"
                
                keyboard = [
                    [InlineKeyboardButton("✅ Да, удалить", callback_data=f"remove_student_execute_{user_id}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="remove_student")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logging.error(f"Error in remove_student_confirm: {e}")
            await query.edit_message_text("❌ Ошибка при получении информации об ученике.")

    async def remove_student_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем информацию об ученике перед удалением
                cursor.execute('SELECT username, full_name FROM allowed_users WHERE user_id = ?', (user_id,))
                student = cursor.fetchone()
                
                if not student:
                    await query.edit_message_text("❌ Ученик не найден.")
                    return
                
                username, full_name = student
                
                # Удаляем из allowed_users
                cursor.execute('DELETE FROM allowed_users WHERE user_id = ?', (user_id,))
                
                # Удаляем из users (если есть)
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                
                conn.commit()
                
                identifier = f"@{username}" if username else f"ID: {user_id}"
                text = f"✅ <b>Ученик удален</b>\n\n"
                text += f"Ученик {identifier} ({full_name}) успешно удален из системы."
                
                keyboard = [
                    [InlineKeyboardButton("🗑️ Удалить еще", callback_data="remove_student")],
                    [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logging.error(f"Error removing student {user_id}: {e}")
            await query.edit_message_text("❌ Ошибка при удалении ученика.")

    # === РЕДАКТИРОВАНИЕ УЧЕНИКОВ ===

    async def edit_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        students = self.db.get_all_students_summary()
        
        if not students:
            text = "✏️ <b>Редактирование ученика</b>\n\nУченики не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        else:
            text = "✏️ <b>Редактирование ученика</b>\n\nВыберите ученика для редактирования:\n\n"
            keyboard = []
            
            for student in students[:20]:  # Показываем первых 20
                status = "✅" if student['is_active'] else "❌"
                
                if student.get('username'):
                    identifier = f"@{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                else:
                    identifier = "Неизвестен"
                
                text += f"{status} <b>{identifier}</b> - {student['full_name']} ({student['grade']} класс)\n"
                
                if student.get('user_id'):
                    keyboard.append([InlineKeyboardButton(
                        f"✏️ {identifier}", 
                        callback_data=f"edit_student_select_{student['user_id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_students")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор параметра для редактирования ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT au.username, au.full_name, au.grade, au.phone_number, au.is_active,
                           u.language
                    FROM allowed_users au
                    LEFT JOIN users u ON au.user_id = u.user_id
                    WHERE au.user_id = ?
                ''', (user_id,))
                student = cursor.fetchone()
                
                if not student:
                    await query.edit_message_text("❌ Ученик не найден.")
                    return
                
                username, full_name, grade, phone_number, is_active, language = student
                
                identifier = f"@{username}" if username else f"ID: {user_id}"
                status_text = "Активен" if is_active else "Неактивен"
                language_text = "Русский" if language == 'ru' else ("Қазақша" if language == 'kk' else language or 'не указан')
                
                text = f"✏️ <b>Редактирование ученика</b>\n\n"
                text += f"👤 <b>{identifier}</b>\n\n"
                text += f"<b>Текущие данные:</b>\n"
                text += f"• ФИО: {full_name or 'не указано'}\n"
                text += f"• Класс: {grade or 'не указан'}\n"
                text += f"• Телефон: {phone_number or 'не указан'}\n"
                text += f"• Язык: {language_text}\n"
                text += f"• Статус: {status_text}\n\n"
                text += f"Что хотите изменить?"
                
                keyboard = [
                    [InlineKeyboardButton("📝 Изменить ФИО", callback_data=f"edit_student_name_{user_id}")],
                    [InlineKeyboardButton("🎓 Изменить класс", callback_data=f"edit_student_grade_{user_id}")],
                    [InlineKeyboardButton("📱 Изменить телефон", callback_data=f"edit_student_phone_{user_id}")],
                    [InlineKeyboardButton("🌐 Изменить язык", callback_data=f"edit_student_language_{user_id}")],
                    [InlineKeyboardButton("🔄 Переключить статус", callback_data=f"edit_student_status_{user_id}")],
                    [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logging.error(f"Error in edit_student_select: {e}")
            await query.edit_message_text("❌ Ошибка при получении информации об ученике.")

    async def edit_student_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения ФИО ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['edit_student_id'] = user_id
        context.user_data['admin_action'] = 'edit_student_name'
        
        text = f"📝 <b>Изменение ФИО</b>\n\nВведите новое ФИО ученика:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_grade_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения класса ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['edit_student_id'] = user_id
        context.user_data['admin_action'] = 'edit_student_grade'
        
        text = f"🎓 <b>Изменение класса</b>\n\nВведите новый класс ученика (от 1 до 11):"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_phone_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения телефона ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['edit_student_id'] = user_id
        context.user_data['admin_action'] = 'edit_student_phone'
        
        text = f"📱 <b>Изменение телефона</b>\n\nВведите новый номер телефона или 'удалить' чтобы убрать:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_language_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения языка ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        text = f"🌐 <b>Изменение языка</b>\n\n"
        text += f"⚠️ <b>Внимание:</b> При смене языка будут очищены:\n"
        text += f"• История ошибок ученика\n"
        text += f"• Результаты тестов\n\n"
        text += f"Выберите новый язык:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data=f"set_language_ru_{user_id}")],
            [InlineKeyboardButton("🇰🇿 Қазақша", callback_data=f"set_language_kk_{user_id}")],
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def set_student_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Установка языка ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Парсим callback_data: set_language_ru_123456 или set_language_kk_123456
        parts = query.data.split('_')
        language = parts[2]  # ru или kk
        user_id = int(parts[3])
        
        try:
            # Устанавливаем язык и очищаем данные
            self.db.update_user_language(user_id, language)
            
            language_name = 'Русский' if language == 'ru' else 'Қазақша'
            
            text = f"✅ <b>Язык изменен</b>\n\n"
            text += f"Язык ученика изменен на: <b>{language_name}</b>\n\n"
            text += f"📝 <b>Очищены данные:</b>\n"
            text += f"• История ошибок\n"
            text += f"• Результаты тестов\n\n"
            text += f"Ученик теперь будет видеть темы на выбранном языке."
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                [InlineKeyboardButton("📋 К списку учеников", callback_data="list_students")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error setting student language: {e}")
            await query.edit_message_text("❌ Ошибка при изменении языка.")

    async def edit_student_status_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса ученика (активен/неактивен)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущий статус
                cursor.execute('SELECT is_active, full_name FROM allowed_users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    await query.edit_message_text("❌ Ученик не найден.")
                    return
                
                current_status, full_name = result
                new_status = not current_status
                
                # Обновляем статус
                cursor.execute('UPDATE allowed_users SET is_active = ? WHERE user_id = ?', (new_status, user_id))
                conn.commit()
                
                status_text = "активирован" if new_status else "деактивирован"
                status_emoji = "✅" if new_status else "❌"
                
                text = f"{status_emoji} <b>Статус изменен</b>\n\n"
                text += f"Ученик <b>{full_name}</b> {status_text}."
                
                keyboard = [
                    [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                    [InlineKeyboardButton("📋 К списку учеников", callback_data="list_students")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logging.error(f"Error toggling student status: {e}")
            await query.edit_message_text("❌ Ошибка при изменении статуса.")

    # === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ===

    async def handle_edit_student_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения ФИО ученика."""
        user_id = context.user_data.get('edit_student_id')
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID ученика не найден.")
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем в allowed_users
                cursor.execute('UPDATE allowed_users SET full_name = ? WHERE user_id = ?', (new_name, user_id))
                
                # Обновляем в users (если есть)
                cursor.execute('UPDATE users SET full_name = ? WHERE user_id = ?', (new_name, user_id))
                
                conn.commit()
                
                await update.message.reply_text(
                    f"✅ ФИО ученика изменено на: <b>{new_name}</b>",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logging.error(f"Error updating student name: {e}")
            await update.message.reply_text("❌ Ошибка при изменении ФИО.")
        
        # Очищаем состояние
        context.user_data.pop('edit_student_id', None)
        context.user_data.pop('admin_action', None)

    async def handle_edit_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка изменения класса ученика."""
        user_id = context.user_data.get('edit_student_id')
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID ученика не найден.")
            return
        
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем в allowed_users
                cursor.execute('UPDATE allowed_users SET grade = ? WHERE user_id = ?', (grade, user_id))
                
                # Обновляем в users (если есть)
                cursor.execute('UPDATE users SET grade = ? WHERE user_id = ?', (grade, user_id))
                
                conn.commit()
                
                await update.message.reply_text(
                    f"✅ Класс ученика изменен на: <b>{grade}</b>",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logging.error(f"Error updating student grade: {e}")
            await update.message.reply_text("❌ Ошибка при изменении класса.")
        
        # Очищаем состояние
        context.user_data.pop('edit_student_id', None)
        context.user_data.pop('admin_action', None)

    async def handle_edit_student_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка изменения телефона ученика."""
        user_id = context.user_data.get('edit_student_id')
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID ученика не найден.")
            return
        
        phone_number = "" if phone_text.lower() == 'удалить' else phone_text.strip()
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем в allowed_users
                cursor.execute('UPDATE allowed_users SET phone_number = ? WHERE user_id = ?', (phone_number, user_id))
                
                # Обновляем в users (если есть)
                cursor.execute('UPDATE users SET phone_number = ? WHERE user_id = ?', (phone_number, user_id))
                
                conn.commit()
                
                if phone_number:
                    await update.message.reply_text(
                        f"✅ Телефон ученика изменен на: <b>{phone_number}</b>",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text("✅ Телефон ученика удален.")
                
        except Exception as e:
            logging.error(f"Error updating student phone: {e}")
            await update.message.reply_text("❌ Ошибка при изменении телефона.")
        
        # Очищаем состояние
        context.user_data.pop('edit_student_id', None)
        context.user_data.pop('admin_action', None)

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def _add_student_to_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     student_user_id: int, username: str, fullname: str, 
                                     grade: int, admin_id: int, phone_number: str = "") -> bool:
        """Добавление ученика в базу данных (метод из старого файла)."""
        try:
            # Добавляем в allowed_users
            success = self.db.add_allowed_user_by_id(student_user_id, fullname, grade, admin_id, username, phone_number)
            
            if success:
                # Синхронизируем с таблицей users
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (user_id, username, full_name, grade, phone_number, language)
                        VALUES (?, ?, ?, ?, ?, 'ru')
                    ''', (student_user_id, username, fullname, grade, phone_number))
                    conn.commit()
                    
                logging.info(f"Student {student_user_id} added to database successfully")
                return True
            else:
                logging.error(f"Failed to add student {student_user_id} to allowed_users")
                return False
                
        except Exception as e:
            logging.error(f"Error adding student to database: {e}")
            return False 