import logging
from typing import Optional
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncManagedMessageRepository(SyncBaseRepository):

    def get(self, user_id: int, message_type: str) -> Optional[dict]:
        """
        Получает информацию об управляемом сообщении по его типу.
        """
        try:
            query = """
                SELECT chat_id, message_id
                FROM managed_messages
                WHERE user_id = %s AND message_type = %s
            """
            result = self.fetch_one(query, (user_id, message_type))
            return result
        except Exception as e:
            logger.error(
                f"Ошибка при получении управляемого сообщения для user_id {user_id} и type {message_type}: {e}",
                exc_info=True
            )
            return None

    def upsert(self, data: dict):
        """
        Создает или обновляет запись об управляемом сообщении.
        """
        try:
            query = """
                INSERT INTO managed_messages (user_id, chat_id, message_id, message_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, message_type) DO UPDATE SET
                    chat_id = EXCLUDED.chat_id,
                    message_id = EXCLUDED.message_id,
                    created_at = CURRENT_TIMESTAMP;
            """
            params = (
                data['user_id'],
                data['chat_id'],
                data['message_id'],
                data['message_type'],
            )
            self.execute_query(query, params)
        except Exception as e:
            logger.error(f"Ошибка при 'upsert' управляемого сообщения: {e}", exc_info=True) 