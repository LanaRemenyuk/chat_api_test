from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from passlib.context import CryptContext
from sqlalchemy import Column, DateTime, String
from sqlalchemy_utils import UUIDType
from sqlmodel import Field, Relationship, SQLModel

from apps.chats.models.chats import UserChatLink
from apps.db import metadata

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserInDB(SQLModel, table=True):
    """Модель пользователя в базе данных"""
    __tablename__ = 'users'
    __table_args__ = {'schema': metadata.schema}

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUIDType(binary=False), nullable=False, primary_key=True, index=True),
    )
    username: str = Field(
        sa_column=Column(String(50), nullable=False, unique=True),
    )
    email: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True),
    )
    hashed_pass: str = Field(
        sa_column=Column(String(255), nullable=False),
    )
    phone: str = Field(
        sa_column=Column(String(15), nullable=False),
    )
    role: str = Field(
        sa_column=Column(String(50), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
    )
    chats: List["ChatInDB"] = Relationship(back_populates="users", link_model=UserChatLink)

    def verify_password(self, password: str) -> bool:
        """Проверка пароля с использованием passlib"""
        return pwd_context.verify(password, self.hashed_pass)

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Хэширование пароля с использованием passlib"""
        return pwd_context.hash(password)
    
    def is_moderator(self) -> bool:
        """Проверка, является ли пользователь модератором"""
        return self.role == "moderator"


