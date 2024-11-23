from fastapi import APIRouter, Depends, Request, status

from apps.core.config import settings
from apps.users.schemas.users import UserCreate, UserCreateResponse
from apps.users.services.users import Service, get_service

router = APIRouter(
    prefix=f'/{settings.users_settings.service_name}/api/v1',
)

setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'users')

@router.post(
    path='/create',
    status_code=status.HTTP_201_CREATED,
    name='user:create',
    tags=['Пользователь'],
    summary='Пользователь: создать',
    operation_id='user:create',
    response_model=UserCreateResponse
)
async def create(
    request: Request,
    user: UserCreate,
    service: Service = Depends(get_service)
) -> UserCreateResponse:
    return await service.create_user(
        request=request,
        user=user
    )