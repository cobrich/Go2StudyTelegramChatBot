"""
Модуль для управления учениками в админ-панели.
Включает добавление, редактирование, удаление учеников и выбор языка.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging
import sqlite3

class StudentsHandler(AdminBaseHandler):
    """Обработчик для управления учениками."""

    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        text = f"👥 <b>Управление учениками</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🆔 Добавить ученика", callback_data="add_student_by_id")],
            [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
            [InlineKeyboardButton("✏️ Редактировать ученика", callback_data="edit_student_start")],
            [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_student_by_id_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по ID."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"🆔 <b>Добавление ученика</b>\n\n"
        text += f"Введите Telegram ID ученика:\n\n"
        text += f"💡 <b>Как узнать ID:</b>\n"
        text += f"• Попросите ученика написать команду /myid боту\n"
        text += f"• Или используйте @userinfobot"
        
        context.user_data['admin_action'] = 'add_student_by_id'
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ ДОБАВЛЕНИЯ УЧЕНИКА ===

    async def handle_add_student_by_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления ученика по ID - этап 1 (user_id)."""
        try:
            student_user_id = int(user_id_text)
        except ValueError:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ Введите корректный user_id (число). Попробуйте еще раз:",
                reply_markup=reply_markup
            )
            return
        
        # Проверяем, что этот пользователь еще не добавлен
        if self.db.check_user_access(student_user_id):
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"❌ Пользователь с ID {student_user_id} уже имеет доступ к боту.",
                reply_markup=reply_markup
            )
            context.user_data.pop('admin_action', None)
            return
        
        # Пытаемся автоматически получить информацию о пользователе
        await update.message.reply_text("🔍 Получаю информацию о пользователе через Telegram API...")
        
        auto_info = {
            'username': None,
            'first_name': None,
            'last_name': None,
            'found_via_api': False
        }
        
        try:
            user_info = await context.bot.get_chat(student_user_id)
            if user_info:
                auto_info.update({
                    'username': user_info.username,
                    'first_name': user_info.first_name,
                    'last_name': user_info.last_name,
                    'found_via_api': True
                })
                
                # Формируем автоматически предложенное ФИО
                suggested_name = f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
                if suggested_name:
                    context.user_data['suggested_full_name'] = suggested_name
                    
        except Exception as e:
            logging.warning(f"Не удалось получить информацию о пользователе {student_user_id}: {e}")
        
        # Сохраняем полученную информацию
        context.user_data['new_student_user_id'] = student_user_id
        context.user_data['auto_detected_info'] = auto_info
        context.user_data['admin_action'] = 'student_by_id_fullname'
        
        # Формируем сообщение с результатами автоопределения
        info_text = f"🆔 <b>Добавление ученика</b>\n\n<b>ID:</b> {student_user_id}\n\n"
        
        if auto_info['found_via_api']:
            info_text += f"✅ <b>Информация найдена через Telegram API:</b>\n"
            if auto_info['username']:
                info_text += f"👤 Username: @{auto_info['username']}\n"
            if auto_info['first_name'] or auto_info['last_name']:
                telegram_name = f"{auto_info['first_name'] or ''} {auto_info['last_name'] or ''}".strip()
                info_text += f"📝 Имя в Telegram: {telegram_name}\n"
            info_text += f"\n"
        else:
            info_text += f"⚠️ <b>Информация не найдена через API</b>\n"
            info_text += f"Возможные причины:\n"
            info_text += f"• Пользователь еще не писал боту\n"
            info_text += f"• Скрытый профиль\n"
            info_text += f"• Неверный ID\n\n"
        
        # Предлагаем ввести ФИО
        if context.user_data.get('suggested_full_name'):
            info_text += f"💡 <b>Предлагаемое ФИО:</b> {context.user_data['suggested_full_name']}\n\n"
            info_text += f"Введите ФИО ученика или отправьте '+' чтобы использовать предлагаемое:"
        else:
            info_text += f"Введите ФИО ученика:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_student_by_id_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика по ID - этап 2 (ФИО)."""
        # Проверяем, хочет ли админ использовать предложенное ФИО
        if fullname.strip() == '+' and context.user_data.get('suggested_full_name'):
            fullname = context.user_data['suggested_full_name']
            await update.message.reply_text(f"✅ Использую предложенное ФИО: {fullname}")
        
        if not fullname.strip():
            await update.message.reply_text("❌ ФИО не может быть пустым. Попробуйте еще раз:")
            return
        
        context.user_data['new_student_fullname'] = fullname.strip()
        context.user_data['admin_action'] = 'student_by_id_grade'
        
        student_user_id = context.user_data.get('new_student_user_id')
        auto_info = context.user_data.get('auto_detected_info', {})
        
        # Формируем сводку информации
        summary_text = f"🆔 <b>Добавление ученика</b>\n\n"
        summary_text += f"<b>ID:</b> {student_user_id}\n"
        summary_text += f"<b>ФИО:</b> {fullname}\n"
        
        if auto_info.get('username'):
            summary_text += f"<b>Username:</b> @{auto_info['username']} (автоопределен)\n"
        
        summary_text += f"\nВведите класс ученика (1-11):"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(summary_text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_student_by_id_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика по ID - этап 3 (класс)."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        student_user_id = context.user_data.get('new_student_user_id')
        fullname = context.user_data.get('new_student_fullname')
        auto_info = context.user_data.get('auto_detected_info', {})
        admin_id = update.effective_user.id
        
        # Используем автоматически определенный username если есть
        username = auto_info.get('username')
        
        # Добавляем ученика в базу данных
        success = self.db.add_allowed_user_by_id(
            user_id=student_user_id,
            full_name=fullname,
            grade=grade,
            added_by=admin_id,
            username=username
        )
        
        if success:
            # Формируем сообщение об успехе
            identifier = f"@{username}" if username else f"ID: {student_user_id}"
            success_text = f"✅ <b>Ученик успешно добавлен!</b>\n\n"
            success_text += f"🆔 <b>ID:</b> {student_user_id}\n"
            success_text += f"👤 <b>ФИО:</b> {fullname}\n"
            success_text += f"🎓 <b>Класс:</b> {grade}\n"
            
            if username:
                success_text += f"📱 <b>Username:</b> @{username} (автоопределен)\n"
                success_text += f"✅ Данные синхронизированы автоматически\n"
            else:
                success_text += f"⚠️ Username не найден\n"
                success_text += f"💡 Будет добавлен при первом входе в бот\n"
            
            if auto_info.get('found_via_api'):
                success_text += f"🔄 Информация получена через Telegram API\n"
            
            success_text += f"\n📊 Ученик может начать пользоваться ботом"
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить еще", callback_data="add_student_by_id")],
                [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            error_text = f"❌ Ошибка при добавлении ученика.\n"
            error_text += f"Возможно, пользователь с ID {student_user_id} уже существует."
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем временные данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_user_id', None)
        context.user_data.pop('new_student_fullname', None)
        context.user_data.pop('auto_detected_info', None)
        context.user_data.pop('suggested_full_name', None)

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
                status = "✅" if student['has_access'] else "❌"
                
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
                
                # Добавляем индикатор активности в тесте
                test_activity = "🔄 В тесте" if student['is_active'] else "💤 Не в тесте"
                
                text += f"{i}. {status} <b>{identifier}</b>\n"
                text += f"   {student['full_name']} ({student['grade']} класс)\n"
                text += f"   {stats}\n"
                text += f"   Статус: {student['status']} | {test_activity}\n\n"
                
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
            
            # Показываем активность по дням (последние 10 дней)
            if stats['daily_progress']:
                text += f"\n📅 <b>Активность по дням (последние 10 дней):</b>\n"
                for day in stats['daily_progress'][:10]:
                    text += f"• {day['date']}: {day['tests_count']} тестов, {day['avg_score']}%\n"
            
            # Показываем ВСЕ темы с результатами
            if stats['topic_performance']:
                text += f"\n🎯 <b>Результаты по всем темам:</b>\n"
                for i, topic in enumerate(stats['topic_performance'], 1):
                    text += f"{i}. <b>{topic['topic']}</b>: {topic['tests_count']} тестов, {topic['avg_score']}%\n"
                    text += f"   Последний тест: {topic['last_attempt'][:10] if topic['last_attempt'] else 'н/д'}\n"
            
            # Показываем проблемные темы с детальной информацией
            if stats['error_analysis']:
                text += f"\n❌ <b>Анализ ошибок по темам:</b>\n"
                for i, error in enumerate(stats['error_analysis'], 1):
                    text += f"{i}. <b>{error['topic']}</b>:\n"
                    text += f"   • Уникальных ошибок: {error['unique_errors']}\n"
                    text += f"   • Всего ошибок: {error['total_errors']}\n"
                    text += f"   • Последняя ошибка: {error['last_error'][:10] if error['last_error'] else 'н/д'}\n"
            
            # Показываем последние ошибки
            if stats['recent_errors']:
                text += f"\n🔍 <b>Последние ошибки (топ-10):</b>\n"
                for i, error in enumerate(stats['recent_errors'][:10], 1):
                    question_preview = error['question'][:50] + '...' if len(error['question']) > 50 else error['question']
                    text += f"{i}. <b>[{error['topic']}]</b> {question_preview}\n"
                    text += f"   Ошибок: {error['error_count']}, Дата: {error['timestamp'][:10]}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_students")]
            ]
        
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
                status = "✅" if student['has_access'] else "❌"
                
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
            # Используем database facade вместо прямого SQLite подключения
            student_info = self.db.get_allowed_user_by_id(user_id)
            
            if not student_info:
                await query.edit_message_text("❌ Ученик не найден.")
                return
            
            username = student_info.get('username')
            full_name = student_info.get('full_name')
            grade = student_info.get('grade')
            
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
            # Используем database facade вместо прямого SQLite подключения
            student_info = self.db.get_allowed_user_by_id(user_id)
            
            if not student_info:
                await query.edit_message_text("❌ Ученик не найден.")
                return
            
            username = student_info.get('username')
            full_name = student_info.get('full_name')
            
            # Удаляем все данные ученика через database facade
            success = self.db.delete_all_user_data(user_id)
            
            if success:
                # Формируем сообщение об успехе
                identifier = f"@{username}" if username else f"ID: {user_id}"
                success_text = f"✅ <b>Ученик удален</b>\n\n"
                success_text += f"Ученик {identifier} ({full_name}) успешно удален из системы.\n\n"
                success_text += f"📊 Все связанные данные (результаты тестов, ошибки) также удалены."
                
                keyboard = [
                    [InlineKeyboardButton("🗑️ Удалить еще", callback_data="remove_student")],
                    [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text("❌ Ошибка при удалении ученика.")
                
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
                status = "✅" if student['has_access'] else "❌"
                
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
        """Выбор параметра для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        # Получаем информацию об ученике
        try:
            # Используем database facade вместо прямого SQLite подключения
            student_info = self.db.get_user_full_profile(user_id)
            
            if not student_info:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="edit_student_start")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден.", reply_markup=reply_markup)
                return
            
            username = student_info.get('username')
            full_name = student_info.get('full_name')
            grade = student_info.get('grade')
            has_access = student_info.get('has_access')
            language = student_info.get('language')
            is_active = self.db.is_user_active(user_id)
            
            text = f"✏️ <b>Редактирование ученика</b>\n\n"
            text += f"👤 <b>Текущие данные:</b>\n"
            if username:
                text += f"• Username: @{username}\n"
            text += f"• ID: {user_id}\n"
            text += f"• ФИО: {full_name or 'не указано'}\n"
            text += f"• Класс: {grade or 'не указан'}\n"
            text += f"• Язык: {'Русский' if language == 'ru' else 'Қазақша' if language == 'kk' else language}\n"
            text += f"• Доступ: {'Разрешен' if has_access else 'Заблокирован'}\n"
            text += f"• В тесте: {'Да' if is_active else 'Нет'}\n\n"
            text += f"Что хотите изменить?"
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить ФИО", callback_data=f"edit_student_name_{user_id}")],
                [InlineKeyboardButton("🎓 Изменить класс", callback_data=f"edit_student_grade_{user_id}")],
                [InlineKeyboardButton("🌐 Изменить язык", callback_data=f"edit_student_language_{user_id}")],
                [InlineKeyboardButton("🔄 Изменить доступ", callback_data=f"edit_student_status_{user_id}")],
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error in edit_student_select: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="edit_student_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Ошибка при получении информации об ученике.", reply_markup=reply_markup)

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

    async def edit_student_language_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения языка ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        text = f"🌐 <b>Изменение языка</b>\n\nВыберите новый язык для ученика:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data=f"set_student_lang_ru_{user_id}")],
            [InlineKeyboardButton("🇰🇿 Қазақша", callback_data=f"set_student_lang_kk_{user_id}")],
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def set_student_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Установка языка ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Парсим callback_data: set_student_lang_ru_123456 или set_student_lang_kk_123456
        parts = query.data.split('_')
        language = parts[3]  # ru или kk
        user_id = int(parts[4])
        
        logging.info(f"[set_student_language] Changing language for user {user_id} to {language}")
        
        try:
            # Обновляем язык в базе данных
            self.db.update_user_language(user_id, language)
            
            # Очищаем данные пользователя при смене языка
            self.db.clear_user_data_on_language_change(user_id)
            
            language_name = "Русский" if language == "ru" else "Қазақша"
            
            text = f"✅ <b>Язык изменен</b>\n\n"
            text += f"Язык ученика успешно изменен на: {language_name}\n\n"
            text += f"ℹ️ Данные пользователя (активные тесты, прогресс) были сброшены."
            
            logging.info(f"[set_student_language] Successfully changed language for user {user_id} to {language}")
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error setting student language: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Ошибка при изменении языка.", reply_markup=reply_markup)

    async def edit_student_status_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса доступа ученика (разрешен/заблокирован)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        try:
            # Используем database facade вместо прямого SQLite подключения
            student_info = self.db.get_allowed_user_by_id(user_id)
            
            if not student_info:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="edit_student_start")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден.", reply_markup=reply_markup)
                return
            
            current_access = student_info.get('has_access')
            full_name = student_info.get('full_name')
            new_access = not current_access
            
            # Обновляем статус доступа через database facade
            success = self.db.set_user_access(user_id, new_access)
            
            if success:
                status_text = "разрешен доступ" if new_access else "заблокирован доступ"
                status_emoji = "✅" if new_access else "🚫"
                
                text = f"{status_emoji} <b>Доступ изменен</b>\n\n"
                text += f"Ученику {full_name} {status_text}.\n\n"
                if new_access:
                    text += f"Ученик теперь может пользоваться ботом."
                else:
                    text += f"Ученик больше не может пользоваться ботом."
                
                keyboard = [
                    [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                    [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text("❌ Ошибка при изменении доступа.")
                
        except Exception as e:
            logging.error(f"Error toggling student access: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Ошибка при изменении доступа.", reply_markup=reply_markup)

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ РЕДАКТИРОВАНИЯ ===

    async def handle_edit_student_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения ФИО ученика."""
        user_id = context.user_data.get('edit_student_id')
        
        if not user_id:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Ошибка: не найден ID ученика.", reply_markup=reply_markup)
            return
        
        if not new_name.strip():
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ ФИО не может быть пустым. Попробуйте еще раз:", reply_markup=reply_markup)
            return
        
        try:
            # Обновляем ФИО в базе данных
            success = self.db.update_allowed_user_by_id(user_id, full_name=new_name.strip())
            
            if success:
                text = f"✅ <b>ФИО изменено</b>\n\n"
                text += f"ФИО ученика успешно изменено на: {new_name.strip()}"
                
                keyboard = [
                    [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                    [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
                ]
            else:
                text = f"❌ <b>Ошибка при изменении ФИО</b>\n\n"
                text += f"Не удалось изменить ФИО ученика."
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data=f"edit_student_name_{user_id}")],
                    [InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error updating student name: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Ошибка при изменении ФИО.", reply_markup=reply_markup)
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_student_id', None)

    async def handle_edit_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка изменения класса ученика."""
        user_id = context.user_data.get('edit_student_id')
        
        if not user_id:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Ошибка: не найден ID ученика.", reply_markup=reply_markup)
            return
        
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:", reply_markup=reply_markup)
                return
        except ValueError:
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:", reply_markup=reply_markup)
            return
        
        try:
            # Обновляем класс в базе данных
            success = self.db.update_allowed_user_by_id(user_id, grade=grade)
            
            if success:
                text = f"✅ <b>Класс изменен</b>\n\n"
                text += f"Класс ученика успешно изменен на: {grade}"
                
                keyboard = [
                    [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_student_select_{user_id}")],
                    [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_student_start")]
                ]
            else:
                text = f"❌ <b>Ошибка при изменении класса</b>\n\n"
                text += f"Не удалось изменить класс ученика."
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data=f"edit_student_grade_{user_id}")],
                    [InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error updating student grade: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_select_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Ошибка при изменении класса.", reply_markup=reply_markup)
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_student_id', None) 