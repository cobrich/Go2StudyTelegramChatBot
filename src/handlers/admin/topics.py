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
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы - сразу показываем выбор разделов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        # Получаем разделы для обоих языков (админ должен видеть все)
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=True)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=True)
        
        # Объединяем разделы с указанием языка (сначала казахские, потом русские)
        all_sections = []
        for section in kk_sections:
            section['language'] = 'kk'
            all_sections.append(section)
        for section in ru_sections:
            section['language'] = 'ru'
            all_sections.append(section)
        
        if not all_sections:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Основные разделы не найдены. Сначала создайте базовую структуру.", 
                                         reply_markup=reply_markup, parse_mode='HTML')
            return
        
        context.user_data['admin_action'] = 'select_main_topic_for_new'
        context.user_data['main_topics_list'] = all_sections
        
        text = "➕ <b>Добавление новой темы</b>\n\n"
        text += "Выберите раздел для новой темы:"
        
        keyboard = []
        
        # Сначала казахские разделы
        if kk_sections:
            for i, section in enumerate(kk_sections):
                keyboard.append([InlineKeyboardButton(
                    f"📚 {section['name']} [kz]",
                    callback_data=f"select_main_topic_{i}"
                )])
        
        # Затем русские разделы
        if ru_sections:
            kk_count = len(kk_sections)
            for i, section in enumerate(ru_sections):
                keyboard.append([InlineKeyboardButton(
                    f"📚 {section['name']} [ru]",
                    callback_data=f"select_main_topic_{kk_count + i}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

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
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

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
            
            keyboard.append([InlineKeyboardButton("🔙 Выбрать другой раздел", callback_data="add_topic")])
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
        """Обработка добавления темы."""
        selected_main_topic = context.user_data.get('selected_main_topic')
        selected_language = context.user_data.get('selected_main_topic_language')
        admin_id = update.effective_user.id
        
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

    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования темы - выбор раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем разделы для обоих языков (админ должен видеть все)
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=True)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=True)
        
        # Объединяем разделы с указанием языка (сначала казахские, потом русские)
        all_sections = []
        for section in kk_sections:
            section['language'] = 'kk'
            all_sections.append(section)
        for section in ru_sections:
            section['language'] = 'ru'
            all_sections.append(section)
        
        if not all_sections:
            text = "❌ <b>Редактирование тем</b>\n\nРазделы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = f"✏️ <b>Редактирование тем</b>\n\n"
            text += "Выберите раздел для редактирования тем:"
            
            # Сохраняем список разделов в контексте
            context.user_data['edit_sections_list'] = all_sections
            
            keyboard = []
            
            # Сначала казахские разделы
            if kk_sections:
                for i, section in enumerate(kk_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [kz] ({topics_count} тем)",
                        callback_data=f"edit_section_topics_{i}"
                    )])
            
            # Затем русские разделы
            if ru_sections:
                kk_count = len(kk_sections)
                for i, section in enumerate(ru_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [ru] ({topics_count} тем)",
                        callback_data=f"edit_section_topics_{kk_count + i}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать темы выбранного раздела для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('edit_section_topics_', ''))
            sections_list = context.user_data.get('edit_sections_list', [])
            
            if section_index >= len(sections_list):
                await query.edit_message_text("❌ Неверный выбор раздела.")
                return
            
            selected_section = sections_list[section_index]
            section_name = selected_section['name']
            section_language = selected_section['language']
            
            # Получаем все темы этого раздела
            topics = self.db.get_all_topics(active_only=False)
            section_topics = [t for t in topics if t.get('main_topic') == section_name]
            
            if not section_topics:
                text = f"✏️ <b>Редактирование тем</b>\n\n"
                text += f"📚 <b>Раздел:</b> {section_name} [{'kz' if section_language == 'kk' else 'ru'}]\n\n"
                text += "В этом разделе нет тем."
                keyboard = [[InlineKeyboardButton("🔙 К выбору раздела", callback_data="edit_topic_start")]]
            else:
                text = f"✏️ <b>Редактирование тем</b>\n\n"
                text += f"📚 <b>Раздел:</b> {section_name} [{'kz' if section_language == 'kk' else 'ru'}]\n\n"
                text += f"Выберите тему для редактирования ({len(section_topics)} тем):\n\n"
                
                keyboard = []
                for topic in section_topics:
                    status = "✅" if topic['is_active'] else "❌"
                    button_text = f"{status} {topic['name']} ({topic['question_count']} вопр.)"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"edit_topic_select_{topic['id']}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔙 К выбору раздела", callback_data="edit_topic_start")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при выборе раздела.")

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
            text += f"<b>Статус:</b> {status_emoji} {status}\n"
            text += f"<b>Вопросов:</b> {topic['question_count']}\n\n"
            text += "Выберите действие:"
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_topic_name_{topic_id}")],
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
            text += f"Текущее название: <b>{topic['name']}</b>\n\n"
            text += "Введите новое название темы:"
            
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_topic_select_{topic_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при редактировании темы.")

    async def edit_topic_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения раздела темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_section_', ''))
            print(f"[DEBUG] edit_topic_section_start: topic_id = {topic_id}")
            
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                print(f"[ERROR] Тема с ID {topic_id} не найдена")
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            print(f"[DEBUG] Найдена тема: {topic['name']}")
            
            # Получаем все разделы для обоих языков
            ru_sections = self.db.get_main_topics_by_language("ru", active_only=True)
            kk_sections = self.db.get_main_topics_by_language("kk", active_only=True)
            
            print(f"[DEBUG] Найдено разделов: ru={len(ru_sections)}, kk={len(kk_sections)}")
            
            # Объединяем разделы с указанием языка (сначала казахские, потом русские)
            all_sections = []
            for section in kk_sections:
                section['language'] = 'kk'
                all_sections.append(section)
            for section in ru_sections:
                section['language'] = 'ru'
                all_sections.append(section)
            
            if not all_sections:
                print(f"[ERROR] Разделы не найдены")
                text = "❌ Разделы не найдены."
                keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup)
                return
            
            # Сохраняем данные в контексте
            context.user_data['edit_topic_id'] = topic_id
            context.user_data['edit_sections_list'] = all_sections
            
            print(f"[DEBUG] Сохранены данные в context: topic_id={topic_id}, sections_count={len(all_sections)}")
            
            text = f"📚 <b>Изменение раздела темы</b>\n\n"
            text += f"Тема: <b>{topic['name']}</b>\n"
            text += f"Текущий раздел: <i>{topic.get('main_topic', 'Без раздела')}</i>\n\n"
            text += "Выберите новый раздел:"
            
            keyboard = []
            
            # Сначала казахские разделы
            if kk_sections:
                for i, section in enumerate(kk_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [kz] ({topics_count} тем)",
                        callback_data=f"edit_topic_section_select_{i}"
                    )])
            
            # Затем русские разделы
            if ru_sections:
                kk_count = len(kk_sections)
                for i, section in enumerate(ru_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [ru] ({topics_count} тем)",
                        callback_data=f"edit_topic_section_select_{kk_count + i}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
            print(f"[DEBUG] Сообщение отправлено, кнопок создано: {len(keyboard)}")
            
        except (ValueError, IndexError) as e:
            print(f"[ERROR] Ошибка в edit_topic_section_start: {e}")
            # Добавляем кнопку "Назад" даже при ошибке
            topic_id = context.user_data.get('edit_topic_id', 'unknown')
            text = "❌ Ошибка при редактировании темы."
            keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}" if topic_id != 'unknown' else "edit_topic_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception as e:
            print(f"[ERROR] Неожиданная ошибка в edit_topic_section_start: {e}")
            # Добавляем кнопку "Назад" даже при ошибке
            topic_id = context.user_data.get('edit_topic_id', 'unknown')
            text = "❌ Произошла неожиданная ошибка."
            keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}" if topic_id != 'unknown' else "edit_topic_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

    async def edit_topic_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор нового раздела для темы."""
        query = update.callback_query
        print(f"[DEBUG] edit_topic_section_select ВЫЗВАН! callback_data: {query.data}")
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('edit_topic_section_select_', ''))
            print(f"[DEBUG] edit_topic_section_select: section_index = {section_index}")
            
            sections_list = context.user_data.get('edit_sections_list', [])
            topic_id = context.user_data.get('edit_topic_id')
            
            print(f"[DEBUG] Данные из context: topic_id={topic_id}, sections_count={len(sections_list)}")
            
            if section_index >= len(sections_list) or not topic_id:
                print(f"[ERROR] Неверные данные: section_index={section_index}, sections_count={len(sections_list)}, topic_id={topic_id}")
                await query.edit_message_text("❌ Ошибка при выборе раздела.")
                return
            
            selected_section = sections_list[section_index]
            section_name = selected_section['name']
            
            print(f"[DEBUG] Выбран раздел: {section_name}")
            
            # Обновляем раздел темы в базе данных
            print(f"[DEBUG] Вызываем db.update_topic_section({topic_id}, '{section_name}')")
            success = self.db.update_topic_section(topic_id, section_name)
            print(f"[DEBUG] Результат update_topic_section: {success}")
            
            if success:
                text = f"✅ Раздел темы успешно изменен на '{section_name}'!"
            else:
                text = f"❌ Ошибка при изменении раздела темы."
            
            keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
            # Очищаем данные
            context.user_data.pop('edit_topic_id', None)
            context.user_data.pop('edit_sections_list', None)
            print(f"[DEBUG] Очищены данные context")
            
        except (ValueError, IndexError) as e:
            print(f"[ERROR] Ошибка в edit_topic_section_select: {e}")
            # Добавляем кнопку "Назад" даже при ошибке
            topic_id = context.user_data.get('edit_topic_id', 'unknown')
            text = "❌ Ошибка при выборе раздела."
            keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}" if topic_id != 'unknown' else "edit_topic_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception as e:
            print(f"[ERROR] Неожиданная ошибка в edit_topic_section_select: {e}")
            # Добавляем кнопку "Назад" даже при ошибке
            topic_id = context.user_data.get('edit_topic_id', 'unknown')
            text = "❌ Произошла неожиданная ошибка."
            keyboard = [[InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}" if topic_id != 'unknown' else "edit_topic_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

    async def edit_topic_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            topic_id = int(query.data.replace('edit_topic_toggle_', ''))
            
            # Получаем текущую информацию о теме
            topics = self.db.get_all_topics(active_only=False)
            topic = next((t for t in topics if t['id'] == topic_id), None)
            
            if not topic:
                await query.edit_message_text("❌ Тема не найдена.")
                return
            
            # Переключаем статус
            success = self.db.toggle_topic_status(topic_id)
            
            if success:
                # Получаем обновленную информацию о теме
                updated_topics = self.db.get_all_topics(active_only=False)
                updated_topic = next((t for t in updated_topics if t['id'] == topic_id), None)
                
                if updated_topic:
                    # Формируем обновленное сообщение для редактирования темы
                    status = "✅ Активна" if updated_topic['is_active'] else "❌ Неактивна"
                    status_action = "❌ Деактивировать" if updated_topic['is_active'] else "✅ Активировать"
                    
                    text = f"✏️ <b>Редактирование темы</b>\n\n"
                    text += f"📝 <b>Название:</b> {updated_topic['name']}\n"
                    text += f"📚 <b>Раздел:</b> {updated_topic.get('main_topic', 'Не указан')}\n"
                    text += f"📊 <b>Статус:</b> {status}\n"
                    text += f"❓ <b>Вопросов:</b> {updated_topic.get('question_count', 0)}\n\n"
                    text += f"✅ <b>Статус темы успешно изменен!</b>"
                    
                    keyboard = [
                        [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_topic_name_{topic_id}")],
                        [InlineKeyboardButton("📚 Изменить раздел", callback_data=f"edit_topic_section_{topic_id}")],
                        [InlineKeyboardButton(status_action, callback_data=f"edit_topic_toggle_{topic_id}")],
                        [InlineKeyboardButton("🔙 К списку тем", callback_data="edit_topic_start")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.edit_message_text("❌ Ошибка при получении обновленной информации о теме.")
            else:
                await query.edit_message_text("❌ Ошибка при изменении статуса темы.")
                
        except (ValueError, IndexError) as e:
            print(f"[ERROR] Ошибка в edit_topic_toggle_status: {e}")
            await query.edit_message_text("❌ Ошибка при изменении статуса темы.")
        except Exception as e:
            print(f"[ERROR] Неожиданная ошибка в edit_topic_toggle_status: {e}")
            await query.edit_message_text("❌ Произошла неожиданная ошибка.")

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

    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления темы - выбор раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем разделы для обоих языков (админ должен видеть все)
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=True)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=True)
        
        # Объединяем разделы с указанием языка (сначала казахские, потом русские)
        all_sections = []
        for section in kk_sections:
            section['language'] = 'kk'
            all_sections.append(section)
        for section in ru_sections:
            section['language'] = 'ru'
            all_sections.append(section)
        
        if not all_sections:
            text = "❌ <b>Удаление тем</b>\n\nРазделы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = f"🗑️ <b>Удаление тем</b>\n\n"
            text += "⚠️ <b>Внимание!</b> При удалении темы будут удалены:\n"
            text += "• Все вопросы в этой теме\n"
            text += "• Все результаты тестов по этой теме\n"
            text += "• Все ссылки на эти вопросы\n\n"
            text += "Выберите раздел для удаления тем:"
            
            # Сохраняем список разделов в контексте
            context.user_data['remove_sections_list'] = all_sections
            
            keyboard = []
            
            # Сначала казахские разделы
            if kk_sections:
                for i, section in enumerate(kk_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [kz] ({topics_count} тем)",
                        callback_data=f"remove_section_topics_{i}"
                    )])
            
            # Затем русские разделы
            if ru_sections:
                kk_count = len(kk_sections)
                for i, section in enumerate(ru_sections):
                    # Получаем количество тем в разделе
                    topics_count = len(self.db.get_subtopics_by_main_topic(section['name']))
                    keyboard.append([InlineKeyboardButton(
                        f"📚 {section['name']} [ru] ({topics_count} тем)",
                        callback_data=f"remove_section_topics_{kk_count + i}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать темы выбранного раздела для удаления."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('remove_section_topics_', ''))
            sections_list = context.user_data.get('remove_sections_list', [])
            
            if section_index >= len(sections_list):
                await query.edit_message_text("❌ Неверный выбор раздела.")
                return
            
            selected_section = sections_list[section_index]
            section_name = selected_section['name']
            section_language = selected_section['language']
            
            # Получаем все темы этого раздела
            topics = self.db.get_all_topics(active_only=False)
            section_topics = [t for t in topics if t.get('main_topic') == section_name]
            
            if not section_topics:
                text = f"🗑️ <b>Удаление тем</b>\n\n"
                text += f"📚 <b>Раздел:</b> {section_name} [{'kz' if section_language == 'kk' else 'ru'}]\n\n"
                text += "В этом разделе нет тем."
                keyboard = [[InlineKeyboardButton("🔙 К выбору раздела", callback_data="remove_topic_start")]]
            else:
                text = f"🗑️ <b>Удаление тем</b>\n\n"
                text += f"📚 <b>Раздел:</b> {section_name} [{'kz' if section_language == 'kk' else 'ru'}]\n\n"
                text += f"Выберите тему для удаления ({len(section_topics)} тем):\n\n"
                
                keyboard = []
                for topic in section_topics:
                    status = "✅" if topic['is_active'] else "❌"
                    button_text = f"{status} {topic['name']} ({topic['question_count']} вопр.)"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"remove_topic_confirm_{topic['id']}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔙 К выбору раздела", callback_data="remove_topic_start")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка при выборе раздела.")

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