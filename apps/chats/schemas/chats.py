from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ChatCreate(BaseModel):
    """Модель для создания чата."""
    name: str = Field(
        ..., 
        max_length=100, 
        description="Название чата"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "general_chat"
            }
        }
    }


class ChatMessageHistory(BaseModel):
    """Модель для истории сообщений чата."""
    id: UUID = Field(
        ..., 
        description="Уникальный идентификатор сообщения"
    )
    action: str = Field(
        ..., 
        description="Тип действия (например, отправка сообщения)"
    )
    username: str = Field(
        ..., 
        max_length=50, 
        description="Имя пользователя, отправившего сообщение"
    )
    channel: str = Field(
        ..., 
        max_length=50, 
        description="Канал, в котором было отправлено сообщение"
    )
    time: datetime = Field(
        ..., 
        description="Время отправки сообщения"
    )
    sequence_number: int = Field(
        ..., 
        description="Последовательный номер сообщения"
    )

    class Config:
        orm_mode = True
        json_schema_extra = {
            "example": {
                "id": "a18cbb4e-b5b8-4825-b9f3-9f930b0e994b",
                "action": "message",
                "username": "lily",
                "channel": "general_chat",
                "time": "2024-11-24T00:12:00Z",
                "sequence_number": 42
            }
        }
