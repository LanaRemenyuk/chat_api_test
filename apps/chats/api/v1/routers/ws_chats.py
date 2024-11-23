from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import List, Dict
from uuid import UUID
from datetime import datetime
from apps.auth.services.dependencies import get_current_user_from_websocket
from apps.users.services.users import Service, get_service
from apps.core.config import settings
from apps.mq.publisher import send_message_to_queue, handle_user_activity, handle_moderator_action

router = APIRouter(
    prefix=f'/{settings.chats_settings.service_name}/api/v1',
)
setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'chats')

active_channels: Dict[str, List[Dict[str, WebSocket]]] = {}
blocked_users: Dict[str, Dict[str, UUID]] = {}

@router.websocket("/ws/{channel_name}")
async def chat_websocket(
    websocket: WebSocket,
    user_id: UUID = Depends(get_current_user_from_websocket),
    channel_name: str = None,
    service: Service = Depends(get_service)
) -> None:
    try:
        user = await service.get_user_by_id(user_id)
        username = user.username
        is_moderator = user.role == 'moderator'

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

        current_time = datetime.now().strftime('%H:%M')
        for connection in active_channels[channel_name]:
            join_message = (
                f"[{current_time}] Вы вошли в чат"
                if connection["user_id"] == user_id
                else f"[{current_time}] {'Модератор' if is_moderator else 'Пользователь'} {username} вошел в чат"
            )
            try:
                await connection["websocket"].send_text(join_message)
            except RuntimeError:
                continue

        await handle_user_activity("connect", username, channel_name, current_time)

        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            current_time = datetime.now().strftime('%H:%M')

            if is_moderator:
                if data.startswith("/kick "):
                    target_username = data.split(" ", 1)[1]
                    target_user = next(
                        (u for u in active_channels[channel_name] if u["username"] == target_username), None
                    )
                    if target_user:
                        active_channels[channel_name] = [
                            conn for conn in active_channels[channel_name]
                            if conn["websocket"] != target_user["websocket"]
                        ]
                        await target_user["websocket"].send_text(f"Вы были удалены из канала {channel_name} модератором.")
                        await target_user["websocket"].close()
                        await websocket.send_text(f"[{current_time}] Пользователь {target_username} был удален из канала.")
                        await handle_user_activity("disconnect", target_username, channel_name, current_time)
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
                        await websocket.send_text(f"[{current_time}] Пользователь {target_username} был заблокирован.")
                        await handle_moderator_action("block", target_username, channel_name, current_time)
                        continue

                elif data.startswith("/unblock "):
                    target_username = data.split(" ", 1)[1]

                    if target_username not in blocked_users[channel_name]:
                        await websocket.send_text(f"[{current_time}] Пользователь {target_username} не найден в блокировке.")
                        continue

                    del blocked_users[channel_name][target_username]
                    await websocket.send_text(f"[{current_time}] Пользователь {target_username} был успешно разблокирован.")
                    await handle_moderator_action("unblock", target_username, channel_name, current_time)

            message_data = {
                "sender": username if connection["user_id"] == user_id else (
                    f"Модератор {username}" if is_moderator else f"Пользователь {username}"
                ),
                "message": data,
                "channel": channel_name,
                "time": current_time
            }
            await send_message_to_queue(channel_name, message_data)

            for connection in active_channels[channel_name]:
                message = f"[{current_time}] {'Вы' if connection['user_id'] == user_id else message_data['sender']}: {data}"
                try:
                    await connection["websocket"].send_text(message)
                except RuntimeError:
                    continue

    except WebSocketDisconnect:
        if channel_name in active_channels:
            active_channels[channel_name] = [conn for conn in active_channels[channel_name] if conn["websocket"] != websocket]

        current_time = datetime.now().strftime('%H:%M')
        for connection in active_channels.get(channel_name, []):
            leave_message = (
                f"[{current_time}] Вы вышли из чата"
                if connection["user_id"] == user_id
                else f"[{current_time}] {'Модератор' if is_moderator else 'Пользователь'} {username} вышел из чата"
            )
            try:
                await connection["websocket"].send_text(leave_message)
            except RuntimeError:
                continue

        await handle_user_activity("disconnect", username, channel_name, current_time)

    except Exception as e:
        await websocket.send_text(f"Ошибка: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

