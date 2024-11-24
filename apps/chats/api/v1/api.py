from fastapi import APIRouter

from apps.chats.api.v1.routers import ws_chats, chats

chats_routers: list[APIRouter] = [
    ws_chats.router,
    chats.router
]