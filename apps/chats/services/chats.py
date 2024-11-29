from datetime import datetime
from functools import lru_cache
from typing import Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from apps.chats.models.chats import ChatInDB, UserChatLink
from apps.chats.schemas.chats import ChatCreate
from apps.db import get_session
from apps.users.models.users import UserInDB


class Service:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat(self, chat_data: ChatCreate) -> ChatInDB:
        """Creates a new chat if it doesn't exist."""
        existing_chat = await self.get_chat_by_name(chat_data.name)
        if existing_chat:
            return existing_chat

        chat = ChatInDB(id=chat_data.id, name=chat_data.name)
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
        user_chat_link = result.scalars().first()
        if not user_chat_link:

            print(f"No link found for user {user_id} in chat {chat_id}")
        return user_chat_link

    
    async def delete_user_chat_link(self, user_id: UUID, chat_id: UUID) -> None:
        link = await self.get_user_chat_link(user_id, chat_id)
        if link:
            await self.session.delete(link)
            await self.session.commit()
        else:
            raise ValueError("User is not a participant in the chat")


def get_service(session: AsyncSession = Depends(get_session)) -> Service:
    return Service(session=session)
