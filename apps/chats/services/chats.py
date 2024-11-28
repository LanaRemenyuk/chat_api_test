from datetime import datetime
from functools import lru_cache
from typing import Optional
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.chats.models.chats import ChatInDB
from apps.users.models.users import UserInDB
from apps.chats.schemas.chats import ChatCreate
from apps.chats.models.chats import ChatInDB, UserChatLink
from apps.db import get_session

class Service:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat(self, chat_data: ChatCreate) -> ChatInDB:
        """Создаёт новый чат, если он не существует."""
        existing_chat = await self.get_chat_by_name(chat_data.name)
        if existing_chat:
            return existing_chat

        chat = ChatInDB(name=chat_data.name)

        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        
        return chat

    async def create_user_chat_link(self, user_id: UUID, chat_id: UUID) -> UserChatLink:
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        self.session.add(user_chat_link)
        await self.session.commit()
        return user_chat_link

    async def get_chat_by_name(self, name: str) -> Optional[ChatInDB]:
        result = await self.session.execute(select(ChatInDB).where(ChatInDB.name == name))
        return result.scalars().first()
    
    async def get_user_chat_link(self, user_id: UUID, chat_id: UUID) -> Optional[UserChatLink]:
        result = await self.session.execute(
            select(UserChatLink).where(
                UserChatLink.user_id == user_id,
                UserChatLink.chat_id == chat_id
            )
        )
        return result.scalars().first()
    
    async def delete_user_chat_link(self, user_id: UUID, chat_id: UUID) -> None:
        link = await self.get_user_chat_link(user_id, chat_id)
        if link:
            await self.session.delete(link)
            await self.session.commit()
        else:
            raise ValueError("Юзер не является участником чатов")
    
@lru_cache
def get_service(session: AsyncSession = Depends(get_session)) -> Service:
    return Service(session=session)
