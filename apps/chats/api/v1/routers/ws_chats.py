import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from apps.auth.services.dependencies import get_current_user_from_websocket
from apps.users.services.users import Service, get_service
from apps.core.config import settings
from apps.mq.publisher import send_message_to_queue, handle_user_activity, handle_moderator_action
from apps.mq.consumer import start_consumer
from apps.chats.schemas.chats import ChatCreate
from apps.chats.services.chats import Service as chat_service, get_service as get_chat_service
from apps.chats.models import ChatMessageInDB

router = APIRouter(
    prefix=f'/{settings.chats_settings.service_name}/api/v1',
)
setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'chats')

active_channels: Dict[str, List[Dict[str, WebSocket]]] = {}
blocked_users: Dict[str, Dict[str, UUID]] = {}
channels_to_consume: Dict[str, bool] = {}
invited_users: Dict[str, List[str]] = {}

@router.websocket("/ws/{channel_name}")
async def chat_websocket(
    websocket: WebSocket,
    user_id: UUID = Depends(get_current_user_from_websocket),
    channel_name: str = None,
    service: Service = Depends(get_service),
    chat_service: chat_service = Depends(get_chat_service),
) -> None:
    try:
        user = await service.get_user_by_id(user_id)
        username = user.username
        is_moderator = user.role == 'moderator'

        chat = await chat_service.get_chat_by_name(channel_name)

        if not chat and is_moderator:  # Только модератор может создавать чат
            chat_data = ChatCreate(name=channel_name, owner_id=user_id)
            chat = await chat_service.create_chat(chat_data)
            asyncio.create_task(start_consumer(f"{channel_name}_messages"))
        
        if not chat:
            await websocket.send_text("Только модератор может создать чат.")
            await websocket.close()
            return
        if channel_name not in invited_users:
            invited_users[channel_name] = []

        if username not in invited_users[channel_name] and not is_moderator:
            await websocket.send_text(f"Вы не были приглашены в чат {channel_name}.")
            await websocket.close()
            return

        if channel_name not in blocked_users:
            blocked_users[channel_name] = {}

        if username in blocked_users[channel_name]:
            await websocket.accept()
            await websocket.send_text("Вы были заблокированы в этом канале. Доступ запрещен.")
            await websocket.close()
            return

        if channel_name not in active_channels:
            active_channels[channel_name] = []

        active_channels[channel_name].append({"user_id": user_id, "username": username, "websocket": websocket})
        await websocket.accept()

        current_time_chat = datetime.now().strftime('%H:%M')
        current_time_rabbit = datetime.now(timezone.utc).isoformat()

        for connection in active_channels[channel_name]:
            join_message = (
                f"[{current_time_chat}] Вы вошли в чат"
                if connection["user_id"] == user_id
                else f"[{current_time_chat}] {'Модератор' if is_moderator else 'Пользователь'} {username} вошел в чат"
            )
            try:
                await connection["websocket"].send_text(join_message)
            except RuntimeError:
                continue

        await handle_user_activity("connect", username, channel_name, current_time_rabbit)

        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            current_time_chat = datetime.now().strftime('%H:%M')
            current_time_rabbit = datetime.now(timezone.utc).isoformat()

            if is_moderator:
                if data.startswith("/invite "):
                    target_username = data.split(" ", 1)[1]
                    if target_username not in invited_users[channel_name]:
                        invited_users[channel_name].append(target_username)
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} был приглашён в чат.")
                        await handle_user_activity("invited", target_username, channel_name, current_time_rabbit)
                    else:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} уже приглашён в чат.")
                    continue
                elif data.startswith("/block "):
                    target_username = data.split(" ", 1)[1]
                    target_user = next(
                        (u for u in active_channels[channel_name] if u["username"] == target_username), None
                    )
                    if target_user:
                        blocked_users[channel_name][target_username] = target_user["user_id"]
                        active_channels[channel_name] = [
                            conn for conn in active_channels[channel_name]
                            if conn["websocket"] != target_user["websocket"]
                        ]
                        await target_user["websocket"].send_text(f"Вы были заблокированы и удалены из канала {channel_name}.")
                        await target_user["websocket"].close()
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} был заблокирован.")
                        await handle_moderator_action("blocked", target_username, channel_name, current_time_rabbit)
                        continue

                elif data.startswith("/unblock "):
                    target_username = data.split(" ", 1)[1]

                    if target_username not in blocked_users[channel_name]:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь с именем {target_username} не найден в блокировке.")
                        continue

                    del blocked_users[channel_name][target_username]
                    await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} был успешно разблокирован.")
                    await handle_moderator_action("unblocked", target_username, channel_name, current_time_rabbit)
                    continue
            
            message_data = ChatMessageInDB(
                action="message",
                username=username,
                channel=channel_name,
                time=current_time_rabbit,
                sequence_number=len(active_channels[channel_name]),
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                id = str(uuid4()),
                message=data,
            )
            await send_message_to_queue(channel_name, message_data.dict())

            for connection in active_channels[channel_name]:
                message = f"[{current_time_chat}] {message_data.username}: {data}"
                try:
                    await connection["websocket"].send_text(message)
                except RuntimeError:
                    continue

    except WebSocketDisconnect:
        if channel_name in active_channels:
            active_channels[channel_name] = [conn for conn in active_channels[channel_name] if conn["websocket"] != websocket]

        current_time_chat = datetime.now().strftime('%H:%M')
        current_time_rabbit = datetime.now(timezone.utc).isoformat()

        for connection in active_channels.get(channel_name, []):
            leave_message = (
                f"[{current_time_chat}] Вы вышли из чата"
                if connection["user_id"] == user_id
                else f"[{current_time_chat}] {'Модератор' if is_moderator else 'Пользователь'} {username} вышел из чата"
            )
            try:
                await connection["websocket"].send_text(leave_message)
            except RuntimeError:
                continue

        await handle_user_activity("disconnect", username, channel_name, current_time_rabbit)

    except Exception as e:
        await websocket.send_text(f"Ошибка: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


