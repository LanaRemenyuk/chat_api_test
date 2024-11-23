from fastapi import APIRouter

from apps.users.api.v1.routers import users

users_routers: list[APIRouter] = [
    users.router
]