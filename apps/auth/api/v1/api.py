from fastapi import APIRouter

from apps.auth.api.v1.routers import auth_service

auth_routers: list[APIRouter] = [
    auth_service.router
]