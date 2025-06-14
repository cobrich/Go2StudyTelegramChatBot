"""
Модуль для управления админами в админ-панели.
Включает добавление, просмотр, удаление админов.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging

class AdminsHandler(AdminBaseHandler):
    """Обработчик для управления админами."""

    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"👨‍💼 <b>Управление админами</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"➕ <b>Добавление админа</b>\n\n"
        text += f"Введите Telegram ID пользователя, которого хотите сделать админом.\n\n"
        text += f"💡 <b>Как узнать ID:</b>\n"
        text += f"• Попросите пользователя написать команду /myid боту\n"
        text += f"• Или используйте @userinfobot\n\n"
        text += f"Введите ID:"
        
        context.user_data['admin_action'] = 'add_admin'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT a.user_id, a.username, a.full_name, a.added_date, a.added_by_admin_id,
                           admin_adder.full_name as added_by_name
                    FROM admins a
                    LEFT JOIN admins admin_adder ON a.added_by_admin_id = admin_adder.user_id
                    ORDER BY a.added_date DESC
                ''')
                admins = cursor.fetchall()
                
                if not admins:
                    text = "📋 <b>Список админов</b>\n\nАдмины не найдены."
                else:
                    text = f"📋 <b>Список админов</b>\n\n"
                    text += f"Всего админов: {len(admins)}\n\n"
                    
                    for i, admin in enumerate(admins, 1):
                        user_id, username, full_name, added_date, added_by_admin_id, added_by_name = admin
                        
                        text += f"{i}. <b>ID: {user_id}</b>\n"
                        if username:
                            text += f"   Username: @{username}\n"
                        if full_name:
                            text += f"   ФИО: {full_name}\n"
                        if added_date:
                            text += f"   Добавлен: {added_date[:10]}\n"
                        if added_by_name:
                            text += f"   Добавил: {added_by_name}\n"
                        text += "\n"
                
        except Exception as e:
            logging.error(f"Error getting admins list: {e}")
            text = "❌ Ошибка при получении списка админов."
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для удаления админа."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция удаления админов в разработке...")

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def remove_admin_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления админа."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления админа в разработке...")

    async def remove_admin_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления админа."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления админа в разработке...")

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ АДМИНОВ ===

    async def handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления админа."""
        await update.message.reply_text("🚧 Функция добавления админа в разработке...")

    async def handle_add_admin_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка username админа."""
        await update.message.reply_text("🚧 Функция обработки username админа в разработке...")

    async def handle_add_admin_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка ФИО админа."""
        await update.message.reply_text("🚧 Функция обработки ФИО админа в разработке...") 