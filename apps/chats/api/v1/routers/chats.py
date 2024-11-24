import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select  # Для асинхронных запросов
from apps.chats.models.chats import ChatMessageInDB
from apps.db import get_session  # Сессия базы данных
from apps.core.config import settings
from apps.mq.consumer import message_buffer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f'/{settings.chats_settings.service_name}/api/v1',
)

setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'chats')

# Новый роут для получения истории сообщений
@router.get("/{channel_name}/history", response_model=List[ChatMessageInDB])
async def get_chat_history(channel_name: str, session: AsyncSession = Depends(get_session)):
    """
    Получает полную историю сообщений чата, включая сообщения из базы данных и из буфера.
    Возвращает список объектов ChatMessageInDB.
    """
    try:
        # Сначала получаем все старые сообщения из базы данных, упорядоченные по sequence_number
        stmt = select(ChatMessageInDB).filter(ChatMessageInDB.channel == channel_name).order_by(ChatMessageInDB.sequence_number)
        result = await session.execute(stmt)

        # Получаем все сообщения из базы данных
        history = result.scalars().all()

        # Добавляем к ним сообщения из буфера
        global message_buffer  # Если message_buffer является глобальной переменной
        for msg in message_buffer:
            if msg["channel"] == channel_name:
                history.append(ChatMessageInDB(
                    action=msg["action"],
                    username=msg["username"],
                    channel=msg["channel"],
                    time=datetime.fromisoformat(msg["time"]).replace(tzinfo=timezone.utc),
                    sequence_number=msg["sequence_number"],
                    message=msg.get("message") or "No message",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat()
                ))

        # Упорядочиваем все сообщения по sequence_number
        history.sort(key=lambda x: x.sequence_number)

        return history

    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


