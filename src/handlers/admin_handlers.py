from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from services.database import Database
import logging

class AdminHandlers:
    def __init__(self):
        self.db = Database()
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Главная админ-панель."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        is_super = self.db.is_super_admin(user_id)
        
        keyboard = []
        
        # Основные функции для всех админов
        keyboard.extend([
            [InlineKeyboardButton("👥 Управление учениками", callback_data="admin_students")],
            [InlineKeyboardButton("📚 Управление темами", callback_data="admin_topics")],
            [InlineKeyboardButton("❓ Управление вопросами", callback_data="admin_questions")],
        ])
        
        # Функции только для суперадмина
        if is_super:
            keyboard.append([InlineKeyboardButton("👑 Управление админами", callback_data="admin_admins")])
        
        keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        role = "Суперадминистратор" if is_super else "Администратор"
        text = f"🔧 **Админ-панель**\n\nВаша роль: {role}\n\nВыберите действие:"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ УЧЕНИКАМИ ===
    
    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить ученика", callback_data="add_student")],
            [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
            [InlineKeyboardButton("✏️ Редактировать ученика", callback_data="edit_student")],
            [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👥 **Управление учениками**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_student'
        await query.edit_message_text("➕ **Добавление ученика**\n\nВведите username ученика (без @):")
    
    async def list_students(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех учеников."""
        query = update.callback_query
        await query.answer()
        
        students = self.db.get_all_allowed_users()
        
        if not students:
            text = "📋 **Список учеников**\n\nУченики не найдены."
        else:
            text = "📋 **Список учеников**\n\n"
            for i, student in enumerate(students, 1):
                status = "✅" if student['is_active'] else "❌"
                text += f"{i}. {status} @{student['username']}\n"
                text += f"   ФИО: {student['full_name']}\n"
                text += f"   Класс: {student['grade']}\n"
                text += f"   Добавлен: {student['added_at'][:10]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ ТЕМАМИ ===
    
    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
            [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
            [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 **Управление темами**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_topic'
        await query.edit_message_text("➕ **Добавление темы**\n\nВведите название новой темы:")
    
    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем."""
        query = update.callback_query
        await query.answer()
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "📋 **Список тем**\n\nТемы не найдены."
        else:
            text = "📋 **Список тем**\n\n"
            for i, topic in enumerate(topics, 1):
                status = "✅" if topic['is_active'] else "❌"
                text += f"{i}. {status} {topic['name']}\n"
                text += f"   ID: {topic['id']}\n"
                text += f"   Описание: {topic['description']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ АДМИНАМИ (только для суперадмина) ===
    
    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами (только для суперадмина)."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Только суперадминистратор может управлять админами.")
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👑 **Управление админами**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_admin'
        await query.edit_message_text("➕ **Добавление админа**\n\nВведите user_id нового админа:")
    
    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        query = update.callback_query
        await query.answer()
        
        admins = self.db.get_all_admins()
        
        if not admins:
            text = "📋 **Список админов**\n\nАдмины не найдены."
        else:
            text = "📋 **Список админов**\n\n"
            for i, admin in enumerate(admins, 1):
                role = "👑 Суперадмин" if admin['is_super_admin'] else "🔧 Админ"
                text += f"{i}. {role}\n"
                text += f"   ID: {admin['user_id']}\n"
                text += f"   Username: @{admin['username'] or 'не указан'}\n"
                text += f"   ФИО: {admin['full_name'] or 'не указано'}\n"
                text += f"   Добавлен: {admin['created_at'][:10]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
    
    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        action = context.user_data.get('admin_action')
        text = update.message.text.strip()
        
        if action == 'add_student':
            await self._handle_add_student(update, context, text)
        elif action == 'add_topic':
            await self._handle_add_topic(update, context, text)
        elif action == 'add_admin':
            await self._handle_add_admin(update, context, text)
        elif action == 'student_fullname':
            await self._handle_student_fullname(update, context, text)
        elif action == 'student_grade':
            await self._handle_student_grade(update, context, text)
        elif action == 'topic_description':
            await self._handle_topic_description(update, context, text)
    
    async def _handle_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка добавления ученика - этап 1 (username)."""
        if username.startswith('@'):
            username = username[1:]
        
        context.user_data['new_student_username'] = username
        context.user_data['admin_action'] = 'student_fullname'
        
        await update.message.reply_text(f"Введите ФИО ученика @{username}:")
    
    async def _handle_student_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_grade'
        
        await update.message.reply_text("Введите класс ученика (число от 1 до 11):")
    
    async def _handle_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика - этап 3 (класс)."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        username = context.user_data.get('new_student_username')
        fullname = context.user_data.get('new_student_fullname')
        admin_id = update.effective_user.id
        
        success = self.db.add_allowed_user(username, fullname, grade, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Ученик @{username} успешно добавлен!\n\nФИО: {fullname}\nКласс: {grade}")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении ученика. Возможно, @{username} уже существует.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_username', None)
        context.user_data.pop('new_student_fullname', None)
    
    async def _handle_add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
        """Обработка добавления темы - этап 1 (название)."""
        context.user_data['new_topic_name'] = topic_name
        context.user_data['admin_action'] = 'topic_description'
        
        await update.message.reply_text(f"Введите описание для темы '{topic_name}' (или отправьте '-' для пропуска):")
    
    async def _handle_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
        """Обработка добавления темы - этап 2 (описание)."""
        topic_name = context.user_data.get('new_topic_name')
        admin_id = update.effective_user.id
        
        if description == '-':
            description = f"Тема: {topic_name}"
        
        success = self.db.add_topic(topic_name, description, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Тема '{topic_name}' успешно добавлена!")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении темы. Возможно, тема '{topic_name}' уже существует.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_topic_name', None)
    
    async def _handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления админа."""
        try:
            new_admin_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text("❌ Введите корректный user_id (число). Попробуйте еще раз:")
            return
        
        admin_id = update.effective_user.id
        
        # Проверяем, что пользователь не пытается добавить себя
        if new_admin_id == admin_id:
            await update.message.reply_text("❌ Вы не можете добавить себя в качестве админа.")
            context.user_data.pop('admin_action', None)
            return
        
        success = self.db.add_admin(new_admin_id, "unknown", "Новый админ", False, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {new_admin_id} успешно добавлен в качестве админа!")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении админа. Возможно, пользователь {new_admin_id} уже является админом.")
        
        context.user_data.pop('admin_action', None)
    
    # === СТАТИСТИКА ===
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику системы."""
        query = update.callback_query
        await query.answer()
        
        # Получаем статистику
        students = self.db.get_all_allowed_users()
        topics = self.db.get_all_topics(active_only=False)
        admins = self.db.get_all_admins()
        
        active_students = len([s for s in students if s['is_active']])
        active_topics = len([t for t in topics if t['is_active']])
        
        text = "📊 **Статистика системы**\n\n"
        text += f"👥 Ученики: {len(students)} (активных: {active_students})\n"
        text += f"📚 Темы: {len(topics)} (активных: {active_topics})\n"
        text += f"👑 Админы: {len(admins)}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown') 