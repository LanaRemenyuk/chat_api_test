from datetime import datetime
from functools import lru_cache
from typing import Optional
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.chats.models.chats import ChatInDB
from apps.chats.schemas.chats import ChatCreate
from apps.chats.models.chats import ChatInDB
from apps.db import get_session

class Service:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat(self, chat_create: ChatCreate) -> ChatInDB:
        """Создает новый чат и сохраняет его в БД."""
        new_chat = ChatInDB(
            name=chat_create.name,
            created_at=datetime.now()
        )

        self.session.add(new_chat)
        await self.session.commit()
        await self.session.refresh(new_chat)

        return ChatInDB.from_orm(new_chat)

    async def get_chat_by_name(self, name: str) -> Optional[ChatInDB]:
        """Находит чат по имени."""
        result = await self.session.execute(select(ChatInDB).where(ChatInDB.name == name))
        return result.scalars().first()
    
@lru_cache
def get_service(session: AsyncSession = Depends(get_session)) -> Service:
    return Service(session=session)
