"""
Модуль для управления темами в админ-панели.
Включает добавление, редактирование, удаление тем и слияние тем.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging

class TopicsHandler(AdminBaseHandler):
    """Обработчик для управления темами."""

    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"📚 <b>Управление темами</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
            [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
            [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic_start")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
            [InlineKeyboardButton("📊 Статистика тем", callback_data="detailed_topics_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить новую тему", callback_data="add_custom_topic")],
            [InlineKeyboardButton("📋 Добавить из базовых тем", callback_data="add_base_topics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("➕ <b>Добавление темы</b>\n\nВыберите способ добавления:", 
                                     reply_markup=reply_markup, parse_mode='HTML')

    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем с количеством вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "📋 <b>Список тем</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            # Группируем темы по основным разделам
            topics_by_section = {}
            for topic in topics:
                main_topic = topic.get('main_topic', 'Без раздела')
                if main_topic not in topics_by_section:
                    topics_by_section[main_topic] = []
                topics_by_section[main_topic].append(topic)
            
            text = f"📋 <b>Список тем</b>\n\n"
            text += f"Всего тем: {len(topics)}\n\n"
            
            for main_topic, section_topics in topics_by_section.items():
                text += f"📚 <b>{main_topic}</b> ({len(section_topics)} тем)\n"
                
                # Сортируем темы: сначала активные, потом неактивные
                active_topics = [t for t in section_topics if t['is_active']]
                inactive_topics = [t for t in section_topics if not t['is_active']]
                
                for topic in active_topics:
                    status = "✅"
                    text += f"  {status} {topic['name']} ({topic['question_count']} вопросов)\n"
                
                for topic in inactive_topics:
                    status = "❌"
                    text += f"  {status} {topic['name']} ({topic['question_count']} вопросов)\n"
                
                text += "\n"
            
            keyboard = [
                [InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_topics_stats")],
                [InlineKeyboardButton("🔄 Обновить статистику", callback_data="refresh_topics_stats")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_custom_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления пользовательской темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем список основных разделов
        user_id = update.effective_user.id
        user_language = self.db.get_user_language(user_id)
        
        # Получаем разделы по языку пользователя
        main_topics = self.db.get_main_topics_by_language(user_language, active_only=True)
        
        if not main_topics:
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Основные разделы не найдены. Сначала создайте базовую структуру.", 
                                         reply_markup=reply_markup, parse_mode='HTML')
            return
        
        context.user_data['admin_action'] = 'select_main_topic_for_new'
        context.user_data['main_topics_list'] = main_topics
        
        keyboard = []
        for i, topic in enumerate(main_topics):
            keyboard.append([InlineKeyboardButton(
                f"📚 {topic['name']}",
                callback_data=f"select_main_topic_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("➕ <b>Добавление новой темы</b>\n\nВыберите основной раздел для новой темы:", 
                                     reply_markup=reply_markup, parse_mode='HTML')

    async def select_main_topic_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор основного раздела для новой темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_index = int(query.data.replace('select_main_topic_', ''))
            main_topics_list = context.user_data.get('main_topics_list', [])
            
            if topic_index >= len(main_topics_list):
                await query.edit_message_text("❌ Неверный выбор раздела.")
                return
            
            selected_topic = main_topics_list[topic_index]
            context.user_data['selected_main_topic'] = selected_topic['name']
            context.user_data['selected_main_topic_language'] = selected_topic['language']
            context.user_data['admin_action'] = 'add_topic'
            
            # Получаем существующие темы в этом разделе
            existing_topics = self.db.get_subtopics_by_main_topic(selected_topic['name'])
            
            text = f"➕ <b>Добавление темы в раздел</b>\n\n"
            text += f"📚 <b>Раздел:</b> {selected_topic['name']}\n"
            text += f"🌐 <b>Язык:</b> {'Русский' if selected_topic['language'] == 'ru' else 'Казахский'}\n\n"
            
            if existing_topics:
                text += f"📋 <b>Существующие темы в этом разделе ({len(existing_topics)}):</b>\n"
                for i, topic_name in enumerate(existing_topics[:5], 1):
                    text += f"{i}. {topic_name}\n"
                
                if len(existing_topics) > 5:
                    text += f"... и еще {len(existing_topics) - 5} тем\n"
                
                text += "\n⚠️ <i>Убедитесь, что новая тема не дублирует существующие</i>\n\n"
            else:
                text += "📋 <i>В этом разделе пока нет тем</i>\n\n"
            
            text += "Введите название новой темы:"
            
            keyboard = []
            if existing_topics:
                keyboard.append([InlineKeyboardButton("📋 Показать все темы раздела", callback_data=f"show_section_topics_{topic_index}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Выбрать другой раздел", callback_data="add_custom_topic")])
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_topics")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при выборе раздела.")

    async def show_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать все темы в разделе."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_index = int(query.data.replace('show_section_topics_', ''))
            main_topics_list = context.user_data.get('main_topics_list', [])
            
            if topic_index >= len(main_topics_list):
                await query.edit_message_text("❌ Неверный выбор раздела.")
                return
            
            selected_topic = main_topics_list[topic_index]
            existing_topics = self.db.get_subtopics_by_main_topic(selected_topic['name'])
            
            text = f"📋 <b>Все темы в разделе '{selected_topic['name']}'</b>\n\n"
            
            if existing_topics:
                for i, topic_name in enumerate(existing_topics, 1):
                    text += f"{i}. {topic_name}\n"
            else:
                text += "В этом разделе пока нет тем."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к добавлению", callback_data=f"select_main_topic_{topic_index}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_topics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при отображении тем.")

    async def handle_add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
        """Обработка добавления темы - этап 1 (название)."""
        context.user_data['new_topic_name'] = topic_name
        context.user_data['admin_action'] = 'topic_description'
        
        await update.message.reply_text(f"Введите описание для темы '{topic_name}' (или отправьте '-' для пропуска):")

    async def handle_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
        """Обработка добавления темы - этап 2 (описание)."""
        topic_name = context.user_data.get('new_topic_name')
        selected_main_topic = context.user_data.get('selected_main_topic')
        selected_language = context.user_data.get('selected_main_topic_language')
        admin_id = update.effective_user.id
        
        if description == '-':
            description = f"Тема: {topic_name}"
        
        # Добавляем тему с указанием языка
        success = self.db.add_topic_with_language(topic_name, selected_language, selected_main_topic, admin_id)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
                [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
                [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic_start")],
                [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"✅ Тема '{topic_name}' успешно добавлена в раздел '{selected_main_topic}' ({selected_language})!\n\n📚 <b>Управление темами</b>\n\nВыберите действие:"
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            error_text = f"❌ Ошибка при добавлении темы. Возможно, тема '{topic_name}' уже существует."
            await update.message.reply_text(error_text)
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_topic_name', None)
        context.user_data.pop('selected_main_topic', None)
        context.user_data.pop('selected_main_topic_language', None)

    # === ВРЕМЕННЫЕ ЗАГЛУШКИ ДЛЯ СОВМЕСТИМОСТИ ===
    
    async def add_base_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для добавления базовых тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления базовых тем в разработке...")

    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "❌ <b>Редактирование тем</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = f"✏️ <b>Редактирование тем</b>\n\nВыберите тему для редактирования:\n\n"
            
            # Группируем по разделам
            topics_by_section = {}
            for topic in topics:
                main_topic = topic.get('main_topic', 'Без раздела')
                if main_topic not in topics_by_section:
                    topics_by_section[main_topic] = []
                topics_by_section[main_topic].append(topic)
            
            keyboard = []
            for main_topic, section_topics in topics_by_section.items():
                # Добавляем заголовок раздела (неактивная кнопка)
                keyboard.append([InlineKeyboardButton(f"📚 {main_topic}", callback_data="noop")])
                
                for topic in section_topics:
                    status = "✅" if topic['is_active'] else "❌"
                    button_text = f"  {status} {topic['name']} ({topic['question_count']})"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"edit_topic_select_{topic['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_topic_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор темы для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_select_', ''))
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            status = "Активна" if topic['is_active'] else "Неактивна"
            status_emoji = "✅" if topic['is_active'] else "❌"
            
            text = f"✏️ <b>Редактирование темы</b>\n\n"
            text += f"<b>Название:</b> {topic['name']}\n"
            text += f"<b>Раздел:</b> {topic.get('main_topic', 'Без раздела')}\n"
            text += f"<b>Описание:</b> {topic.get('description', 'Не указано')}\n"
            text += f"<b>Статус:</b> {status_emoji} {status}\n"
            text += f"<b>Вопросов:</b> {topic['question_count']}\n\n"
            text += "Выберите действие:"
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_topic_name_{topic_id}")],
                [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_topic_desc_{topic_id}")],
                [InlineKeyboardButton("📚 Изменить раздел", callback_data=f"edit_topic_section_{topic_id}")],
                [InlineKeyboardButton(f"{'❌ Деактивировать' if topic['is_active'] else '✅ Активировать'}", 
                                    callback_data=f"edit_topic_toggle_{topic_id}")],
                [InlineKeyboardButton("🔙 К списку тем", callback_data="edit_topic_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при выборе темы.")

    async def edit_topic_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения названия темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_name_', ''))
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            context.user_data['admin_action'] = 'edit_topic_name'
            context.user_data['edit_topic_id'] = topic_id
            
            text = f"📝 <b>Изменение названия темы</b>\n\n"
            text += f"Тема: <b>{topic['name']}</b>\n"
            text += f"Текущее название: <i>{topic['name']}</i>\n\n"
            text += "Введите новое название темы:"
            
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_topic_select_{topic_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при редактировании темы.")

    async def edit_topic_desc_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения описания темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_desc_', ''))
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            context.user_data['admin_action'] = 'edit_topic_description'
            context.user_data['edit_topic_id'] = topic_id
            
            text = f"📄 <b>Изменение описания темы</b>\n\n"
            text += f"Тема: <b>{topic['name']}</b>\n"
            text += f"Текущее описание: <i>{topic.get('description', 'Не указано')}</i>\n\n"
            text += "Введите новое описание темы:"
            
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_topic_select_{topic_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при редактировании темы.")

    async def edit_topic_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_toggle_', ''))
            
            # Переключаем статус
            success = self.db.toggle_topic_status(topic_id)
            
            if success:
                # Возвращаемся к редактированию темы
                await self.edit_topic_select(update, context)
            else:
                await query.edit_message_text("❌ Ошибка при изменении статуса темы.")
                
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при изменении статуса темы.")

    async def handle_edit_topic_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения названия темы."""
        topic_id = context.user_data.get('edit_topic_id')
        
        if not topic_id:
            await update.message.reply_text("❌ Ошибка: тема не выбрана.")
            return
        
        success = self.db.update_topic_name(topic_id, new_name)
        
        if success:
            text = f"✅ Название темы успешно изменено на '{new_name}'!"
        else:
            text = f"❌ Ошибка при изменении названия темы. Возможно, тема с таким названием уже существует."
        
        keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_topic_id', None)

    async def handle_edit_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_description: str) -> None:
        """Обработка изменения описания темы."""
        topic_id = context.user_data.get('edit_topic_id')
        
        if not topic_id:
            await update.message.reply_text("❌ Ошибка: тема не выбрана.")
            return
        
        success = self.db.update_topic_description(topic_id, new_description)
        
        if success:
            text = f"✅ Описание темы успешно изменено!"
        else:
            text = f"❌ Ошибка при изменении описания темы."
        
        keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_topic_id', None)

    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "❌ <b>Удаление тем</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = f"🗑️ <b>Удаление тем</b>\n\nВыберите тему для удаления:\n\n"
            text += "⚠️ <b>Внимание!</b> При удалении темы будут удалены:\n"
            text += "• Все вопросы в этой теме\n"
            text += "• Все результаты тестов по этой теме\n"
            text += "• Все ссылки на эти вопросы\n\n"
            
            # Группируем по разделам
            topics_by_section = {}
            for topic in topics:
                main_topic = topic.get('main_topic', 'Без раздела')
                if main_topic not in topics_by_section:
                    topics_by_section[main_topic] = []
                topics_by_section[main_topic].append(topic)
            
            keyboard = []
            for main_topic, section_topics in topics_by_section.items():
                # Добавляем заголовок раздела (неактивная кнопка)
                keyboard.append([InlineKeyboardButton(f"📚 {main_topic}", callback_data="noop")])
                
                for topic in section_topics:
                    status = "✅" if topic['is_active'] else "❌"
                    button_text = f"  {status} {topic['name']} ({topic['question_count']} вопр.)"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"remove_topic_confirm_{topic['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_topic_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('remove_topic_confirm_', ''))
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            text = f"🗑️ <b>Подтверждение удаления темы</b>\n\n"
            text += f"<b>Тема:</b> {topic['name']}\n"
            text += f"<b>Раздел:</b> {topic.get('main_topic', 'Без раздела')}\n"
            text += f"<b>Вопросов:</b> {topic['question_count']}\n\n"
            text += "⚠️ <b>ВНИМАНИЕ!</b> Это действие необратимо!\n\n"
            text += "При удалении будут удалены:\n"
            text += f"• {topic['question_count']} вопросов\n"
            text += "• Все результаты тестов по этой теме\n"
            text += "• Все связанные данные\n\n"
            text += "Вы уверены, что хотите удалить эту тему?"
            
            keyboard = [
                [InlineKeyboardButton("❌ ДА, УДАЛИТЬ", callback_data=f"remove_topic_execute_{topic_id}")],
                [InlineKeyboardButton("🔙 Отмена", callback_data="remove_topic")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при выборе темы для удаления.")

    async def remove_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('remove_topic_execute_', ''))
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            topic_name = topic['name']
            question_count = topic['question_count']
            
            # Удаляем тему и все связанные данные
            success = self.db.delete_topic_completely(topic_id)
            
            if success:
                text = f"✅ <b>Тема успешно удалена!</b>\n\n"
                text += f"<b>Удалена тема:</b> {topic_name}\n"
                text += f"<b>Удалено вопросов:</b> {question_count}\n"
                text += f"<b>Удалены:</b> все результаты тестов и связанные данные\n\n"
                text += "📚 <b>Управление темами</b>\n\nВыберите действие:"
                
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
                    [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
                    [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic_start")],
                    [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
                    [InlineKeyboardButton("📊 Статистика тем", callback_data="detailed_topics_stats")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
                ]
            else:
                text = f"❌ <b>Ошибка при удалении темы</b>\n\n"
                text += f"Не удалось удалить тему '{topic_name}'. Попробуйте еще раз."
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"remove_topic_confirm_{topic_id}")],
                    [InlineKeyboardButton("🔙 К списку тем", callback_data="remove_topic")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при удалении темы.")

    async def detailed_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Детальная статистика по темам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем статистику по темам
                cursor.execute('''
                    SELECT 
                        s.name as topic_name,
                        s.main_topic,
                        s.is_active,
                        COUNT(q.id) as question_count,
                        COUNT(DISTINCT tr.user_id) as unique_users,
                        COUNT(tr.id) as total_tests,
                        ROUND(AVG(tr.score), 1) as avg_score
                    FROM subtopics s
                    LEFT JOIN questions q ON s.name = q.topic
                    LEFT JOIN test_results tr ON s.name = tr.topic
                    GROUP BY s.name, s.main_topic, s.is_active
                    ORDER BY s.main_topic, s.name
                ''')
                
                stats = cursor.fetchall()
                
                if not stats:
                    text = "📊 <b>Детальная статистика тем</b>\n\nДанных нет."
                else:
                    text = "📊 <b>Детальная статистика тем</b>\n\n"
                    
                    # Группируем по разделам
                    current_section = None
                    total_questions = 0
                    total_tests = 0
                    
                    for stat in stats:
                        topic_name, main_topic, is_active, question_count, unique_users, total_tests_topic, avg_score = stat
                        
                        if main_topic != current_section:
                            if current_section is not None:
                                text += "\n"
                            text += f"📚 <b>{main_topic or 'Без раздела'}</b>\n"
                            current_section = main_topic
                        
                        status = "✅" if is_active else "❌"
                        text += f"  {status} <b>{topic_name}</b>\n"
                        text += f"    • Вопросов: {question_count}\n"
                        text += f"    • Уникальных пользователей: {unique_users}\n"
                        text += f"    • Всего тестов: {total_tests_topic}\n"
                        if avg_score:
                            text += f"    • Средний балл: {avg_score}%\n"
                        text += "\n"
                        
                        total_questions += question_count
                        total_tests += total_tests_topic
                    
                    text += f"📈 <b>Общая статистика:</b>\n"
                    text += f"• Всего вопросов: {total_questions}\n"
                    text += f"• Всего тестов: {total_tests}\n"
                
        except Exception as e:
            logging.error(f"Error getting topics stats: {e}")
            text = "❌ Ошибка при получении статистики."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="detailed_topics_stats")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def refresh_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обновить статистику тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Просто перенаправляем на список тем для обновления
        await self.list_topics(update, context)

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def add_base_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления базовых тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления базовых тем в разработке...")

    async def add_base_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение добавления базовой темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения добавления базовой темы в разработке...")

    async def add_all_missing_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Добавление всех отсутствующих тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления всех отсутствующих тем в разработке...")

    async def remove_topic_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления темы в разработке...")

    async def remove_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления темы в разработке...")

    async def remove_topic_permanent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Постоянное удаление темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция постоянного удаления темы в разработке...")

    async def remove_topic_permanent_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение постоянного удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения постоянного удаления темы в разработке...") 