from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException,  Request, Response, status

from apps.auth.schemas.auth import TokenPayload, LoginRequest, RefreshTokenRequest
from apps.auth.services.auth_service import TokenService, get_token_service
from apps.core.config import settings

router = APIRouter(
    prefix=f'/{settings.auth_settings.service_name}/api/v1',
)

setattr(router, 'version', 'v1')
setattr(router, 'service_name', 'auth_service')

@router.post(
    path='/login',
    status_code=status.HTTP_200_OK,
    name='auth:token:login',
    tags=['Аутентификация'],
    summary='Авторизация пользователя',
    operation_id='auth:token:login',
    response_model=dict
)
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    service: TokenService = Depends(get_token_service),
) -> dict:
    """
    Логин пользователя: проверка учетных данных, создание токенов.
    """
    username = login_data.username
    password = login_data.password
    return await service.login(username, password, response)

@router.post(
    path='/refresh',
    status_code=status.HTTP_200_OK,
    name='auth:token:refresh',
    tags=['Аутентификация'],
    summary='Обновить токен доступа',
    operation_id='auth:token:refresh',
    response_model=dict
)
async def refresh_token(body: RefreshTokenRequest, service: TokenService = Depends(get_token_service)) -> dict:
    return await service.refresh_access_token(refresh_token=body.refresh_token)

@router.get(
    path='/verify',
    status_code=status.HTTP_200_OK,
    name='auth:token:verify',
    tags=['Аутентификация'],
    summary='Проверить токен',
    operation_id='auth:token:verify',
    response_model=TokenPayload
)
async def verify_token(
    request: Request,
    authorization: Optional[str] = Header(None),
    service: TokenService = Depends(get_token_service),
) -> TokenPayload:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Заголовок авторизации отсутствует")
    
    token = service.extract_token_from_header(authorization)
    return await service.verify_access_token(token=token)

@router.post(
    path='/logout',
    status_code=status.HTTP_200_OK,
    name='auth:token:logout',
    tags=['Аутентификация'],
    summary='Выход из системы',
    operation_id='auth:token:logout',
)
async def logout(
    response: Response,
    authorization: Optional[str] = Header(None),
    service: TokenService = Depends(get_token_service),
) -> dict:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Заголовок авторизации отсутствует")
    
    token = service.extract_token_from_header(authorization)
    user_id = await service.get_current_user(token)
    await service.logout(response, user_id)
    
    return {"message": "Пользователь успешно вышел из системы"}


