from datetime import datetime, timezone
from typing import Callable, ClassVar, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import UUIDType
from sqlmodel import Field, Relationship, SQLModel

from apps.db import metadata


class AuthTokensInDB(SQLModel, table=True):
    __tablename__ = 'tokens'
    __table_args__ = {'schema': metadata.schema}

    id: UUID = Field(default_factory=uuid4, sa_column=Column(UUIDType(binary=False), nullable=False, primary_key=True, index=True))
    user_id: UUID = Field(sa_column=Column(UUIDType(binary=False)))
    refresh_token: str = Field(sa_column=Column(String(255), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)))

    @classmethod
    async def get_refresh_token_for_user(cls, session: AsyncSession, refresh_token: str) -> Optional[UUID]:
        query = select(cls.user_id).where(cls.refresh_token == refresh_token)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def save_refresh_token(cls, session: AsyncSession, user_id: UUID, refresh_token: str) -> None:
        query = update(cls).where(cls.user_id == user_id).values(refresh_token=refresh_token, updated_at=datetime.now(timezone.utc)).returning(cls.id)
        result = await session.execute(query)
        updated_token = result.fetchone()
        if updated_token is None:
            token = cls(user_id=user_id, refresh_token=refresh_token)
            session.add(token)
        await session.commit()

    @classmethod
    async def delete_tokens(cls, session: AsyncSession, user_id: UUID) -> None:
        query = select(cls).where(cls.user_id == user_id)
        tokens = (await session.execute(query)).scalars().all()
        for token in tokens:
            await session.delete(token)
        await session.commit()