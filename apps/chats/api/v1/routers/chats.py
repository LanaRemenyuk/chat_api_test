import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from apps.chats.models.chats import ChatInDB, ChatMessageInDB, UserChatLink
from apps.core.config import settings
from apps.db import get_session
from apps.mq.consumer import message_buffer
from apps.users.models.users import UserInDB

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f'/{settings.chats_settings.service_name}/api/v1',
)

setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'chats')

@router.get(
    path="/{channel_name}/history",
    response_model=List[ChatMessageInDB],
    status_code=status.HTTP_200_OK,
    tags=["Чат"],
    summary="Получить историю сообщений чата",
    operation_id="get_chat_history",
)
async def get_chat_history(channel_name: str, session: AsyncSession = Depends(get_session)):
    try:
        stmt = select(ChatMessageInDB).filter(ChatMessageInDB.channel == channel_name).order_by(ChatMessageInDB.sequence_number)
        result = await session.execute(stmt)
        history = result.scalars().all()

        for msg in message_buffer:
            if msg["channel"] == channel_name:
                history.append(ChatMessageInDB(
                    action=msg["action"],
                    username=msg["username"],
                    channel=msg["channel"],
                    time=datetime.fromisoformat(msg["time"]).replace(tzinfo=timezone.utc),
                    sequence_number=msg["sequence_number"],
                    message=msg.get("message") or "Сообщение отсутствует",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat()
                ))

        history.sort(key=lambda x: x.sequence_number)
        return history

    except Exception as e:
        logger.error(f"Ошибка при получении истории чата: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post(
    path="/{channel_name}/add_user",
    status_code=status.HTTP_200_OK,
    tags=["Чат"],
    summary="Добавить пользователя в чат",
    operation_id="add_user_to_chat",
)
async def add_user_to_chat(
    channel_name: str,
    username: str,
    session: AsyncSession = Depends(get_session),
):
    try:
        chat_query = await session.execute(select(ChatInDB).where(ChatInDB.name == channel_name))
        chat = chat_query.scalars().first()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Чат {channel_name} не найден"
            )

        user_query = await session.execute(select(UserInDB).where(UserInDB.username == username))
        user = user_query.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь {username} не найден"
            )

        user_chat_link_query = await session.execute(
            select(UserChatLink).where(
                UserChatLink.user_id == user.id,
                UserChatLink.chat_id == chat.id,
            )
        )
        if user_chat_link_query.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Пользователь {username} уже является участником этого чата"
            )

        user_chat_link = UserChatLink(user_id=user.id, chat_id=chat.id)
        session.add(user_chat_link)
        await session.commit()
        return {"detail": f"Пользователь {username} добавлен в чат {channel_name}"}

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь уже является участником этого чата"
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла ошибка: {str(e)}"
        )



