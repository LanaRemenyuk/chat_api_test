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
from apps.db import get_session
from sqlalchemy.ext.asyncio import AsyncSession

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
    session: AsyncSession = Depends(get_session)
) -> None:
    try:
        user = await service.get_user_by_id(user_id)
        username = user.username
        is_moderator = user.role == 'moderator'

        chat = await chat_service.get_chat_by_name(channel_name)

        if not chat:
            chat_data = ChatCreate(name=channel_name)
            chat = await chat_service.create_chat(chat_data)
            asyncio.create_task(start_consumer(f"{channel_name}_messages"))
            existing_link = await chat_service.get_user_chat_link(user_id=user_id, chat_id=chat.id)
            if not existing_link:
                await chat_service.create_user_chat_link(user_id=user_id, chat_id=chat.id)
                await session.commit()
 
        if channel_name not in invited_users:
            invited_users[channel_name] = []
            invited_users[channel_name].append(username)

        link = await chat_service.get_user_chat_link(user_id=user.id, chat_id=chat.id)
        if not link and not is_moderator:
            await websocket.send_text(f"Вы не добавлены в чат {channel_name}")
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
                    target_user = await service.get_user_by_name(target_username)

                    if not target_user:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} не существует.")
                        continue

                    existing_link = await chat_service.get_user_chat_link(user_id=target_user.id, chat_id=chat.id)
                    if existing_link:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} уже в чате.")
                        continue

                    await chat_service.create_user_chat_link(user_id=target_user.id, chat_id=chat.id)
                    await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} был приглашён в чат.")
                    await handle_user_activity("invited", target_username, channel_name, current_time_rabbit)
                    continue

                elif data.startswith("/block "):
                    target_username = data.split(" ", 1)[1]
                    target_user = await service.get_user_by_name(target_username)

                    if not target_user:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} не существует.")
                        continue

                    blocked_user_link = await chat_service.get_user_chat_link(user_id=target_user.id, chat_id=chat.id)
                    print(f'zheppppa {target_user.id} xxx {chat.id}')
                    if not blocked_user_link:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} не в чате.")
                        continue

                    for connection in active_channels[channel_name]:
                        if connection["username"] == target_username:
                            await connection["websocket"].send_text(f"Вы были заблокированы в канале {channel_name}.")
                            await connection["websocket"].close()  # Close the connection
                            active_channels[channel_name].remove(connection)
                            break

                    blocked_users[channel_name][target_username] = target_user.id

                    await chat_service.delete_user_chat_link(user_id=target_user.id, chat_id=chat.id)
                    await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} был заблокирован.")
                    await handle_moderator_action("blocked", target_username, channel_name, current_time_rabbit)


                elif data.startswith("/unblock "):
                    target_username = data.split(" ", 1)[1]
                    target_user = await service.get_user_by_name(target_username)

                    if not target_user:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} не существует.")
                        continue

                    blocked_user_link = await chat_service.get_user_chat_link(user_id=target_user.id, chat_id=chat.id)
                    if blocked_user_link:
                        await websocket.send_text(f"[{current_time_chat}] Пользователь {target_username} уже в чате.")
                        continue

                    await chat_service.create_user_chat_link(user_id=target_user.id, chat_id=chat.id)
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