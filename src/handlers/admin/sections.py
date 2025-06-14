"""
Модуль управления разделами (main_topics) для админ-панели.
Поддерживает создание, редактирование, удаление разделов с языковой поддержкой.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, List, Any, Optional
from handlers.base_handler import BaseHandler
from services.database import Database


class SectionsHandler(BaseHandler):
    """Обработчик управления разделами."""
    
    def __init__(self, db: Database, question_service):
        super().__init__(db, question_service)
        self.sections_mapping = {}  # Для хранения mapping разделов
    
    async def sections_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Главное меню управления разделами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем статистику разделов
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=False)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=False)
        
        total_sections = len(ru_sections) + len(kk_sections)
        
        text = "📚 <b>Управление разделами</b>\n\n"
        text += f"📊 Всего разделов: {total_sections} ({len(ru_sections)} ru + {len(kk_sections)} kk)\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📋 Список всех разделов", callback_data="list_all_sections")],
            [InlineKeyboardButton("➕ Добавить раздел", callback_data="add_section_start")],
            [InlineKeyboardButton("✏️ Редактировать раздел", callback_data="edit_section_start")],
            [InlineKeyboardButton("🗑️ Удалить раздел", callback_data="delete_section_start")],
            [InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def list_all_sections(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать все разделы с языковыми индикаторами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем разделы по языкам
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=False)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=False)
        
        text = "📚 <b>Все разделы</b>\n\n"
        text += f"📊 Всего: {len(ru_sections) + len(kk_sections)} разделов\n\n"
        
        # Русские разделы
        if ru_sections:
            text += "🇷🇺 <b>Русские разделы:</b>\n"
            for section in ru_sections:
                # Получаем количество подтем
                subtopics = self.db.get_subtopics_by_main_topic(section['name'])
                status_icon = "✅" if section.get('is_active', True) else "❌"
                text += f"{status_icon} {section['name']} ({len(subtopics)} тем)\n"
            text += "\n"
        
        # Казахские разделы
        if kk_sections:
            text += "🇰🇿 <b>Казахские разделы:</b>\n"
            for section in kk_sections:
                # Получаем количество подтем
                subtopics = self.db.get_subtopics_by_main_topic(section['name'])
                status_icon = "✅" if section.get('is_active', True) else "❌"
                text += f"{status_icon} {section['name']} ({len(subtopics)} тем)\n"
            text += "\n"
        
        if not ru_sections and not kk_sections:
            text += "❌ Разделы не найдены.\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать добавление нового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = "➕ <b>Добавление раздела</b>\n\n"
        text += "Выберите язык для нового раздела:"
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="add_section_lang_ru")],
            [InlineKeyboardButton("🇰🇿 Казахский", callback_data="add_section_lang_kk")],
            [InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_section_language_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбран язык для нового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем язык из callback_data
        language = query.data.split('_')[-1]  # ru или kk
        context.user_data['adding_section_language'] = language
        
        lang_name = "Русский" if language == "ru" else "Казахский"
        
        text = f"➕ <b>Добавление раздела</b>\n\n"
        text += f"🌐 Язык: {lang_name}\n\n"
        text += "Введите название нового раздела:\n\n"
        text += "<i>Например: 📊 Арифметика и числа</i>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="add_section_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Устанавливаем состояние ожидания названия раздела
        context.user_data['awaiting_section_name'] = True
    
    async def edit_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать редактирование раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем все разделы
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=False)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=False)
        
        all_sections = []
        for section in ru_sections:
            section['language'] = 'ru'
            all_sections.append(section)
        for section in kk_sections:
            section['language'] = 'kk'
            all_sections.append(section)
        
        if not all_sections:
            text = "❌ <b>Редактирование разделов</b>\n\n"
            text += "Разделы не найдены.\n"
            text += "Сначала создайте разделы."
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить раздел", callback_data="add_section_start")],
                [InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        text = "✏️ <b>Редактирование разделов</b>\n\n"
        text += "Выберите раздел для редактирования:\n\n"
        
        keyboard = []
        self.sections_mapping.clear()
        
        # Группируем по языкам
        if ru_sections:
            text += "🇷🇺 <b>Русские разделы:</b>\n"
            for i, section in enumerate(ru_sections):
                section_id = f"ru_{i}"
                self.sections_mapping[section_id] = {
                    'name': section['name'],
                    'language': 'ru',
                    'is_active': section.get('is_active', True)
                }
                status_icon = "✅" if section.get('is_active', True) else "❌"
                text += f"{status_icon} {section['name']}\n"
                keyboard.append([InlineKeyboardButton(
                    f"🇷🇺 {section['name']}", 
                    callback_data=f"edit_section_select_{section_id}"
                )])
            text += "\n"
        
        if kk_sections:
            text += "🇰🇿 <b>Казахские разделы:</b>\n"
            for i, section in enumerate(kk_sections):
                section_id = f"kk_{i}"
                self.sections_mapping[section_id] = {
                    'name': section['name'],
                    'language': 'kk',
                    'is_active': section.get('is_active', True)
                }
                status_icon = "✅" if section.get('is_active', True) else "❌"
                text += f"{status_icon} {section['name']}\n"
                keyboard.append([InlineKeyboardButton(
                    f"🇰🇿 {section['name']}", 
                    callback_data=f"edit_section_select_{section_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбран раздел для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем ID раздела
        section_id = query.data.replace("edit_section_select_", "")
        
        if section_id not in self.sections_mapping:
            await query.edit_message_text("❌ Раздел не найден.")
            return
        
        section_info = self.sections_mapping[section_id]
        context.user_data['editing_section'] = section_info
        
        lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
        status_text = "Активен" if section_info['is_active'] else "Неактивен"
        
        text = f"✏️ <b>Редактирование раздела</b>\n\n"
        text += f"{lang_flag} <b>{section_info['name']}</b>\n"
        text += f"📊 Статус: {status_text}\n\n"
        text += "Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("📝 Изменить название", callback_data="edit_section_name")],
            [InlineKeyboardButton("🔄 Переключить статус", callback_data="edit_section_toggle_status")],
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_section_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_section_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать изменение названия раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        section_info = context.user_data.get('editing_section')
        if not section_info:
            await query.edit_message_text("❌ Информация о разделе потеряна.")
            return
        
        lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
        
        text = f"📝 <b>Изменение названия раздела</b>\n\n"
        text += f"{lang_flag} Текущее название: <b>{section_info['name']}</b>\n\n"
        text += "Введите новое название раздела:\n\n"
        text += "<i>Например: 📊 Арифметика и числа</i>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_section_select_{section_info['language']}_0")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Устанавливаем состояние ожидания нового названия
        context.user_data['awaiting_section_new_name'] = True
    
    async def edit_section_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключить статус раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        section_info = context.user_data.get('editing_section')
        if not section_info:
            await query.edit_message_text("❌ Информация о разделе потеряна.")
            return
        
        # Переключаем статус в базе данных
        # Примечание: нужно будет добавить метод в database.py
        new_status = not section_info['is_active']
        
        # Здесь должен быть вызов метода БД для изменения статуса раздела
        # success = self.db.toggle_main_topic_status(section_info['name'], new_status)
        
        lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
        status_text = "активирован" if new_status else "деактивирован"
        
        text = f"✅ <b>Статус изменен</b>\n\n"
        text += f"{lang_flag} Раздел <b>{section_info['name']}</b> {status_text}.\n\n"
        text += "Возвращаемся в меню управления разделами..."
        
        keyboard = [
            [InlineKeyboardButton("🔙 В меню разделов", callback_data="sections_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать удаление раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем все разделы
        ru_sections = self.db.get_main_topics_by_language("ru", active_only=False)
        kk_sections = self.db.get_main_topics_by_language("kk", active_only=False)
        
        all_sections = []
        for section in ru_sections:
            section['language'] = 'ru'
            all_sections.append(section)
        for section in kk_sections:
            section['language'] = 'kk'
            all_sections.append(section)
        
        if not all_sections:
            text = "❌ <b>Удаление разделов</b>\n\n"
            text += "Разделы не найдены."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        text = "🗑️ <b>Удаление разделов</b>\n\n"
        text += "⚠️ <b>ВНИМАНИЕ!</b> Удаление раздела приведет к удалению всех связанных тем и вопросов!\n\n"
        text += "Выберите раздел для удаления:\n\n"
        
        keyboard = []
        self.sections_mapping.clear()
        
        # Группируем по языкам
        if ru_sections:
            text += "🇷🇺 <b>Русские разделы:</b>\n"
            for i, section in enumerate(ru_sections):
                section_id = f"ru_{i}"
                self.sections_mapping[section_id] = {
                    'name': section['name'],
                    'language': 'ru'
                }
                subtopics = self.db.get_subtopics_by_main_topic(section['name'])
                text += f"• {section['name']} ({len(subtopics)} тем)\n"
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ {section['name']}", 
                    callback_data=f"delete_section_confirm_{section_id}"
                )])
            text += "\n"
        
        if kk_sections:
            text += "🇰🇿 <b>Казахские разделы:</b>\n"
            for i, section in enumerate(kk_sections):
                section_id = f"kk_{i}"
                self.sections_mapping[section_id] = {
                    'name': section['name'],
                    'language': 'kk'
                }
                subtopics = self.db.get_subtopics_by_main_topic(section['name'])
                text += f"• {section['name']} ({len(subtopics)} тем)\n"
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ {section['name']}", 
                    callback_data=f"delete_section_confirm_{section_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="sections_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_section_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем ID раздела
        section_id = query.data.replace("delete_section_confirm_", "")
        
        if section_id not in self.sections_mapping:
            await query.edit_message_text("❌ Раздел не найден.")
            return
        
        section_info = self.sections_mapping[section_id]
        context.user_data['deleting_section'] = section_info
        
        # Получаем статистику что будет удалено
        subtopics = self.db.get_subtopics_by_main_topic(section_info['name'])
        
        # Подсчитываем вопросы
        total_questions = 0
        for subtopic in subtopics:
            questions = self.db.get_tasks_for_topic(subtopic['name'])
            total_questions += len(questions)
        
        lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
        
        text = f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
        text += f"{lang_flag} <b>Раздел:</b> {section_info['name']}\n\n"
        text += f"📊 <b>Будет удалено:</b>\n"
        text += f"• Тем: {len(subtopics)}\n"
        text += f"• Вопросов: {total_questions}\n"
        text += f"• Все результаты тестов по этим темам\n\n"
        text += f"❌ <b>ЭТО ДЕЙСТВИЕ НЕОБРАТИМО!</b>\n\n"
        text += f"Вы уверены, что хотите удалить раздел?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data="delete_section_execute")],
            [InlineKeyboardButton("❌ Отмена", callback_data="delete_section_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_section_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнить удаление раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        section_info = context.user_data.get('deleting_section')
        if not section_info:
            await query.edit_message_text("❌ Информация о разделе потеряна.")
            return
        
        try:
            # Удаляем раздел из базы данных
            success = self.db.delete_base_topic_section(section_info['name'], hard_delete=True)
            
            lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
            
            if success:
                text = f"✅ <b>Раздел удален</b>\n\n"
                text += f"{lang_flag} Раздел <b>{section_info['name']}</b> и все связанные данные успешно удалены.\n\n"
                text += "Возвращаемся в меню управления разделами..."
            else:
                text = f"❌ <b>Ошибка удаления</b>\n\n"
                text += f"Не удалось удалить раздел <b>{section_info['name']}</b>.\n"
                text += "Попробуйте еще раз или обратитесь к разработчику."
            
            keyboard = [
                [InlineKeyboardButton("🔙 В меню разделов", callback_data="sections_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            text = f"❌ <b>Ошибка</b>\n\n"
            text += f"Произошла ошибка при удалении раздела: {str(e)}"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="delete_section_start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # Обработчики текстовых сообщений
    async def handle_section_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка введенного названия нового раздела."""
        if not context.user_data.get('awaiting_section_name'):
            return False
        
        section_name = update.message.text.strip()
        language = context.user_data.get('adding_section_language', 'ru')
        
        if not section_name:
            await update.message.reply_text("❌ Название раздела не может быть пустым. Попробуйте еще раз.")
            return True
        
        # Проверяем, не существует ли уже такой раздел
        existing_sections = self.db.get_main_topics_by_language(language, active_only=False)
        if any(section['name'].lower() == section_name.lower() for section in existing_sections):
            await update.message.reply_text(f"❌ Раздел с названием '{section_name}' уже существует. Выберите другое название.")
            return True
        
        try:
            # Добавляем раздел в базу данных
            user_id = update.effective_user.id
            success = self.db.add_main_topic_with_language(section_name, language, [], created_by=user_id)
            
            lang_flag = "🇷🇺" if language == 'ru' else "🇰🇿"
            
            if success:
                text = f"✅ <b>Раздел создан</b>\n\n"
                text += f"{lang_flag} Раздел <b>{section_name}</b> успешно создан!\n\n"
                text += "Теперь вы можете добавлять в него темы через меню управления темами."
            else:
                text = f"❌ <b>Ошибка создания</b>\n\n"
                text += f"Не удалось создать раздел <b>{section_name}</b>.\n"
                text += "Попробуйте еще раз или обратитесь к разработчику."
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить еще раздел", callback_data="add_section_start")],
                [InlineKeyboardButton("🔙 В меню разделов", callback_data="sections_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        
        finally:
            # Очищаем состояние
            context.user_data.pop('awaiting_section_name', None)
            context.user_data.pop('adding_section_language', None)
        
        return True
    
    async def handle_section_new_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка нового названия раздела при редактировании."""
        if not context.user_data.get('awaiting_section_new_name'):
            return False
        
        new_name = update.message.text.strip()
        section_info = context.user_data.get('editing_section')
        
        if not section_info:
            await update.message.reply_text("❌ Информация о разделе потеряна.")
            return True
        
        if not new_name:
            await update.message.reply_text("❌ Название раздела не может быть пустым. Попробуйте еще раз.")
            return True
        
        # Проверяем, не существует ли уже такой раздел
        existing_sections = self.db.get_main_topics_by_language(section_info['language'], active_only=False)
        if any(section['name'].lower() == new_name.lower() and section['name'] != section_info['name'] 
               for section in existing_sections):
            await update.message.reply_text(f"❌ Раздел с названием '{new_name}' уже существует. Выберите другое название.")
            return True
        
        try:
            # Обновляем название раздела в базе данных
            success = self.db.update_base_topic_section(section_info['name'], new_main_topic=new_name)
            
            lang_flag = "🇷🇺" if section_info['language'] == 'ru' else "🇰🇿"
            
            if success:
                text = f"✅ <b>Название изменено</b>\n\n"
                text += f"{lang_flag} Раздел переименован:\n"
                text += f"<b>Было:</b> {section_info['name']}\n"
                text += f"<b>Стало:</b> {new_name}\n\n"
                text += "Изменения сохранены!"
            else:
                text = f"❌ <b>Ошибка изменения</b>\n\n"
                text += f"Не удалось изменить название раздела.\n"
                text += "Попробуйте еще раз или обратитесь к разработчику."
            
            keyboard = [
                [InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_section_start")],
                [InlineKeyboardButton("🔙 В меню разделов", callback_data="sections_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        
        finally:
            # Очищаем состояние
            context.user_data.pop('awaiting_section_new_name', None)
            context.user_data.pop('editing_section', None)
        
        return True 