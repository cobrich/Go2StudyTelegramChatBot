import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

# Импортируем фасад базы данных
from src.services.database import get_database_instance

logger = logging.getLogger(__name__)

class MessageManager:
    """
    Класс для управления "ключевыми" сообщениями в интерфейсе.
    Отвечает за удаление старых версий сообщений перед отправкой новых.
    """
    def __init__(self, db_facade=None):
        self.db = db_facade or get_database_instance()

    async def send_managed_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        message_type: str,
        reply_markup: InlineKeyboardMarkup = None,
        **kwargs,
    ):
        """
        Отправляет или редактирует "управляемое" сообщение.
        Если возможно, редактирует существующее сообщение, иначе удаляет старое и отправляет новое.

        :param update: Объект Update от Telegram.
        :param context: Контекст от python-telegram-bot.
        :param text: Текст нового сообщения.
        :param message_type: Уникальный тип сообщения ('main_menu', 'progress_summary', etc.).
        :param reply_markup: Клавиатура для сообщения.
        :param kwargs: Дополнительные аргументы для send_message/edit_message_text (например, parse_mode).
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        query = update.callback_query

        # Попытка отредактировать сообщение, если это ответ на callback
        if query:
            try:
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    **kwargs
                )
                # Если редактирование успешно, мы просто выходим,
                # так как message_id и chat_id не изменились.
                logger.info(f"Отредактировано управляемое сообщение (type: {message_type}) для user_id: {user_id}")
                return
            except BadRequest as e:
                # Ошибка может возникнуть, если текст сообщения не изменился
                if "Message is not modified" in str(e):
                    logger.info("Сообщение не изменено, пропуск редактирования.")
                    await query.answer() # Отвечаем на колбэк, чтобы убрать "часики"
                    return
                # Если другая ошибка, мы продолжим и отправим новое сообщение
                logger.warning(f"Не удалось отредактировать сообщение, будет отправлено новое. Ошибка: {e}")

        # Если это не callback или редактирование не удалось, удаляем старое и отправляем новое.
        old_message = self.db.get_managed_message(user_id, message_type)
        if old_message:
            try:
                await context.bot.delete_message(
                    chat_id=old_message['chat_id'],
                    message_id=old_message['message_id']
                )
                logger.info(f"Удалено старое сообщение (type: {message_type}) для user_id: {user_id}")
            except BadRequest as e:
                logger.warning(f"Не удалось удалить сообщение (id: {old_message['message_id']}): {e}")
        
        # Отправляем новое сообщение
        new_message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            **kwargs,
        )
        
        # Сохраняем информацию о новом сообщении в БД
        self.db.upsert_managed_message(
            user_id=user_id,
            chat_id=chat_id,
            message_id=new_message.message_id,
            message_type=message_type,
        )
        logger.info(f"Отправлено и сохранено новое управляемое сообщение (type: {message_type}) для user_id: {user_id}") 