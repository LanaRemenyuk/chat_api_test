from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy_utils import UUIDType
from sqlmodel import Field, Relationship, SQLModel

from apps.db import metadata


class UserChatLink(SQLModel, table=True):
    """Промежуточная таблица для связи ManyToMany между пользователями и чатами"""
    __tablename__ = "user_chat_links"
    __table_args__ = {'schema': metadata.schema}

    user_id: UUID = Field(
    sa_column=Column(
        UUIDType(binary=False), 
        ForeignKey(f"{metadata.schema}.users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    )
    chat_id: UUID = Field(
        sa_column=Column(
            UUIDType(binary=False), 
            ForeignKey(f"{metadata.schema}.chats.id", ondelete="CASCADE"), 
            primary_key=True
        )
    )
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ChatInDB(SQLModel, table=True):
    """Модель чата"""
    __tablename__ = 'chats'
    __table_args__ = {'schema': metadata.schema}

    id: UUID = Field(default_factory=uuid4, sa_column=Column(UUIDType(binary=False), nullable=False, primary_key=True, index=True))
    name: str = Field(sa_column=Column(String(255), nullable=False, unique=True)) 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)))
    users: List["UserInDB"] = Relationship(back_populates="chats", link_model=UserChatLink)

class ChatMessageInDB(SQLModel, table=True):
    """Модель сообщения в чате, соответствующая структуре RabbitMQ."""
    __tablename__ = 'chat_messages'
    __table_args__ = {'schema': metadata.schema}

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUIDType(binary=False), nullable=False, primary_key=True, index=True),
    )
    action: str = Field(
        sa_column=Column(String(50), nullable=False),
    )
    username: str = Field(
        sa_column=Column(String(50), nullable=False),
    )
    channel: str = Field(
        sa_column=Column(String(50), nullable=False),
    )
    time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    )
    sequence_number: int = Field(
        sa_column=Column(Integer, nullable=False, index=True),
    )
    message: str = Field(
        sa_column=Column(String, nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
    )