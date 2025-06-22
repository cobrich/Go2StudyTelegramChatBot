"""
Модуль для управления админами в админ-панели.
Включает добавление, просмотр, удаление админов.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging

class AdminsHandler(AdminBaseHandler):
    """Обработчик для управления админами."""

    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        user_id = update.effective_user.id
        
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только для суперадминистратора.")
            return
        
        text = f"👑 <b>Управление администраторами</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = update.effective_user.id
        
        # Проверяем, что пользователь является суперадмином
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может добавлять админов.")
            return
        
        context.user_data['admin_action'] = 'add_admin'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "➕ <b>Добавление обычного администратора</b>\n\n"
        text += "👨‍💼 <b>Права обычного администратора:</b>\n"
        text += "• Управление учениками\n"
        text += "• Управление темами\n"
        text += "• Управление вопросами\n"
        text += "• Просмотр статистики\n\n"
        text += "ℹ️ <i>Для добавления суперадминистратора используйте скрипт init_superadmin.py</i>\n\n"
        text += "Введите Telegram user_id нового администратора:"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        admins = self.db.get_all_admins()
        
        if not admins:
            text = "👑 <b>Список администраторов</b>\n\nАдминистраторы не найдены."
        else:
            text = "👑 <b>Список администраторов</b>\n\n"
            for i, admin in enumerate(admins, 1):
                role = "👑 Суперадмин" if admin['is_super_admin'] else "👨‍💼 Админ"
                text += f"{i}. {role}\n"
                text += f"   ID: {admin['user_id']}\n"
                text += f"   Username: @{admin['username']}\n"
                text += f"   Имя: {admin['full_name']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления админа (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = update.effective_user.id
        
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        admins = self.db.get_all_admins()
        current_admin_id = user_id
        
        # Фильтруем список: убираем суперадминов и текущего пользователя
        removable_admins = [admin for admin in admins if not admin['is_super_admin'] and admin['user_id'] != current_admin_id]
        
        if not removable_admins:
            text = "🗑️ <b>Удаление администратора</b>\n\nНет администраторов, которых можно удалить.\n\n"
            text += "ℹ️ <i>Суперадминистратор не может удалить себя или других суперадминистраторов.</i>"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]]
        else:
            text = "🗑️ <b>Удаление администратора</b>\n\nВыберите администратора для удаления:\n\n"
            text += "⚠️ <i>Можно удалить только обычных админов</i>\n\n"
            keyboard = []
            
            for admin in removable_admins:
                display_text = f"👨‍💼 @{admin['username']} - {admin['full_name']}"
                keyboard.append([InlineKeyboardButton(
                    display_text,
                    callback_data=f"remove_admin_confirm_{admin['user_id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления админа."""
        query = update.callback_query
        admin_id_to_remove = int(query.data.replace('remove_admin_confirm_', ''))
        await self.safe_answer_callback(query)
        
        current_user_id = update.effective_user.id
        
        # Дополнительная проверка прав
        if not self.db.is_super_admin(current_user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        # Получаем информацию об админе
        admins = self.db.get_all_admins()
        admin_to_remove = next((admin for admin in admins if admin['user_id'] == admin_id_to_remove), None)
        
        if not admin_to_remove:
            await query.edit_message_text(
                "❌ Администратор не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]])
            )
            return
        
        # Проверяем, что не пытаемся удалить суперадмина или себя
        if admin_to_remove['is_super_admin']:
            await query.edit_message_text(
                "❌ Нельзя удалить суперадминистратора.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="remove_admin")]])
            )
            return
        
        if admin_id_to_remove == current_user_id:
            await query.edit_message_text(
                "❌ Нельзя удалить самого себя.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="remove_admin")]])
            )
            return
        
        text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
        text += f"<b>Администратор:</b> @{admin_to_remove['username']}\n"
        text += f"<b>Имя:</b> {admin_to_remove['full_name']}\n"
        text += f"<b>ID:</b> {admin_to_remove['user_id']}\n"
        text += f"<b>Роль:</b> {'👑 Суперадмин' if admin_to_remove['is_super_admin'] else '👨‍💼 Админ'}\n\n"
        text += "⚠️ <b>ВНИМАНИЕ:</b> Это действие нельзя отменить!\n"
        text += "Пользователь потеряет права администратора.\n\n"
        text += "Подтвердите удаление:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"remove_admin_execute_{admin_id_to_remove}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="remove_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления админа."""
        query = update.callback_query
        admin_id_to_remove = int(query.data.replace('remove_admin_execute_', ''))
        await self.safe_answer_callback(query)
        
        current_user_id = update.effective_user.id
        
        # Финальная проверка прав
        if not self.db.is_super_admin(current_user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        # Получаем информацию об админе перед удалением
        admins = self.db.get_all_admins()
        admin_to_remove = next((admin for admin in admins if admin['user_id'] == admin_id_to_remove), None)
        
        if not admin_to_remove:
            await query.edit_message_text(
                "❌ Администратор не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]])
            )
            return
        
        # Финальные проверки безопасности
        if admin_to_remove['is_super_admin'] or admin_id_to_remove == current_user_id:
            await query.edit_message_text(
                "❌ Операция запрещена по соображениям безопасности.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]])
            )
            return
        
        # Выполняем удаление
        try:
            success = self.db.remove_admin(admin_id_to_remove)
            
            if success:
                text = f"✅ <b>Администратор успешно удален</b>\n\n"
                text += f"<b>Удаленный администратор:</b>\n"
                text += f"• Username: @{admin_to_remove['username']}\n"
                text += f"• Имя: {admin_to_remove['full_name']}\n"
                text += f"• ID: {admin_to_remove['user_id']}\n\n"
                text += f"Пользователь больше не имеет прав администратора."
                
                logging.info(f"Admin {current_user_id} removed admin {admin_id_to_remove} (@{admin_to_remove['username']})")
            else:
                text = f"❌ <b>Ошибка при удалении администратора</b>\n\n"
                text += f"Не удалось удалить администратора из базы данных.\n"
                text += f"Попробуйте еще раз или обратитесь к разработчику."
                
                logging.error(f"Failed to remove admin {admin_id_to_remove} by admin {current_user_id}")
                
        except Exception as e:
            text = f"❌ <b>Ошибка при удалении администратора</b>\n\n"
            text += f"Произошла ошибка: {str(e)}\n"
            text += f"Обратитесь к разработчику."
            
            logging.error(f"Exception while removing admin {admin_id_to_remove} by admin {current_user_id}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к управлению админами", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ АДМИНОВ ===

    async def handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления админа."""
        try:
            new_admin_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Введите числовой Telegram ID:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]])
            )
            return
        
        current_user_id = update.effective_user.id
        
        # Проверяем права
        if not self.db.is_super_admin(current_user_id):
            await update.message.reply_text("❌ Доступ запрещен. Только суперадминистратор может добавлять админов.")
            return
        
        # Проверяем, не является ли пользователь уже админом
        if self.db.is_admin(new_admin_id):
            await update.message.reply_text(
                f"❌ Пользователь с ID {new_admin_id} уже является администратором.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]])
            )
            return
        
        # Сохраняем ID и переходим к запросу username
        context.user_data['new_admin_id'] = new_admin_id
        context.user_data['admin_action'] = 'add_admin_username'
        
        text = f"➕ <b>Добавление администратора</b>\n\n"
        text += f"<b>ID:</b> {new_admin_id}\n\n"
        text += f"Теперь введите username нового администратора (без @):"
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]]),
            parse_mode='HTML'
        )

    async def handle_add_admin_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка username админа."""
        # Убираем @ если есть
        username = username.lstrip('@')
        
        if not username:
            await update.message.reply_text(
                "❌ Username не может быть пустым. Введите username:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]])
            )
            return
        
        # Сохраняем username и переходим к запросу ФИО
        context.user_data['new_admin_username'] = username
        context.user_data['admin_action'] = 'add_admin_fullname'
        
        new_admin_id = context.user_data.get('new_admin_id')
        
        text = f"➕ <b>Добавление администратора</b>\n\n"
        text += f"<b>ID:</b> {new_admin_id}\n"
        text += f"<b>Username:</b> @{username}\n\n"
        text += f"Теперь введите полное имя администратора:"
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]]),
            parse_mode='HTML'
        )

    async def handle_add_admin_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка ФИО админа."""
        if not fullname.strip():
            await update.message.reply_text(
                "❌ Имя не может быть пустым. Введите полное имя:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_admins")]])
            )
            return
        
        current_user_id = update.effective_user.id
        new_admin_id = context.user_data.get('new_admin_id')
        new_admin_username = context.user_data.get('new_admin_username')
        
        # Финальная проверка прав
        if not self.db.is_super_admin(current_user_id):
            await update.message.reply_text("❌ Доступ запрещен. Только суперадминистратор может добавлять админов.")
            return
        
        # Проверяем еще раз, что пользователь не стал админом за время заполнения формы
        if self.db.is_admin(new_admin_id):
            await update.message.reply_text(
                f"❌ Пользователь с ID {new_admin_id} уже является администратором.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]])
            )
            return
        
        # Добавляем админа
        try:
            success = self.db.add_admin(
                user_id=new_admin_id,
                username=new_admin_username,
                full_name=fullname.strip(),
                is_super_admin=False,  # Обычный админ
                created_by=current_user_id
            )
            
            if success:
                text = f"✅ <b>Администратор успешно добавлен!</b>\n\n"
                text += f"<b>Новый администратор:</b>\n"
                text += f"• ID: {new_admin_id}\n"
                text += f"• Username: @{new_admin_username}\n"
                text += f"• Имя: {fullname.strip()}\n"
                text += f"• Роль: 👨‍💼 Обычный админ\n\n"
                text += f"<b>Права администратора:</b>\n"
                text += f"• Управление учениками\n"
                text += f"• Управление темами\n"
                text += f"• Управление вопросами\n"
                text += f"• Просмотр статистики\n\n"
                text += f"Пользователь может использовать команду /admin для доступа к панели."
                
                logging.info(f"Admin {current_user_id} added new admin {new_admin_id} (@{new_admin_username})")
            else:
                text = f"❌ <b>Ошибка при добавлении администратора</b>\n\n"
                text += f"Не удалось добавить администратора в базу данных.\n"
                text += f"Возможно, пользователь уже является админом или произошла ошибка.\n"
                text += f"Попробуйте еще раз."
                
                logging.error(f"Failed to add admin {new_admin_id} by admin {current_user_id}")
                
        except Exception as e:
            text = f"❌ <b>Ошибка при добавлении администратора</b>\n\n"
            text += f"Произошла ошибка: {str(e)}\n"
            text += f"Обратитесь к разработчику."
            
            logging.error(f"Exception while adding admin {new_admin_id} by admin {current_user_id}: {e}")
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_admin_id', None)
        context.user_data.pop('new_admin_username', None)
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к управлению админами", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML') 