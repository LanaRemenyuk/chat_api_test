from datetime import datetime, timedelta
from functools import lru_cache
from uuid import UUID
from fastapi import HTTPException, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.auth.models.auth_service import AuthTokensInDB
from apps.users.models.users import UserInDB
from apps.db import get_session
from apps.core.config import settings
import jwt

class TokenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def create_access_token(self, user_id: UUID, expires_delta: timedelta = None) -> str:
        to_encode = {"sub": str(user_id), "exp": datetime.utcnow() + (expires_delta or timedelta(minutes=3600))}
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")

    async def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            if payload.get("exp") < datetime.utcnow().timestamp():
                raise jwt.ExpiredSignatureError
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный или истекший токен")

    async def refresh_access_token(self, refresh_token: str) -> dict:
        user_id = await AuthTokensInDB.get_refresh_token_for_user(self.session, refresh_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Не найден refresh токен для пользователя")
        new_access_token = self.create_access_token(user_id)
        return {"access_token": new_access_token, "token_type": "bearer"}
    
    def extract_token_from_header(self, authorization: str) -> str:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        return authorization.split(" ")[1]

    async def verify_access_token(self, token: str) -> dict:
        return await self.decode_access_token(token)

    async def get_current_user(self, token: str) -> UUID:
        payload = await self.decode_access_token(token)
        return UUID(payload["sub"])

    async def login(self, username: str, password: str, response: Response) -> dict:
        user = await self.session.execute(select(UserInDB).filter(UserInDB.username == username))
        user = user.scalar_one_or_none()
        if not user or not user.verify_password(password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учетные данные")
        access_token = self.create_access_token(user.id)
        refresh_token = self.create_access_token(user.id, expires_delta=timedelta(days=30))
        await AuthTokensInDB.save_refresh_token(self.session, user.id, refresh_token)
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token,
            max_age=timedelta(days=30), 
            expires=timedelta(days=30), 
            httponly=True,
            samesite="Strict",
        )

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def logout(self, response: Response, user_id: UUID) -> None:
        response.delete_cookie("refresh_token")
        await AuthTokensInDB.delete_tokens(self.session, user_id)

def get_token_service(session: AsyncSession = Depends(get_session)) -> TokenService:
    return TokenService(session=session)
