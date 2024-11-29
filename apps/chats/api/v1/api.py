from fastapi import APIRouter

from apps.chats.api.v1.routers import chats, ws_chats

chats_routers: list[APIRouter] = [
    ws_chats.router,
    chats.router
]