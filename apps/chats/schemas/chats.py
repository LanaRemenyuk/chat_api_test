from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    """Модель для создания чата"""
    id: UUID = Field(description="id чата")
    name: str = Field(..., max_length=100, description="Название чата")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "00b4a513-16ed-498c-9494-5bdf5ca32206",
                "name": "general_chat"
            }
        }
    }


class ChatMessageHistory(BaseModel):
    """Модель для истории сообщений чата."""
    id: UUID = Field(
        ..., 
        description="id сообщения"
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
        description="Последовательный номер сообщения (для воссоздания истории сообщений)"
    )

    class Config:
        from_attributes = True
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
