from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, status

from .auth_service import TokenService, get_token_service

async def get_refresh_token(request: Request, service: TokenService = Depends()):
    """Получение refresh-токена"""
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token не найден в cookies"
        )
    
    try:
        token_data = await service.refresh_access_token(refresh_token)
        return token_data["access_token"]
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token истек или недействителен"
        )
    
async def get_current_user_from_websocket(websocket: WebSocket, service: TokenService = Depends(get_token_service)) -> UUID:
    """Получение юзера из токена в заголовке вебсокета"""
    token = websocket.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Токен отсутствует в заголовке вебсокета"
        )

    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Неправильный формат токена в заголовке вебсокета"
        )
    token = token.split(" ")[1]

    try:
        payload = await service.decode_access_token(token)
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Некорректный или истекший токен")

    return user_id
