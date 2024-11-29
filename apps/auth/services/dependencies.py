# app/auth/dependencies.py
from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, status

from .auth_service import TokenService, get_token_service


async def get_refresh_token(request: Request, service: TokenService = Depends()):
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
    token = websocket.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is missing in WebSocket header"
        )

    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid token format in WebSocket header"
        )
    token = token.split(" ")[1]

    try:
        payload = await service.decode_access_token(token)
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id
