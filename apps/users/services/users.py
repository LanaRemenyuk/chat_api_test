from functools import lru_cache
from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from apps.db import get_session
from apps.users.models.users import UserInDB
from apps.users.schemas.users import UserCreate, UserCreateResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, request: Request, user: UserCreate) -> UserCreateResponse:
        """Метод для создания пользователя, хэширует пароль и проверяет уникальность."""
        hashed_password = pwd_context.hash(user.hashed_pass)

        try:
            existing_user = await self.session.execute(
                select(UserInDB).where(
                    (UserInDB.username == user.username) | (UserInDB.email == user.email) | (UserInDB.phone == user.phone)
                )
            )
            existing_user = existing_user.scalars().first()

            if existing_user:
                conflict_fields = {
                    'username': (existing_user.username == user.username, "Имя пользователя уже зарегистрировано"),
                    'email': (existing_user.email == user.email, "Email уже зарегистрирован"),
                    'phone': (existing_user.phone == user.phone, "Номер телефона уже зарегистрирован")
                }
                
                for field, (is_conflict, message) in conflict_fields.items():
                    if is_conflict:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=message
                        )

            user_in_db: UserInDB = UserInDB(
                **user.dict(exclude={"hashed_pass"}),
                hashed_pass=hashed_password,
            )


            self.session.add(user_in_db)
            await self.session.commit()
            await self.session.refresh(user_in_db)

            return UserCreateResponse(
                id=user_in_db.id,
                username=user_in_db.username,
                phone=user_in_db.phone,
                email=user_in_db.email,
                role=user_in_db.role,
            )

        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error. Please try again."
            )
        
    async def get_user_by_id(self, user_id: UUID) -> UserInDB:
        user = await self.session.execute(select(UserInDB).filter(UserInDB.id == user_id))
        user = user.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        return user

@lru_cache
def get_service(session: AsyncSession = Depends(get_session)) -> Service:
    return Service(session=session)
